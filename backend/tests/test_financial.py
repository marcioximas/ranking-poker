def test_get_financial_returns_summary(client):
    r = client.get("/api/financial")
    assert r.status_code == 200
    data = r.json()
    # All zero with no current round and no config
    assert "caixa_anterior" in data
    assert "caixa_noite" in data
    assert "premiacao_total" in data


def test_financial_summary_with_no_round(client):
    r = client.get("/api/financial")
    data = r.json()
    assert data["total_buyins"] == 0
    assert data["caixa_noite"] == 0.0


def test_update_financial_requires_auth(client):
    r = client.put("/api/financial", json={"caixa_anterior": 1000, "ranking_anterior": 500})
    assert r.status_code == 401


def test_update_financial(client, auth):
    r = client.put("/api/financial",
                   json={"caixa_anterior": 2000.0, "ranking_anterior": 800.0},
                   headers=auth)
    assert r.status_code == 200
    data = r.json()
    assert data["caixa_anterior"] == 2000.0
    assert data["ranking_anterior"] == 800.0


def test_ranking_withdrawal_only_reduces_ranking_money(client, auth):
    client.put("/api/financial", json={"caixa_anterior": 300, "ranking_anterior": 500}, headers=auth)
    before = client.get("/api/financial").json()
    scores_before = client.get("/api/ranking").json()

    payload = {"name": "Churrasco", "value": 100}
    assert client.post("/api/ranking-withdrawals", json=payload).status_code == 401
    response = client.post("/api/ranking-withdrawals", json=payload, headers=auth)
    assert response.status_code == 201
    assert client.post("/api/ranking-withdrawals", json=payload, headers=auth).status_code == 409

    after = client.get("/api/financial").json()
    assert after["ranking_total"] == before["ranking_total"] - 100
    assert after["ranking_anterior"] == before["ranking_anterior"]
    assert after["total_ranking_withdrawals"] == 100
    assert after["ranking_withdrawals"] == [response.json()]
    assert after["caixa_total"] == before["caixa_total"]
    assert after["total_despesas"] == before["total_despesas"]
    assert client.get("/api/ranking").json() == scores_before


def test_ranking_withdrawal_rejects_empty_name_and_invalid_value(client, auth):
    for payload in [
        {"name": " ", "value": 100},
        {"name": "Churrasco", "value": 0},
        {"name": "Churrasco", "value": -1},
    ]:
        assert client.post("/api/ranking-withdrawals", json=payload, headers=auth).status_code == 422
    assert client.get("/api/financial").json()["ranking_withdrawals"] == []


def test_financial_caixa_includes_round_buyin(client, auth, player, current_round):
    client.put("/api/config",
               json={"buyin_value": 100.0, "rebuy_value": 80.0, "addon_value": 50.0, "tournament_name": "T",
                     "presence_points": 10, "punctuality_points": 15, "itm_bonus_points": 5,
                     "prize_pct": 70, "ranking_pct": 30}, headers=auth)
    client.post(f"/api/rounds/{current_round['id']}/players",
                json={"player_id": player["id"], "buyin": 1, "rebuy": 1, "addon": 1}, headers=auth)

    r = client.get("/api/financial")
    data = r.json()
    assert data["total_buyins"] == 1
    assert data["total_rebuys"] == 1
    assert data["total_addons"] == 1
    assert data["total_arrecadado_bruto"] == 230.0
    # Taxa de R$10; base = R$220; caixa = taxa + 7,5% da base.
    assert data["caixa_noite"] == 10.0 + 220.0 * 0.075
    assert data["ranking_noite"] == 220.0 * 0.075
    assert data["premiacao_total"] == 220.0 * 0.85


def test_financial_accumulates_historical_rounds_in_previous_fields(client, auth):
    client.put(
        "/api/financial",
        json={"caixa_anterior": 0.0, "ranking_anterior": 0.0},
        headers=auth,
    )

    client.put(
        "/api/config",
        json={
            "buyin_value": 100.0,
            "rebuy_value": 80.0,
            "addon_value": 50.0,
            "tournament_name": "T",
            "presence_points": 10,
            "punctuality_points": 15,
            "itm_bonus_points": 5,
            "prize_pct": 70,
            "ranking_pct": 15,
        },
        headers=auth,
    )

    p1 = client.post("/api/players", json={"name": "Jogador 1"}, headers=auth).json()
    p2 = client.post("/api/players", json={"name": "Jogador 2"}, headers=auth).json()

    r1 = client.post("/api/rounds", json={"label": "Rodada 01"}, headers=auth).json()
    r2 = client.post("/api/rounds", json={"label": "Rodada 02"}, headers=auth).json()

    client.post(
        f"/api/rounds/{r1['id']}/players",
        json={"player_id": p1["id"], "buyin": 1, "rebuy": 1, "addon": 1},
        headers=auth,
    )
    client.post(
        f"/api/rounds/{r2['id']}/players",
        json={"player_id": p2["id"], "buyin": 1, "addon": 0},
        headers=auth,
    )

    data = client.get("/api/financial").json()
    # Sem rodada atual aberta, todas as rodadas finalizadas (01 e 02) já entram
    # no acumulado assim que fecham — a Rodada 02 só é exibida como "noite" para
    # fins informativos, sem contar de novo (evita duplicidade).
    #
    # Rodada 01: bruto = 100 + 80 + 50(addon) = 230; taxa de R$10;
    # base = 220; caixa recebe 10 + 7,5% da base = 26.50.
    #
    # Rodada 02: bruto = 100; taxa de R$10; base = 90;
    # caixa recebe 10 + 7,5% da base = 16.75.
    #
    # caixa_anterior = 26.50 (só Rodada 01; a 02 fica separada em caixa_noite)
    # ranking_anterior = 16.50 (só Rodada 01; a 02 fica de fora do "anterior" e
    # aparece separada em ranking_noite, para anterior + noite = total)
    assert data["caixa_anterior"] == 26.5
    assert data["ranking_anterior"] == 16.5

    # Caixa total = anterior + noite - despesas, sem duplicidade.
    assert data["caixa_total"] == 43.25
    assert data["caixa_atual"] == 43.25
    assert data["caixa_noite"] == 16.75
    assert data["ranking_noite"] == 6.75
    assert data["ranking_total"] == 23.25


