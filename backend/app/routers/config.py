from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import require_admin
from ..models import Config
from ..schemas import ConfigRead, ConfigUpdate

router = APIRouter(prefix="/config", tags=["Configurações"])


def _get_or_create(db: Session) -> Config:
    config = db.query(Config).first()
    if not config:
        config = Config()
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.get("", response_model=ConfigRead, summary="Buscar configurações do torneio")
def get_config(db: Session = Depends(get_db)):
    return _get_or_create(db)


@router.put("", response_model=ConfigRead, summary="Atualizar configurações do torneio",
            dependencies=[Depends(require_admin)])
def update_config(data: ConfigUpdate, db: Session = Depends(get_db)):
    config = _get_or_create(db)
    for key, value in data.model_dump().items():
        setattr(config, key, value)
    db.commit()
    db.refresh(config)
    return config
