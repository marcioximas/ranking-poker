from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..dependencies import require_admin
from ..models import Round, RoundPlayer, SemestralScore, Player, Config
from ..schemas import (
    RoundRead, RoundCreate, RoundUpdate,
    RoundPlayerRead, RoundPlayerCreate, RoundPlayerUpdate,
    FinalizeResult, FinalizeRankingEntry,
)

router = APIRouter(prefix="/rounds", tags=["Rodadas"])

ENTRY_FEE = 10.0
DEALER_FEE = 50.0
DEALER_FEE_MIN_PLAYERS = 7


def _dealer_fee(num_players: int) -> float:
    return DEALER_FEE if num_players >= DEALER_FEE_MIN_PLAYERS else 0.0


def _normalize_buyin_rebuy(buyin: Optional[int], rebuy: Optional[int]) -> tuple[int, int]:
    buyin_val = max(int(buyin or 0), 0)
    if rebuy is None:
        # Backward compatibility: legacy payload used buyin as total entries.
        entries = buyin_val
        if entries <= 0:
            return 0, 0
        return 1, max(entries - 1, 0)

    rebuy_val = max(int(rebuy or 0), 0)
    return (1 if buyin_val > 0 else 0), rebuy_val


def _entry_gross(buyins: int, rebuys: int, config: Config) -> float:
    if buyins <= 0 and rebuys <= 0:
        return 0.0
    buyin_value = config.buyin_value or 0
    rebuy_value = getattr(config, "rebuy_value", None)
    if rebuy_value is None:
        rebuy_value = buyin_value
    return buyins * buyin_value + rebuys * rebuy_value


def _entry_fee(buyins: int, rebuys: int) -> float:
    return max(buyins + rebuys, 0) * ENTRY_FEE


def _calc_prize_points(
    colocacao: int,
    total_buyins: int,
    total_rebuys: int,
    total_addons: int,
    config: Config,
    num_players: int = 0,
) -> int:
    """Convert a placement into ranking points based on the prize pool formula.

    85% of arrecadado goes to prizes: 70% to 1st, 30% to 2nd.
    Points = int(prize_reais) // 10  (first 2 digits for <R$1000, 3 for ≥R$1000).
    """
    buyin_value = config.buyin_value or 0
    rebuy_value = getattr(config, "rebuy_value", None)
    if rebuy_value is None:
        rebuy_value = buyin_value

    gross_entries = total_buyins * buyin_value + total_rebuys * rebuy_value

    base_entries = max(gross_entries - _entry_fee(total_buyins, total_rebuys) - _dealer_fee(num_players), 0.0)

    arrecadado = base_entries + total_addons * (config.addon_value or 0)
    prize_pool = arrecadado * 0.85
    if colocacao == 1:
        prize = prize_pool * 0.70
    elif colocacao == 2:
        prize = prize_pool * 0.30
    else:
        return 0
    return int(prize) // 10


def _calc_total(rp: RoundPlayer) -> int:
    return (rp.pontos or 0) + (rp.presenca or 0) + (rp.bonus or 0) + (rp.indicacao or 0) + (rp.pontualidade or 0)


def _to_read(rp: RoundPlayer) -> RoundPlayerRead:
    return RoundPlayerRead(
        id=rp.id,
        round_id=rp.round_id,
        player_id=rp.player_id,
        player_name=rp.player.name,
        buyin=rp.buyin,
        rebuy=rp.rebuy or 0,
        addon=rp.addon,
        colocacao=rp.colocacao or 0,
        pontos=rp.pontos,
        presenca=rp.presenca,
        bonus=rp.bonus,
        indicacao=rp.indicacao,
        pontualidade=rp.pontualidade,
        total=_calc_total(rp),
    )


def _auto_label(db: Session, d) -> str:
    count = db.query(Round).count() + 1
    if d:
        return f"Rodada {count} - {d.strftime('%d/%m')}"
    return f"Rodada {count}"


# ── Round CRUD ──────────────────────────────────────────────────────────────

@router.get("", response_model=List[RoundRead], summary="Listar todas as rodadas")
def list_rounds(db: Session = Depends(get_db)):
    return db.query(Round).order_by(Round.id).all()


@router.get("/current", response_model=Optional[RoundRead], summary="Buscar rodada em andamento")
def get_current_round(db: Session = Depends(get_db)):
    return db.query(Round).filter(Round.is_current == True).first()


