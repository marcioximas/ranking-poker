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


def test_financial_caixa_includes_round_buyin(client, auth, player, current_round):
    client.put("/api/config",
               json={"buyin_value": 100.0, "rebuy_value": 80.0, "addon_value": 50.0, "tournament_name": "T",
                     "presence_points": 10, "punctuality_points": 15, "itm_bonus_points": 5,
                     "prize_pct": 70, "ranking_pct": 30}, headers=auth)
    client.post(f"/api/rounds/{current_round['id']}/players",
                json={"player_id": player["id"], "buyin": 2, "addon": 1}, headers=auth)

    r = client.get("/api/financial")
    data = r.json()
    assert data["total_buyins"] == 2
    assert data["total_addons"] == 1
    assert data["caixa_noite"] == 100.0 + 80.0 + 1 * 50.0  # 230.0


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
    assert data["caixa_com_despesas"] == 1000.0 - 300.0
