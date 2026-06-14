from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import date as Date


# ── Config ─────────────────────────────────────────────────────────────────

class ConfigUpdate(BaseModel):
    tournament_name: str = "Poker Night"
    buyin_value: float = Field(50.0, ge=0)
    addon_value: float = Field(50.0, ge=0)
    presence_points: int = Field(10, ge=0)
    punctuality_points: int = Field(15, ge=0)
    itm_bonus_points: int = Field(5, ge=0)
    prize_pct: float = Field(70.0, ge=0, le=100)
    ranking_pct: float = Field(30.0, ge=0, le=100)
    pix_receiver_player_id: Optional[int] = None


class ConfigRead(ConfigUpdate):
    id: int

    class Config:
        from_attributes = True


# ── Player ─────────────────────────────────────────────────────────────────

class PlayerCreate(BaseModel):
    name: str = Field(..., min_length=1)
    telefone: Optional[str] = None
    pix: Optional[str] = None


class PlayerUpdate(BaseModel):
    name: str = Field(..., min_length=1)
    telefone: Optional[str] = None
    pix: Optional[str] = None


class PlayerRead(BaseModel):
    id: int
    name: str
    telefone: Optional[str] = None
    pix: Optional[str] = None

    class Config:
        from_attributes = True


# ── Round ──────────────────────────────────────────────────────────────────

class RoundCreate(BaseModel):
    label: Optional[str] = None
    date: Optional[Date] = None


class RoundUpdate(BaseModel):
    label: Optional[str] = None
    date: Optional[Date] = None
    is_active_in_ranking: Optional[bool] = None


class RoundRead(BaseModel):
    id: int
    label: str
    date: Optional[Date]
    is_active_in_ranking: bool
    is_current: bool
    is_finalized: bool

    class Config:
        from_attributes = True


# ── Round Players ──────────────────────────────────────────────────────────

class RoundPlayerCreate(BaseModel):
    player_id: int
    buyin: int = Field(1, ge=0)
    addon: int = Field(0, ge=0)
    colocacao: int = Field(0, ge=0)
    pontos: int = Field(0, ge=0)
    presenca: int = Field(0, ge=0)
    bonus: int = Field(0, ge=0)
    indicacao: int = Field(0, ge=0)
    pontualidade: int = Field(0, ge=0)


class RoundPlayerUpdate(BaseModel):
    buyin: Optional[int] = Field(None, ge=0)
    addon: Optional[int] = Field(None, ge=0)
    colocacao: Optional[int] = Field(None, ge=0)
    pontos: Optional[int] = Field(None, ge=0)
    presenca: Optional[int] = Field(None, ge=0)
    bonus: Optional[int] = Field(None, ge=0)
    indicacao: Optional[int] = Field(None, ge=0)
    pontualidade: Optional[int] = Field(None, ge=0)


class RoundPlayerRead(BaseModel):
    id: int
    round_id: int
    player_id: int
    player_name: str
    buyin: int
    addon: int
    colocacao: int
    pontos: int
    presenca: int
    bonus: int
    indicacao: int
    pontualidade: int
    total: int


# ── Semestral Ranking ──────────────────────────────────────────────────────

class SemestralScoreUpdate(BaseModel):
    score: int = Field(..., ge=0)


class SemestralScoreRead(BaseModel):
    player_id: int
    round_id: int
    score: int


class RankingRow(BaseModel):
    player_id: int
    player_name: str
    scores: Dict[int, int]
    total: int


class RankingResponse(BaseModel):
    rounds: List[RoundRead]
    active_round_ids: List[int]
    rows: List[RankingRow]


class ActiveRoundsUpdate(BaseModel):
    round_ids: List[int]


# ── Financial ──────────────────────────────────────────────────────────────

class FinancialUpdate(BaseModel):
    caixa_anterior: float = Field(0.0, ge=0)
    ranking_anterior: float = Field(0.0, ge=0)


class FinancialRead(BaseModel):
    caixa_anterior: float
    ranking_anterior: float

    class Config:
        from_attributes = True


class FinancialSummary(BaseModel):
    caixa_anterior: float
    ranking_anterior: float
    total_buyins: int
    total_addons: int
    caixa_noite: float
    caixa_atual: float
    premiacao_total: float
    premiacao_1: float
    premiacao_2: float
    ranking_noite: float
    ranking_total: float
    total_despesas: float
    caixa_com_despesas: float


# ── Expenses ───────────────────────────────────────────────────────────────

class ExpenseCreate(BaseModel):
    name: str = Field(..., min_length=1)
    value: float = Field(0.0, ge=0)


class ExpenseUpdate(BaseModel):
    name: Optional[str] = None
    value: Optional[float] = Field(None, ge=0)


class ExpenseRead(BaseModel):
    id: int
    name: str
    value: float

    class Config:
        from_attributes = True


# ── Auth ───────────────────────────────────────────────────────────────────

class PasswordVerify(BaseModel):
    password: str


class AuthResponse(BaseModel):
    valid: bool


# ── Finalize Result ────────────────────────────────────────────────────────

class FinalizeRankingEntry(BaseModel):
    position: int
    player_id: int
    player_name: str
    total_points: int
    prize: float


class FinalizeResult(BaseModel):
    round_id: int
    round_label: str
    players_count: int
    total_buyins: int
    total_addons: int
    caixa_noite: float
    premiacao_total: float
    ranking_noite: float
    ranking: List[FinalizeRankingEntry]