@router.get("/{round_id}", response_model=RoundRead, summary="Buscar rodada por ID")
def get_round(round_id: int, db: Session = Depends(get_db)):
    round_ = db.query(Round).filter(Round.id == round_id).first()
    if not round_:
        raise HTTPException(404, "Rodada não encontrada.")
    return round_


@router.post("", response_model=RoundRead, status_code=201,
             summary="Criar rodada histórica finalizada (para ranking)",
             dependencies=[Depends(require_admin)])
def create_round(data: RoundCreate, db: Session = Depends(get_db)):
    label = data.label or _auto_label(db, data.date)
    round_ = Round(label=label, date=data.date, is_current=False,
                   is_active_in_ranking=True, is_finalized=True)
    db.add(round_)
    db.commit()
    db.refresh(round_)
    return round_


@router.post("/current", response_model=RoundRead, status_code=201,
             summary="Iniciar nova rodada",
             dependencies=[Depends(require_admin)])
def start_current_round(data: RoundCreate, db: Session = Depends(get_db)):
    if db.query(Round).filter(Round.is_current == True).first():
        raise HTTPException(409, "Já existe uma rodada em andamento. Finalize-a primeiro.")
    label = data.label or _auto_label(db, data.date)
    round_ = Round(label=label, date=data.date, is_current=True, is_active_in_ranking=False, is_finalized=False)
    db.add(round_)
    db.commit()
    db.refresh(round_)
    return round_


@router.put("/{round_id}", response_model=RoundRead, summary="Atualizar rodada",
            dependencies=[Depends(require_admin)])
def update_round(round_id: int, data: RoundUpdate, db: Session = Depends(get_db)):
    round_ = db.query(Round).filter(Round.id == round_id).first()
    if not round_:
        raise HTTPException(404, "Rodada não encontrada.")
    if data.label is not None:
        round_.label = data.label
    if data.date is not None:
        round_.date = data.date
    if data.is_active_in_ranking is not None:
        round_.is_active_in_ranking = data.is_active_in_ranking
    db.commit()
    db.refresh(round_)
    return round_


@router.delete("/{round_id}", status_code=204, summary="Excluir rodada",
               dependencies=[Depends(require_admin)])
def delete_round(round_id: int, db: Session = Depends(get_db)):
    round_ = db.query(Round).filter(Round.id == round_id).first()
    if not round_:
        raise HTTPException(404, "Rodada não encontrada.")
    db.delete(round_)
    db.commit()


# ── Round Players ───────────────────────────────────────────────────────────

@router.get("/{round_id}/players", response_model=List[RoundPlayerRead],
            summary="Listar jogadores da rodada")
def list_round_players(round_id: int, db: Session = Depends(get_db)):
    round_ = db.query(Round).filter(Round.id == round_id).first()
    if not round_:
        raise HTTPException(404, "Rodada não encontrada.")
    rps = sorted(round_.round_players, key=_calc_total, reverse=True)
    return [_to_read(rp) for rp in rps]


@router.post("/{round_id}/players", response_model=RoundPlayerRead, status_code=201,
             summary="Adicionar jogador à rodada",
             dependencies=[Depends(require_admin)])
def add_round_player(round_id: int, data: RoundPlayerCreate, db: Session = Depends(get_db)):
    round_ = db.query(Round).filter(Round.id == round_id).first()
    if not round_:
        raise HTTPException(404, "Rodada não encontrada.")
    if not db.query(Player).filter(Player.id == data.player_id).first():
        raise HTTPException(404, "Jogador não encontrado.")
    if db.query(RoundPlayer).filter(RoundPlayer.round_id == round_id, RoundPlayer.player_id == data.player_id).first():
        raise HTTPException(409, "Jogador já está nesta rodada.")
    payload = data.model_dump()
    buyin_norm, rebuy_norm = _normalize_buyin_rebuy(payload.get("buyin"), payload.get("rebuy"))
    payload["buyin"] = buyin_norm
    payload["rebuy"] = rebuy_norm
    rp = RoundPlayer(**payload, round_id=round_id)
    db.add(rp)
    db.commit()
    db.refresh(rp)
    return _to_read(rp)


@router.put("/{round_id}/players/{player_id}", response_model=RoundPlayerRead,
            summary="Atualizar dados do jogador na rodada",
            dependencies=[Depends(require_admin)])
