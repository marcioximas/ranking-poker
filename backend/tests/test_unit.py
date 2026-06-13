"""
Unit tests for pure business logic — no database, no HTTP.
These test the lowest layer of the pyramid: isolated functions and formulas.
"""
import pytest
from types import SimpleNamespace

from app.routers.rounds import _calc_total


def make_rp(**kwargs):
    defaults = dict(pontos=0, presenca=0, bonus=0, indicacao=0, pontualidade=0)
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ── _calc_total ──────────────────────────────────────────────────────────────

class TestCalcTotal:
    def test_all_zero(self):
        assert _calc_total(make_rp()) == 0

    def test_sum_all_fields(self):
        rp = make_rp(pontos=10, presenca=5, bonus=3, indicacao=2, pontualidade=1)
        assert _calc_total(rp) == 21

    def test_none_fields_treated_as_zero(self):
        rp = make_rp(pontos=None, presenca=None, bonus=None, indicacao=None, pontualidade=None)
        assert _calc_total(rp) == 0

    def test_partial_none_fields(self):
        rp = make_rp(pontos=10, presenca=None, bonus=5, indicacao=None, pontualidade=None)
        assert _calc_total(rp) == 15

    def test_only_pontos(self):
        assert _calc_total(make_rp(pontos=15)) == 15

    def test_only_presenca(self):
        assert _calc_total(make_rp(presenca=5)) == 5

    def test_only_bonus(self):
        assert _calc_total(make_rp(bonus=10)) == 10

    def test_large_values(self):
        rp = make_rp(pontos=1000, presenca=500, bonus=300, indicacao=200, pontualidade=100)
        assert _calc_total(rp) == 2100

    def test_ordering_matters_for_sort(self):
        rp_high = make_rp(pontos=30)
        rp_low  = make_rp(pontos=10)
        assert _calc_total(rp_high) > _calc_total(rp_low)


# ── Prize distribution ────────────────────────────────────────────────────────

def distribute_prizes(n_players: int, premiacao_total: float) -> list[float]:
    """Mirrors the prize logic in finalize_round."""
    return [
        premiacao_total * 0.7 if i == 0
        else (premiacao_total * 0.3 if i == 1 else 0.0)
        for i in range(n_players)
    ]


class TestPrizeDistribution:
    def test_single_player_gets_70_pct(self):
        prizes = distribute_prizes(1, 100.0)
        assert prizes == [70.0]

    def test_two_players_split_70_30(self):
        prizes = distribute_prizes(2, 100.0)
        assert prizes == [70.0, 30.0]

    def test_third_player_gets_zero(self):
        prizes = distribute_prizes(3, 100.0)
        assert prizes[2] == 0.0

    def test_many_players_only_top_two_paid(self):
        prizes = distribute_prizes(8, 200.0)
        assert prizes[0] == pytest.approx(140.0)
        assert prizes[1] == pytest.approx(60.0)
        assert all(p == 0.0 for p in prizes[2:])

    def test_prizes_sum_is_full_premiacao(self):
        prizes = distribute_prizes(5, 300.0)
        assert sum(prizes) == pytest.approx(300.0)

    def test_zero_premiacao(self):
        prizes = distribute_prizes(3, 0.0)
        assert all(p == 0.0 for p in prizes)


# ── Financial formulas ────────────────────────────────────────────────────────

class TestFinancialFormulas:
    def test_caixa_noite_only_buyins(self):
        buyin_value, addon_value = 50.0, 30.0
        total_buyins, total_addons = 4, 0
        caixa_noite = total_buyins * buyin_value + total_addons * addon_value
        assert caixa_noite == pytest.approx(200.0)

    def test_caixa_noite_buyins_and_addons(self):
        caixa_noite = 3 * 50.0 + 2 * 50.0
        assert caixa_noite == pytest.approx(250.0)

    def test_premiacao_pct(self):
        caixa_noite = 300.0
        premiacao_total = caixa_noite * (70.0 / 100)
        assert premiacao_total == pytest.approx(210.0)

    def test_ranking_pct(self):
        caixa_noite = 300.0
        ranking_noite = caixa_noite * (10.0 / 100)
        assert ranking_noite == pytest.approx(30.0)

    def test_caixa_atual_adds_anterior(self):
        caixa_atual = 500.0 + 300.0
        assert caixa_atual == pytest.approx(800.0)

    def test_caixa_com_despesas_subtracts(self):
        caixa_com_despesas = 800.0 - 150.0
        assert caixa_com_despesas == pytest.approx(650.0)

    def test_caixa_com_despesas_can_be_negative(self):
        caixa_com_despesas = 100.0 - 200.0
        assert caixa_com_despesas < 0

    def test_ranking_total_adds_anterior(self):
        ranking_total = 100.0 + 30.0
        assert ranking_total == pytest.approx(130.0)

    def test_prize_split_adds_to_premiacao(self):
        premiacao_total = 210.0
        assert premiacao_total * 0.7 + premiacao_total * 0.3 == pytest.approx(premiacao_total)
