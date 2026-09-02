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
    # 100 (buyin) + 80 (rebuy) + 50 (addon); só 1 jogador, sem taxa de dealer (regra é 7+)
    assert data["caixa_noite"] == 100.0 + 80.0 + 1 * 50.0


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
    # Rodada 01: 1 buyin(100) + 1 rebuy(80) = 180 bruto; taxa R$10
    # (R$10 por jogador que fez buy-in, não por rebuy);
    # sem taxa de dealer (só 1 jogador, regra é 7+); base = (180-10) + 50(addon) = 220
    # contribuição p/ caixa: taxa(10) + 7.5% de 220 = 26.5; p/ ranking: 7.5% de 220 = 16.5
    #
    # Rodada 02: 1 buyin(100) = 100 bruto; taxa R$10; sem taxa de dealer
    # base = 100 - 10 = 90
    # contribuição p/ caixa: taxa(10) + 7.5% de 90 (6.75) = 16.75; p/ ranking: 6.75
    #
    # caixa_anterior = 26.5 + 16.75 = 43.25 (fecha e entra na hora, sem duplicidade)
    # ranking_anterior = 16.5 (só Rodada 01; a 02 fica de fora do "anterior" e
    # aparece separada em ranking_noite, para anterior + noite = total)
    assert data["caixa_anterior"] == 43.25
    assert data["ranking_anterior"] == 16.5

    # Sem rodada em aberto, caixa_atual não soma nada extra da "noite", mas o
    # ranking sempre soma ranking_noite (que nunca está em ranking_anterior).
    assert data["caixa_atual"] == 43.25
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
    # As despesas abatem diretamente do caixa anterior.
    assert data["caixa_anterior"] == 1000.0 - 300.0
    assert data["caixa_atual"] == 1000.0 - 300.0
    # Premiação da noite c/despesas é independente do caixa acumulado:
    # sem rodada nenhuma, a premiação da noite é 0, então fica negativa.
    assert data["caixa_com_despesas"] == 0.0 - 300.0


def test_financial_round_in_progress_adds_full_pot_to_caixa(client, auth, player, current_round):
    client.put("/api/financial",
               json={"caixa_anterior": 0.0, "ranking_anterior": 0.0}, headers=auth)
    client.put("/api/config",
               json={"buyin_value": 100.0, "rebuy_value": 80.0, "addon_value": 50.0, "tournament_name": "T",
                     "presence_points": 10, "punctuality_points": 15, "itm_bonus_points": 5,
                     "prize_pct": 70, "ranking_pct": 30}, headers=auth)
    client.post(f"/api/rounds/{current_round['id']}/players",
                json={"player_id": player["id"], "buyin": 1, "rebuy": 0, "addon": 0}, headers=auth)

    data = client.get("/api/financial").json()
    # Rodada em aberto (não finalizada): o pote inteiro (100, sem taxa de dealer)
    # ainda está fisicamente no caixa, então soma integralmente ao caixa_atual.
    assert data["caixa_noite"] == 100.0
    assert data["caixa_anterior"] == 0.0
    assert data["caixa_atual"] == 100.0
    # base = 100 - 10 (taxa) = 90; ranking_noite (pendente) = 7.5% de 90 = 6.75
    assert data["ranking_noite"] == 6.75
    assert data["ranking_total"] == 6.75
