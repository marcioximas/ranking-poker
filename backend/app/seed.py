from sqlalchemy.orm import Session
from datetime import date
from .models import Config, Financial, Expense, Player, Round, SemestralScore

SEED_ROUNDS = [
    {"label": "Rodada 1 - 08/10",  "date": date(2025, 10,  8)},
    {"label": "Rodada 2 - 05/11",  "date": date(2025, 11,  5)},
    {"label": "Rodada 3 - 19/11",  "date": date(2025, 11, 19)},
    {"label": "Rodada 4 - 10/12",  "date": date(2025, 12, 10)},
    {"label": "Rodada 5 - 14/01",  "date": date(2026,  1, 14)},
    {"label": "Rodada 6 - 28/01",  "date": date(2026,  1, 28)},
    {"label": "Rodada 7 - 11/02",  "date": date(2026,  2, 11)},
    {"label": "Rodada 8 - 25/02",  "date": date(2026,  2, 25)},
    {"label": "Rodada 9 - 11/03",  "date": date(2026,  3, 11)},
    {"label": "Rodada 10 - 25/03", "date": date(2026,  3, 25)},
    {"label": "Rodada 11 - 08/04", "date": date(2026,  4,  8)},
    {"label": "Rodada 12 - 22/04", "date": date(2026,  4, 22)},
    {"label": "Rodada 13 - 06/05", "date": date(2026,  5,  6)},
    {"label": "Rodada 14 - 20/05", "date": date(2026,  5, 20)},
    {"label": "Rodada 15 - 03/06", "date": date(2026,  6,  3)},
    {"label": "Rodada 16 - 17/06", "date": date(2026,  6, 17)},
    {"label": "Rodada 17 - 22/06", "date": date(2026,  6, 22)},
    {"label": "Rodada 18 - 06/07", "date": date(2026,  7,  6)},
    {"label": "Rodada 19 - 13/07", "date": date(2026,  7, 13)},
]

SEED_SEMESTRAL = {
    "Mateus":        [100, 85, 55, 90, 75, 80, 95, 70, 85, 55, 90, 100, 53, 25, 95, 85,  0,  0,  0],
    "Henrique":      [ 80, 70, 25, 70, 60, 55, 80, 65, 70, 25, 75,  85, 25, 25, 25, 25,  0,  0,  0],
    "China":         [ 90, 95, 85, 80, 70, 75, 90, 80, 75, 45, 80,  90, 25, 25, 25,158,  0,  0,  0],
    "Ximas":         [ 60, 50, 40, 55, 45, 50, 65, 55, 50, 68,122,  45, 10,  0,  0,  0,  0,  0,  0],
    "Deivid":        [ 55, 60, 50, 60, 55, 50, 70, 60, 55, 45, 45,  50, 25, 25,  0,  0,  0,  0,  0],
    "Morais":        [ 40, 45, 35, 45, 40, 35, 55, 45, 40, 25, 25,   0, 25,  0,  0,  0,  0,  0,  0],
    "Danilo Vieira": [ 35, 40, 30, 40, 35, 30, 50, 40, 35, 25, 77,  25, 25,  0,  0,  0,  0,  0,  0],
    "Andre":         [  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 45,  25,  0,  0,  0,  0,  0,  0,  0],
    "Joel":          [  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,  25,  0,  0,  0,  0,  0,  0,  0],
    "Rafael":        [ 25, 25,  0,  0,  0,  0,  0,  0,  0,  0,  0,   0,  0,  0,  0,  0,  0,  0,  0],
    "Marcelo":       [  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,   0,  0,  0,  0,  0,  0,  0,  0],
    "Chamma":        [  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,   0, 25,  0,  0,  0,  0,  0,  0],
    "Comando":       [  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  45,  0,  0,  0,  0,  0,  0,  0],
    "Para":          [  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,   0,  0,  0,  0,  0,  0,  0,  0],
    "Cicero":        [  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,   0,  0,  0,  0,  0,  0,  0,  0],
    "Claudinho":     [  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 25,   0,  0,  0,  0,  0,  0,  0,  0],
}

SEED_EXPENSES = {
    "Dealer": 50.0,
    "Maleta": 900.0,
    "Mesa": 800.0,
    "Lavagem Mesa": 130.0,
    "Cadeiras": 1120.0,
    "Baralho": 90.0,
    "TV c/ Suporte": 1025.0,
    "Câmera": 337.0,
}


def seed_db(db: Session) -> None:
    if db.query(Config).first():
        return  # already seeded

    db.add(Config())
    db.add(Financial(caixa_anterior=3868.23, ranking_anterior=1621.25))
    for name, value in SEED_EXPENSES.items():
        db.add(Expense(name=name, value=value))
    db.flush()

    rounds: list[Round] = []
    for i, r in enumerate(SEED_ROUNDS):
        round_ = Round(
            label=r["label"],
            date=r["date"],
            is_active_in_ranking=(i >= 16),  # last 3: ids 17,18,19
            is_finalized=True,
            is_current=False,
        )
        db.add(round_)
        rounds.append(round_)
    db.flush()

    for player_name, scores in SEED_SEMESTRAL.items():
        player = Player(name=player_name)
        db.add(player)
        db.flush()
        for idx, score in enumerate(scores):
            if idx < len(rounds):
                db.add(SemestralScore(
                    player_id=player.id,
                    round_id=rounds[idx].id,
                    score=score,
                ))

    db.commit()
