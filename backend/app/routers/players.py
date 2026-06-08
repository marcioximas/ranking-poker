from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..dependencies import require_admin
from ..models import Player
from ..schemas import PlayerRead, PlayerCreate, PlayerUpdate

router = APIRouter(prefix="/players", tags=["Jogadores"])


@router.get("", response_model=List[PlayerRead], summary="Listar todos os jogadores cadastrados")
def list_players(db: Session = Depends(get_db)):
    return db.query(Player).order_by(Player.name).all()


@router.get("/{player_id}", response_model=PlayerRead, summary="Buscar jogador por ID")
def get_player(player_id: int, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(404, "Jogador não encontrado.")
    return player


@router.post("", response_model=PlayerRead, status_code=201, summary="Cadastrar novo jogador",
             dependencies=[Depends(require_admin)])
def create_player(data: PlayerCreate, db: Session = Depends(get_db)):
    if db.query(Player).filter(Player.name == data.name).first():
        raise HTTPException(409, f"Jogador '{data.name}' já existe.")
    player = Player(name=data.name)
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


@router.put("/{player_id}", response_model=PlayerRead, summary="Atualizar nome do jogador",
            dependencies=[Depends(require_admin)])
def update_player(player_id: int, data: PlayerUpdate, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(404, "Jogador não encontrado.")
    if db.query(Player).filter(Player.name == data.name, Player.id != player_id).first():
        raise HTTPException(409, f"Já existe outro jogador com o nome '{data.name}'.")
    player.name = data.name
    db.commit()
    db.refresh(player)
    return player


@router.delete("/{player_id}", status_code=204, summary="Remover jogador",
               description="Remove o jogador e todos os seus dados de rodadas e ranking.",
               dependencies=[Depends(require_admin)])
def delete_player(player_id: int, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(404, "Jogador não encontrado.")
    db.delete(player)
    db.commit()
