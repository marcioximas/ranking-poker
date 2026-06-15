from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
import asyncio
import io
import unicodedata

from ..database import get_db
from ..dependencies import require_admin
from ..models import Player, Round, RoundPlayer

router = APIRouter(prefix="/rounds", tags=["Importar Rodada"])

# Maps normalized Portuguese column names → RoundPlayer field
_COLUMN_MAP = {
    # name
    "jogador": "name", "nome": "name", "player": "name",
    # pontos
    "pontos": "pontos", "pts": "pontos",
    # presenca
    "presenca": "presenca",
    # bonus
    "bonus": "bonus", "itm": "bonus", "bonus itm": "bonus",
    # pontualidade
    "pontualidade": "pontualidade", "pont": "pontualidade",
    # indicacao
    "indicacao": "indicacao", "ind": "indicacao",
    # buyin
    "compras": "buyin", "buyin": "buyin", "buyins": "buyin",
    "buy-in": "buyin", "buy-ins": "buyin", "rebuys": "buyin",
    "buy in / rebuy": "buyin", "buy in": "buyin", "rebuy": "buyin",
    # addon
    "addon": "addon", "addons": "addon", "add-on": "addon",
    # colocacao
    "colocacao": "colocacao", "col": "colocacao",
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


def _parse_words(content: bytes) -> list[dict]:
    """
    Word-level extraction for PDFs with rotated/complex headers.
    Reconstructs rows by grouping words that share the same y-band,
    then matches columns by x-position against detected headers.
    """
    import pdfplumber
    rows = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            words = page.extract_words(x_tolerance=5, y_tolerance=5) or []
            if not words:
                continue

            # Group words into lines by top-coordinate band
            from collections import defaultdict
            bands: dict[int, list] = defaultdict(list)
            for w in words:
                band = round(float(w["top"]) / 5) * 5
                bands[band].append(w)

            sorted_bands = sorted(bands.items())

            # Find the header line: the one that contains a "nome" or "jogador" word
            header_band_idx = None
            header_cols: dict[int, str] = {}  # x_center -> field
            for idx, (band, wds) in enumerate(sorted_bands):
                norm_texts = [_norm(w["text"]) for w in wds]
                if any(t in ("nome", "jogador", "player") for t in norm_texts):
                    header_band_idx = idx
                    for w in wds:
                        field = _COLUMN_MAP.get(_norm(w["text"]))
                        if field:
                            x_center = (float(w["x0"]) + float(w["x1"])) / 2
                            header_cols[x_center] = field
                    break

            if header_band_idx is None or not header_cols:
                continue

            col_xs = sorted(header_cols.keys())

            def nearest_col(x):
                return min(col_xs, key=lambda cx: abs(cx - x))

            # Parse subsequent lines as data rows
            for band, wds in sorted_bands[header_band_idx + 1:]:
                if not wds:
                    continue
                entry: dict[str, str] = {}
                for w in wds:
                    x_mid = (float(w["x0"]) + float(w["x1"])) / 2
                    col_x = nearest_col(x_mid)
                    field = header_cols[col_x]
                    if field not in entry:
                        entry[field] = w["text"]
                    else:
                        entry[field] += " " + w["text"]  # multi-word name

                name = entry.get("name", "").strip()
                # Stop at financial summary section
                if not name or any(kw in name.lower() for kw in ("total", "caixa", "ranking", "dealer", "premiacao")):
                    break
                rows.append(entry)
    return rows


def _parse_text(content: bytes) -> list[dict]:
    """Last-resort fallback: parse 'Nome, pontos' lines from plain text."""
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
    try:
        rows = _parse_tables(content)
        if rows:
            return rows
        rows = _parse_words(content)
        if rows:
            return rows
        return _parse_text(content)
    except Exception as exc:
        raise HTTPException(422, f"Erro ao processar o PDF: {exc}")


def _parse_csv(content: bytes) -> list[dict]:
    import csv
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(text.splitlines())
    rows = []
    for raw in reader:
        entry: dict[str, str] = {}
        for col, val in raw.items():
            field = _COLUMN_MAP.get(_norm(col or ""))
            if field and field not in entry:
                entry[field] = (val or "").strip()
        if entry.get("name"):
            rows.append(entry)
    return rows


def _find_player(name: str, db_players: list[Player]):
    norm = _norm(name)
    # Exact match first
    for p in db_players:
        if _norm(p.name) == norm:
            return p
    # Prefix match: "Danilo" → "Danilo Vieira" (avoids false positives like "Fael"→"Rafael")
    for p in db_players:
        pn = _norm(p.name)
        if norm and len(norm) >= 4 and (pn.startswith(norm) or norm.startswith(pn)):
            return p
    return None


def _match_players(raw_rows: list[dict], db_players: list[Player]):
    matched, unmatched = [], []

    for row in raw_rows:
        name = row.get("name", "").strip()
        if not name:
            continue
        player = _find_player(name, db_players)
        if not player:
            unmatched.append(name)
        else:
            matched.append({
                "player_id":    player.id,
                "player_name":  player.name,
                "buyin":        _to_int(row.get("buyin")) or 1,
                "addon":        _to_int(row.get("addon")),
                "colocacao":    _to_int(row.get("colocacao")),
                "pontos":       _to_int(row.get("pontos")),
                "presenca":     _to_int(row.get("presenca")),
                "bonus":        _to_int(row.get("bonus")),
                "pontualidade": _to_int(row.get("pontualidade")),
                "indicacao":    _to_int(row.get("indicacao")),
            })
    return matched, unmatched


def _do_import(matched: list, unmatched: list, dry_run: bool, label: Optional[str], db: Session):
    if dry_run:
        return {"dry_run": True, "matched": matched, "unmatched": unmatched}

    if not matched:
        raise HTTPException(
            422,
            "Nenhum jogador foi encontrado no cadastro. "
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
            colocacao=m["colocacao"],
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


@router.post(
    "/import-csv",
    summary="Importar rodada via CSV",
    dependencies=[Depends(require_admin)],
)
async def import_round_from_csv(
    file:    UploadFile    = File(..., description="CSV exportado da planilha da rodada"),
    label:   Optional[str] = Form(None),
    dry_run: bool          = Form(False),
    db:      Session       = Depends(get_db),
):
    """
    Importa uma rodada a partir de um arquivo CSV.

    **Colunas reconhecidas** (case-insensitive, aceita acentuação):
    `Nome` / `Jogador`, `Buy in / Rebuy` / `Compras`, `Addon`, `Pontos`,
    `Presença`, `Bônus ITM`, `Indicação`, `Pontualidade`, `Colocação`.
    """
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(400, "O arquivo deve ser um CSV (.csv).")

    content = await file.read()
    if not content:
        raise HTTPException(400, "O arquivo CSV está vazio.")

    try:
        raw_rows = _parse_csv(content)
    except Exception as exc:
        raise HTTPException(422, f"Erro ao processar o CSV: {exc}")

    if not raw_rows:
        raise HTTPException(
            422,
            "Nenhum dado encontrado no CSV. "
            "Verifique se o arquivo contém uma coluna 'Nome' ou 'Jogador'.",
        )

    db_players = db.query(Player).all()
    matched, unmatched = _match_players(raw_rows, db_players)
    return _do_import(matched, unmatched, dry_run, label, db)


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
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "O arquivo deve ser um PDF (.pdf).")

    content = await file.read()
    if not content:
        raise HTTPException(400, "O arquivo PDF está vazio.")

    MAX_SIZE = 5 * 1024 * 1024
    if len(content) > MAX_SIZE:
        raise HTTPException(413, "O arquivo PDF não pode ser maior que 5 MB.")

    loop = asyncio.get_event_loop()
    try:
        raw_rows = await asyncio.wait_for(
            loop.run_in_executor(None, _parse_pdf, content),
            timeout=20.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(408, "O processamento do PDF excedeu o tempo limite.")

    if not raw_rows:
        raise HTTPException(
            422,
            "Nenhum dado encontrado no PDF. O arquivo pode ser baseado em imagem. "
            "Tente exportar como CSV.",
        )

    db_players = db.query(Player).all()
    matched, unmatched = _match_players(raw_rows, db_players)
    return _do_import(matched, unmatched, dry_run, label, db)