def update_round_player(round_id: int, player_id: int, data: RoundPlayerUpdate, db: Session = Depends(get_db)):
    rp = db.query(RoundPlayer).filter(RoundPlayer.round_id == round_id, RoundPlayer.player_id == player_id).first()
    if not rp:
        raise HTTPException(404, "Jogador não está nesta rodada.")
    updates = data.model_dump(exclude_none=True)
    if "buyin" in updates or "rebuy" in updates:
        if "buyin" in updates and "rebuy" not in updates:
            # Legacy update payload: buyin represented total entries.
            buyin_norm, rebuy_norm = _normalize_buyin_rebuy(updates.get("buyin"), None)
        else:
            buyin_source = updates.get("buyin", rp.buyin)
            rebuy_source = updates.get("rebuy", rp.rebuy)
            buyin_norm, rebuy_norm = _normalize_buyin_rebuy(buyin_source, rebuy_source)
        updates["buyin"] = buyin_norm
        updates["rebuy"] = rebuy_norm

    for field, value in updates.items():
        setattr(rp, field, value)
    db.commit()
    db.refresh(rp)
    return _to_read(rp)


@router.delete("/{round_id}/players/{player_id}", status_code=204,
               summary="Remover jogador da rodada",
               dependencies=[Depends(require_admin)])
def remove_round_player(round_id: int, player_id: int, db: Session = Depends(get_db)):
    rp = db.query(RoundPlayer).filter(RoundPlayer.round_id == round_id, RoundPlayer.player_id == player_id).first()
    if not rp:
        raise HTTPException(404, "Jogador não está nesta rodada.")
    db.delete(rp)
    db.commit()


# ── Finalize ────────────────────────────────────────────────────────────────

@router.post("/{round_id}/finalize", response_model=FinalizeResult,
             summary="Finalizar rodada",
             dependencies=[Depends(require_admin)])
def finalize_round(round_id: int, db: Session = Depends(get_db)):
    round_ = db.query(Round).filter(Round.id == round_id).first()
    if not round_:
        raise HTTPException(404, "Rodada não encontrada.")
    if round_.is_finalized:
        raise HTTPException(409, "Rodada já foi finalizada.")

    rps = round_.round_players
    if not rps:
        raise HTTPException(400, "Nenhum jogador na rodada.")

    config = db.query(Config).first()
    if not config:
        config = Config()
        db.add(config)
        db.commit()
        db.refresh(config)
    total_buyins = sum(rp.buyin for rp in rps)
    total_rebuys = sum(rp.rebuy or 0 for rp in rps)
    total_addons = sum(rp.addon for rp in rps)
    total_entries_gross = sum(_entry_gross(rp.buyin or 0, rp.rebuy or 0, config) for rp in rps)
    total_entry_fee = sum(_entry_fee(rp.buyin or 0, rp.rebuy or 0) for rp in rps)
    total_addons_value = total_addons * (config.addon_value or 0)
    dealer_fee = _dealer_fee(len(rps))
    base_noite = max(total_entries_gross - total_entry_fee - dealer_fee, 0.0) + total_addons_value
    caixa_noite = max(total_entries_gross + total_addons_value - dealer_fee, 0.0)
    premiacao_total = base_noite * 0.85
    ranking_noite = base_noite * 0.075

    # Calculate pontos from colocacao using the prize pool formula
    for rp in rps:
        rp.pontos = _calc_prize_points(
            rp.colocacao or 0,
            total_buyins,
            total_rebuys,
            total_addons,
            config,
            len(rps),
        )
    db.commit()

    for rp in rps:
        score_val = _calc_total(rp)
        existing = db.query(SemestralScore).filter(
            SemestralScore.player_id == rp.player_id,
            SemestralScore.round_id == round_id,
        ).first()
        if existing:
            existing.score = score_val
        else:
            db.add(SemestralScore(player_id=rp.player_id, round_id=round_id, score=score_val))

    round_.is_finalized = True
    round_.is_current = False
    round_.is_active_in_ranking = True
    db.commit()

    sorted_rps = sorted(rps, key=_calc_total, reverse=True)
    ranking = []
    for i, rp in enumerate(sorted_rps):
        prize = premiacao_total * 0.7 if i == 0 else (premiacao_total * 0.3 if i == 1 else 0.0)
        ranking.append(FinalizeRankingEntry(
            position=i + 1,
            player_id=rp.player_id,
            player_name=rp.player.name,
            total_points=_calc_total(rp),
            prize=prize,
        ))

    return FinalizeResult(
        round_id=round_id,
        round_label=round_.label,
        players_count=len(rps),
        total_buyins=total_buyins,
        total_rebuys=total_rebuys,
        total_addons=total_addons,
        caixa_noite=caixa_noite,
        premiacao_total=premiacao_total,
        ranking_noite=ranking_noite,
        ranking=ranking,
    )
