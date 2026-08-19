from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..dependencies import require_admin
from ..models import Financial, Expense, Config, Round, RoundPlayer
from ..schemas import (
    FinancialRead, FinancialUpdate, FinancialSummary,
    ExpenseRead, ExpenseCreate, ExpenseUpdate,
)

router = APIRouter(tags=["Financeiro"])

RANKING_PCT_FIXED = 0.075
CAIXA_ANTERIOR_PCT_FIXED = 0.075
ENTRY_FEE = 10.0
DEALER_FEE = 50.0
DEALER_FEE_MIN_PLAYERS = 7


def _get_or_create_financial(db: Session) -> Financial:
    fin = db.query(Financial).first()
    if not fin:
        fin = Financial()
        db.add(fin)
        db.commit()
        db.refresh(fin)
    return fin


def _calc_total(rp: RoundPlayer) -> int:
    return (rp.pontos or 0) + (rp.presenca or 0) + (rp.bonus or 0) + (rp.indicacao or 0) + (rp.pontualidade or 0)


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


def _dealer_fee(num_players: int) -> float:
    return DEALER_FEE if num_players >= DEALER_FEE_MIN_PLAYERS else 0.0


def _round_totals(rps: list[RoundPlayer], config: Config) -> tuple[float, float, float, float]:
    total_addons = sum(rp.addon for rp in rps)
    addons_value = total_addons * (config.addon_value or 0)

    gross_entries = sum(_entry_gross(rp.buyin or 0, rp.rebuy or 0, config) for rp in rps)
    total_fee = sum(_entry_fee(rp.buyin or 0, rp.rebuy or 0) for rp in rps)
    dealer_fee = _dealer_fee(len(rps))
    base_without_fee = max(gross_entries - total_fee - dealer_fee, 0.0) + addons_value
    caixa_total = max(gross_entries + addons_value - dealer_fee, 0.0)
    return caixa_total, base_without_fee, total_fee, dealer_fee


# ── Financial summary ───────────────────────────────────────────────────────

@router.get("/financial", response_model=FinancialSummary, summary="Resumo financeiro da rodada atual",
            tags=["Financeiro"])
def get_financial(db: Session = Depends(get_db)):
    fin = _get_or_create_financial(db)
    config = db.query(Config).first()
    if not config:
        config = Config()
        db.add(config)
        db.commit()
        db.refresh(config)

    current_round = db.query(Round).filter(Round.is_current == True).first()

    all_finalized = db.query(Round).filter(
        Round.is_finalized == True,
        Round.is_current == False,
    ).order_by(Round.id).all()

    if current_round:
        rps: list[RoundPlayer] = current_round.round_players
        historical_rounds = all_finalized
    else:
        # No active round: show last finalized round as "noite", rest as histórico
        last_round = all_finalized[-1] if all_finalized else None
        rps = last_round.round_players if last_round else []
        historical_rounds = all_finalized[:-1] if last_round else []

    total_buyins = sum(rp.buyin or 0 for rp in rps)
    total_rebuys = sum(rp.rebuy or 0 for rp in rps)
    total_addons = sum(rp.addon for rp in rps)

    caixa_noite, base_noite, _, dealer_fee = _round_totals(rps, config)
    premiacao_total = base_noite * 0.85
    ranking_noite = base_noite * RANKING_PCT_FIXED
    caixa_anterior_noite = base_noite * CAIXA_ANTERIOR_PCT_FIXED

    historico_caixa_anterior = 0.0
    historico_ranking = 0.0
    for round_ in historical_rounds:
        _, base_hist, fee_hist, _ = _round_totals(round_.round_players or [], config)
        historico_caixa_anterior += fee_hist + base_hist * CAIXA_ANTERIOR_PCT_FIXED
        historico_ranking += base_hist * RANKING_PCT_FIXED

    total_despesas = sum(e.value for e in db.query(Expense).all())
    caixa_anterior = (fin.caixa_anterior or 0.0) + historico_caixa_anterior
    ranking_anterior = (fin.ranking_anterior or 0.0) + historico_ranking

    caixa_atual = caixa_anterior + caixa_noite + caixa_anterior_noite - total_despesas
    ranking_total = ranking_anterior + ranking_noite
    caixa_com_despesas = premiacao_total - total_despesas

    return FinancialSummary(
        caixa_anterior=caixa_anterior,
        ranking_anterior=ranking_anterior,
        total_buyins=total_buyins,
        total_rebuys=total_rebuys,
        total_addons=total_addons,
        caixa_noite=caixa_noite,
        dealer_fee=dealer_fee,
        caixa_atual=caixa_atual,
        premiacao_total=premiacao_total,
        premiacao_1=premiacao_total * 0.7,
        premiacao_2=premiacao_total * 0.3,
        ranking_noite=ranking_noite,
        ranking_total=ranking_total,
        total_despesas=total_despesas,
        caixa_com_despesas=caixa_com_despesas,
    )


@router.put("/financial", response_model=FinancialRead,
            summary="Atualizar caixa e ranking anteriores",
            tags=["Financeiro"],
            dependencies=[Depends(require_admin)])
def update_financial(data: FinancialUpdate, db: Session = Depends(get_db)):
    fin = _get_or_create_financial(db)
    fin.caixa_anterior = data.caixa_anterior
    fin.ranking_anterior = data.ranking_anterior
    db.commit()
    db.refresh(fin)
    return fin


# ── Expenses ────────────────────────────────────────────────────────────────

@router.get("/expenses", response_model=List[ExpenseRead], summary="Listar todas as despesas",
            tags=["Financeiro"])
def list_expenses(db: Session = Depends(get_db)):
    return db.query(Expense).order_by(Expense.name).all()


@router.post("/expenses", response_model=ExpenseRead, status_code=201,
             summary="Adicionar despesa", tags=["Financeiro"],
             dependencies=[Depends(require_admin)])
def create_expense(data: ExpenseCreate, db: Session = Depends(get_db)):
    if db.query(Expense).filter(Expense.name == data.name).first():
        raise HTTPException(409, f"Despesa '{data.name}' já existe.")
    expense = Expense(name=data.name, value=data.value)
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.put("/expenses/{expense_id}", response_model=ExpenseRead,
            summary="Atualizar despesa", tags=["Financeiro"],
            dependencies=[Depends(require_admin)])
def update_expense(expense_id: int, data: ExpenseUpdate, db: Session = Depends(get_db)):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(404, "Despesa não encontrada.")
    if data.name is not None:
        if db.query(Expense).filter(Expense.name == data.name, Expense.id != expense_id).first():
            raise HTTPException(409, f"Já existe uma despesa com o nome '{data.name}'.")
        expense.name = data.name
    if data.value is not None:
        expense.value = data.value
    db.commit()
    db.refresh(expense)
    return expense


@router.delete("/expenses/{expense_id}", status_code=204, summary="Remover despesa",
               tags=["Financeiro"],
               dependencies=[Depends(require_admin)])
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(404, "Despesa não encontrada.")
    db.delete(expense)
    db.commit()
