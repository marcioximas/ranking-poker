from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
import io
import unicodedata

from ..database import get_db
from ..dependencies import require_admin
from ..models import Player, Round, RoundPlayer

router = APIRouter(prefix="/rounds", tags=["Importar Rodada"])

# Maps normalized Portuguese column names → RoundPlayer field
_COLUMN_MAP = {
    "jogador": "name", "nome": "name", "player": "name",
    "pontos": "pontos", "pts": "pontos",
    "presenca": "presenca", "presença": "presenca",
    "bonus": "bonus", "bônus": "bonus", "itm": "bonus",
    "pontualidade": "pontualidade", "pont": "pontualidade",
    "indicacao": "indicacao", "indicação": "indicacao", "ind": "indicacao",
    "compras": "buyin", "buyin": "buyin", "buyins": "buyin",
    "buy-in": "buyin", "buy-ins": "buyin", "rebuys": "buyin",
    "addon": "addon", "addons": "addon", "add-on": "addon",
}


def _norm(s: str) -> str:
    s = s.lower().strip()
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def _to_int(v) -> int:
    try:
        return max(0, int(str(v).strip().replace(",", "").split(".")[0]))
    except (ValueError, TypeError):
        return 0


def _parse_tables(content: bytes) -> list[dict]:
    """Extract rows from PDF tables (spreadsheet-style exports)."""
    import pdfplumber
    rows = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            for table in (page.extract_tables() or []):
                if not table or len(table) < 2:
                    continue
                norm_headers = [_norm(str(h or "")) for h in table[0]]

                col_map: dict[int, str] = {}
                for i, nh in enumerate(norm_headers):
                    field = _COLUMN_MAP.get(nh)
                    if field and field not in col_map.values():
                        col_map[i] = field

                if "name" not in col_map.values():
                    continue

                for raw_row in table[1:]:
                    cells = [str(c or "").strip() for c in raw_row]
                    if not any(cells):
                        continue
                    entry = {field: cells[i] for i, field in col_map.items() if i < len(cells)}
                    if entry.get("name"):
                        rows.append(entry)
    return rows


def _parse_text(content: bytes) -> list[dict]:
    """Fallback: parse 'Nome, pontos' lines from plain text."""
    import pdfplumber
    rows = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 1 and parts[0] and not parts[0][0].isdigit():
                    entry = {"name": parts[0]}
                    if len(parts) >= 2:
                        entry["pontos"] = parts[1]
                    rows.append(entry)
    return rows


def _parse_pdf(content: bytes) -> list[dict]:
    rows = _parse_tables(content)
    return rows if rows else _parse_text(content)


def _match_players(raw_rows: list[dict], db_players: list[Player]):
    index = {_norm(p.name): p for p in db_players}
    matched, unmatched = [], []

    for row in raw_rows:
        name = row.get("name", "").strip()
        if not name:
            continue
        player = index.get(_norm(name))
        if not player:
            unmatched.append(name)
        else:
            matched.append({
                "player_id":    player.id,
                "player_name":  player.name,
                "buyin":        _to_int(row.get("buyin")) or 1,
                "addon":        _to_int(row.get("addon")),
                "pontos":       _to_int(row.get("pontos")),
                "presenca":     _to_int(row.get("presenca")),
                "bonus":        _to_int(row.get("bonus")),
                "pontualidade": _to_int(row.get("pontualidade")),
                "indicacao":    _to_int(row.get("indicacao")),
            })
    return matched, unmatched


@router.post(
    "/import-pdf",
    summary="Importar rodada via PDF",
    dependencies=[Depends(require_admin)],
)
async def import_round_from_pdf(
    file:    UploadFile    = File(..., description="PDF com a planilha da rodada"),
    label:   Optional[str] = Form(None),
    dry_run: bool          = Form(False),
    db:      Session       = Depends(get_db),
):
    """
    Lê uma planilha PDF e cria uma rodada com os jogadores reconhecidos.

    **Formato esperado** — tabela com pelo menos a coluna *Jogador*:

    | Jogador | Pontos | Presença | Bônus | Pontualidade | Indicação | Compras | Addon |
    |---------|--------|----------|-------|--------------|-----------|---------|-------|
    | Alice   | 10     | 5        | 10    | 0            | 0         | 1       | 0     |

    - `dry_run=true` → apenas analisa e retorna preview, sem criar nada.
    - `dry_run=false` → analisa + cria rodada + adiciona jogadores reconhecidos.
    """
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "O arquivo deve ser um PDF (.pdf).")

    content = await file.read()
    if not content:
        raise HTTPException(400, "O arquivo PDF está vazio.")

    MAX_SIZE = 5 * 1024 * 1024  # 5 MB
    if len(content) > MAX_SIZE:
        raise HTTPException(413, "O arquivo PDF não pode ser maior que 5 MB.")

    raw_rows = _parse_pdf(content)
    if not raw_rows:
        raise HTTPException(
            422,
            "Nenhum dado encontrado no PDF. "
            "Verifique se o arquivo contém uma tabela com coluna 'Jogador' ou 'Nome'.",
        )

    db_players = db.query(Player).all()
    matched, unmatched = _match_players(raw_rows, db_players)

    if dry_run:
        return {"dry_run": True, "matched": matched, "unmatched": unmatched}

    if not matched:
        raise HTTPException(
            422,
            "Nenhum jogador do PDF foi encontrado no cadastro. "
            "Verifique se os nomes coincidem com os jogadores cadastrados.",
        )

    if db.query(Round).filter(Round.is_current == True).first():
        raise HTTPException(409, "Já existe uma rodada em andamento. Finalize-a primeiro.")

    round_label = label or f"Rodada {db.query(Round).count() + 1}"

    if db.query(Round).filter(Round.label == round_label).first():
        raise HTTPException(409, f"Já existe uma rodada com o label '{round_label}'.")
    round_ = Round(
        label=round_label,
        is_current=True,
        is_active_in_ranking=False,
        is_finalized=False,
    )
    db.add(round_)
    db.commit()
    db.refresh(round_)

    for m in matched:
        db.add(RoundPlayer(
            round_id=round_.id,
            player_id=m["player_id"],
            buyin=m["buyin"],
            addon=m["addon"],
            pontos=m["pontos"],
            presenca=m["presenca"],
            bonus=m["bonus"],
            pontualidade=m["pontualidade"],
            indicacao=m["indicacao"],
        ))
    db.commit()

    return {
        "dry_run":       False,
        "round_id":      round_.id,
        "round_label":   round_label,
        "players_added": len(matched),
        "matched":       matched,
        "unmatched":     unmatched,
    }
