from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..dependencies import require_admin
from ..models import Round, Player, SemestralScore
from ..schemas import (
    RankingResponse, RankingRow, RoundRead,
    SemestralScoreRead, SemestralScoreUpdate,
    ActiveRoundsUpdate,
)

router = APIRouter(prefix="/ranking", tags=["Ranking Semestral"])


@router.get("", response_model=RankingResponse, summary="Buscar ranking semestral completo")
def get_ranking(db: Session = Depends(get_db)):
    rounds = db.query(Round).filter(Round.is_finalized == True).order_by(Round.id).all()
    active_ids = [r.id for r in rounds if r.is_active_in_ranking]
    players = db.query(Player).all()

    score_index: dict[tuple, int] = {
        (s.player_id, s.round_id): s.score
        for s in db.query(SemestralScore).all()
    }

    rows = []
    for player in players:
        scores = {r.id: score_index.get((player.id, r.id), 0) for r in rounds}
        total = sum(scores.get(rid, 0) for rid in active_ids)
        rows.append(RankingRow(
            player_id=player.id,
            player_name=player.name,
            scores=scores,
            total=total,
        ))

    rows.sort(key=lambda r: r.total, reverse=True)

    return RankingResponse(
        rounds=[RoundRead.model_validate(r) for r in rounds],
        active_round_ids=active_ids,
        rows=rows,
    )


@router.put("/active-rounds", summary="Definir rodadas visíveis no ranking",
            dependencies=[Depends(require_admin)])
def set_active_rounds(data: ActiveRoundsUpdate, db: Session = Depends(get_db)):
    rounds = db.query(Round).filter(Round.is_finalized == True).all()
    for r in rounds:
        r.is_active_in_ranking = r.id in data.round_ids
    db.commit()
    return {"active_round_ids": data.round_ids}


@router.put("/{player_id}/{round_id}", response_model=SemestralScoreRead,
            summary="Editar pontuação de um jogador em uma rodada",
            dependencies=[Depends(require_admin)])
def update_score(player_id: int, round_id: int, data: SemestralScoreUpdate, db: Session = Depends(get_db)):
    if not db.query(Player).filter(Player.id == player_id).first():
        raise HTTPException(404, "Jogador não encontrado.")
    if not db.query(Round).filter(Round.id == round_id).first():
        raise HTTPException(404, "Rodada não encontrada.")

    score = db.query(SemestralScore).filter(
        SemestralScore.player_id == player_id,
        SemestralScore.round_id == round_id,
    ).first()

    if score:
        score.score = data.score
    else:
        score = SemestralScore(player_id=player_id, round_id=round_id, score=data.score)
        db.add(score)

    db.commit()
    db.refresh(score)
    return SemestralScoreRead(player_id=score.player_id, round_id=score.round_id, score=score.score)