# ── Expenses ────────────────────────────────────────────────────────────────

def test_list_expenses_empty(client):
    r = client.get("/api/expenses")
    assert r.status_code == 200
    assert r.json() == []


def test_create_expense(client, auth):
    r = client.post("/api/expenses", json={"name": "Mesa", "value": 800.0}, headers=auth)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Mesa"
    assert data["value"] == 800.0


def test_create_duplicate_expense_returns_409(client, auth):
    client.post("/api/expenses", json={"name": "Mesa", "value": 800.0}, headers=auth)
    r = client.post("/api/expenses", json={"name": "Mesa", "value": 100.0}, headers=auth)
    assert r.status_code == 409


def test_update_expense(client, auth):
    e = client.post("/api/expenses", json={"name": "Mesa", "value": 800.0},
                    headers=auth).json()
    r = client.put(f"/api/expenses/{e['id']}", json={"value": 900.0}, headers=auth)
    assert r.status_code == 200
    assert r.json()["value"] == 900.0


def test_delete_expense(client, auth):
    e = client.post("/api/expenses", json={"name": "Dealer", "value": 50.0},
                    headers=auth).json()
    r = client.delete(f"/api/expenses/{e['id']}", headers=auth)
    assert r.status_code == 204
    assert client.get("/api/expenses").json() == []


def test_expenses_affect_financial_summary(client, auth):
    client.put("/api/financial",
               json={"caixa_anterior": 1000.0, "ranking_anterior": 0}, headers=auth)
    client.post("/api/expenses", json={"name": "Dealer", "value": 300.0}, headers=auth)

    data = client.get("/api/financial").json()
    assert data["total_despesas"] == 300.0
    # As despesas abatam somente no total, não no caixa anterior.
    assert data["caixa_anterior"] == 1000.0
    assert data["caixa_total"] == 1000.0 - 300.0
    assert data["caixa_atual"] == 1000.0 - 300.0
    # Despesas abatam somente do caixa acumulado, nunca da premiação.
    assert data["premiacao_total"] == 0.0


def test_financial_round_in_progress_adds_caixa_contribution(client, auth, player, current_round):
    client.put("/api/financial",
               json={"caixa_anterior": 0.0, "ranking_anterior": 0.0}, headers=auth)
    client.put("/api/config",
               json={"buyin_value": 100.0, "rebuy_value": 80.0, "addon_value": 50.0, "tournament_name": "T",
                     "presence_points": 10, "punctuality_points": 15, "itm_bonus_points": 5,
                     "prize_pct": 70, "ranking_pct": 30}, headers=auth)
    client.post(f"/api/rounds/{current_round['id']}/players",
                json={"player_id": player["id"], "buyin": 1, "rebuy": 0, "addon": 0}, headers=auth)

    data = client.get("/api/financial").json()
    # Rodada em aberto: taxa de R$10 + 7,5% da base (R$90).
    assert data["caixa_noite"] == 16.75
    assert data["caixa_anterior"] == 0.0
    assert data["caixa_total"] == 16.75
    assert data["caixa_atual"] == 16.75
    assert data["ranking_noite"] == 6.75
    assert data["ranking_total"] == 6.75


def test_financial_caixa_contribution_deducts_dealer_fee(client, auth, current_round):
    client.put("/api/financial",
               json={"caixa_anterior": 0.0, "ranking_anterior": 0.0}, headers=auth)
    client.put("/api/config",
               json={"buyin_value": 100.0, "rebuy_value": 80.0, "addon_value": 50.0, "tournament_name": "T",
                     "presence_points": 10, "punctuality_points": 15, "itm_bonus_points": 5,
                     "prize_pct": 70, "ranking_pct": 30}, headers=auth)

    for index in range(7):
        player = client.post("/api/players", json={"name": f"Jogador {index}"}, headers=auth).json()
        client.post(f"/api/rounds/{current_round['id']}/players",
                    json={"player_id": player["id"], "buyin": 1}, headers=auth)

    data = client.get("/api/financial").json()
    # Base = 700 - 70 de taxa; caixa = 70 + 7,5% da base - 50 do dealer.
    assert data["dealer_fee"] == 50.0
    assert data["caixa_noite"] == 67.25
