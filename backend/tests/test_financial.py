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
                json={"player_id": player["id"], "buyin": 1, "rebuy": 1, "addon": 1}, headers=auth)

    r = client.get("/api/financial")
    data = r.json()
    assert data["total_buyins"] == 1
    assert data["total_rebuys"] == 1
    assert data["total_addons"] == 1
    # 100 (buyin) + 80 (rebuy) + 50 (addon) - 50 (taxa dealer, ronda com < 7 jogadores) = 180.0
    assert data["caixa_noite"] == 100.0 + 80.0 + 1 * 50.0 - 50.0


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
    # Sem rodada atual aberta, a última rodada finalizada (Rodada 02) vira "noite"
    # e só a Rodada 01 entra no histórico acumulado.
    #
    # Rodada 01 (histórico): 1 buyin(100) + 1 rebuy(80) = 180 bruto; taxa R$20;
    # taxa dealer R$50 (rodada com < 7 jogadores); base = (180-20-50) + 50(addon) = 160
    # caixa anterior histórico: taxa(20) + 7.5% de 160 = 32.0
    assert data["caixa_anterior"] == 32.0
    # ranking anterior histórico: 7.5% de 160 = 12.0
    assert data["ranking_anterior"] == 12.0

    # Rodada 02 (noite): 1 buyin(100) = 100 bruto; taxa R$10; taxa dealer R$50
    # base = 100 - 10 - 50 = 40; caixa_noite = 100 - 50 = 50
    # caixa_atual = 32.0 (anterior) + 50 (noite) + 7.5% de 40 (3.0) = 85.0
    assert data["caixa_atual"] == 85.0
    # ranking_total = 12.0 (anterior) + 7.5% de 40 (3.0) = 15.0
    assert data["ranking_total"] == 15.0


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
    # Caixa atual (todo o caixa acumulado) desconta as despesas.
    assert data["caixa_atual"] == 1000.0 - 300.0
    # Premiação da noite c/despesas é independente do caixa acumulado:
    # sem rodada nenhuma, a premiação da noite é 0, então fica negativa.
    assert data["caixa_com_despesas"] == 0.0 - 300.0
