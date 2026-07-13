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


def _entry_amount(entries: int, config: Config) -> float:
    if entries <= 0:
        return 0.0
    buyin_value = config.buyin_value or 0
    rebuy_value = getattr(config, "rebuy_value", None)
    if rebuy_value is None:
        rebuy_value = buyin_value
    return buyin_value + max(entries - 1, 0) * rebuy_value


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
    rps: list[RoundPlayer] = current_round.round_players if current_round else []

    total_buyins = sum(rp.buyin for rp in rps)
    total_addons = sum(rp.addon for rp in rps)
    caixa_noite = sum(_entry_amount(rp.buyin, config) for rp in rps) + total_addons * config.addon_value
    premiacao_total = caixa_noite * (config.prize_pct / 100)
    ranking_noite = caixa_noite * (config.ranking_pct / 100)

    total_despesas = sum(e.value for e in db.query(Expense).all())
    caixa_anterior = fin.caixa_anterior
    ranking_anterior = 0.0

    caixa_atual = caixa_anterior + caixa_noite
    ranking_total = ranking_anterior + ranking_noite
    caixa_com_despesas = caixa_atual - total_despesas

    return FinancialSummary(
        caixa_anterior=caixa_anterior,
        ranking_anterior=ranking_anterior,
        total_buyins=total_buyins,
        total_addons=total_addons,
        caixa_noite=caixa_noite,
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
