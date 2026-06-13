import pytest


# ── Round CRUD ──────────────────────────────────────────────────────────────

def test_list_rounds_empty(client):
    r = client.get("/api/rounds")
    assert r.status_code == 200
    assert r.json() == []


def test_get_current_round_when_none(client):
    r = client.get("/api/rounds/current")
    assert r.status_code == 200
    assert r.json() is None


def test_start_current_round(client, auth):
    r = client.post("/api/rounds/current", json={"label": "Rodada 1"}, headers=auth)
    assert r.status_code == 201
    data = r.json()
    assert data["label"] == "Rodada 1"
    assert data["is_current"] is True
    assert data["is_finalized"] is False


def test_start_round_requires_auth(client):
    r = client.post("/api/rounds/current", json={"label": "X"})
    assert r.status_code == 401


def test_start_second_current_round_returns_409(client, auth, current_round):
    r = client.post("/api/rounds/current", json={"label": "Duplicada"}, headers=auth)
    assert r.status_code == 409


def test_get_current_round(client, auth, current_round):
    r = client.get("/api/rounds/current")
    assert r.status_code == 200
    assert r.json()["id"] == current_round["id"]


def test_create_historical_round(client, auth):
    r = client.post("/api/rounds", json={"label": "Rodada Hist.", "date": "2025-10-08"},
                    headers=auth)
    assert r.status_code == 201
    data = r.json()
    assert data["is_finalized"] is True
    assert data["is_current"] is False
    assert data["is_active_in_ranking"] is True


def test_create_historical_round_requires_auth(client):
    r = client.post("/api/rounds", json={"label": "X"})
    assert r.status_code == 401


def test_auto_label_when_not_provided(client, auth):
    r = client.post("/api/rounds/current", json={}, headers=auth)
    assert r.status_code == 201
    assert r.json()["label"].startswith("Rodada")


def test_update_round(client, auth, current_round):
    r = client.put(f"/api/rounds/{current_round['id']}",
                   json={"label": "Atualizada"}, headers=auth)
    assert r.status_code == 200
    assert r.json()["label"] == "Atualizada"


def test_delete_round(client, auth, current_round):
    r = client.delete(f"/api/rounds/{current_round['id']}", headers=auth)
    assert r.status_code == 204
    assert client.get("/api/rounds/current").json() is None


def test_get_nonexistent_round_returns_404(client):
    r = client.get("/api/rounds/9999")
    assert r.status_code == 404


# ── Round Players ───────────────────────────────────────────────────────────

def test_add_player_to_round(client, auth, current_round, player):
    r = client.post(f"/api/rounds/{current_round['id']}/players",
                    json={"player_id": player["id"], "buyin": 2, "addon": 1},
                    headers=auth)
    assert r.status_code == 201
    data = r.json()
    assert data["player_id"] == player["id"]
    assert data["buyin"] == 2
    assert data["addon"] == 1


def test_add_duplicate_player_to_round_returns_409(client, auth, current_round, player):
    payload = {"player_id": player["id"]}
    client.post(f"/api/rounds/{current_round['id']}/players", json=payload, headers=auth)
    r = client.post(f"/api/rounds/{current_round['id']}/players", json=payload, headers=auth)
    assert r.status_code == 409


def test_update_round_player(client, auth, current_round, player):
    client.post(f"/api/rounds/{current_round['id']}/players",
                json={"player_id": player["id"]}, headers=auth)
    r = client.put(f"/api/rounds/{current_round['id']}/players/{player['id']}",
                   json={"pontos": 500, "presenca": 10}, headers=auth)
    assert r.status_code == 200
    data = r.json()
    assert data["pontos"] == 500
    assert data["presenca"] == 10
    assert data["total"] == 510


def test_remove_player_from_round(client, auth, current_round, player):
    client.post(f"/api/rounds/{current_round['id']}/players",
                json={"player_id": player["id"]}, headers=auth)
    r = client.delete(f"/api/rounds/{current_round['id']}/players/{player['id']}",
                      headers=auth)
    assert r.status_code == 204


def test_list_round_players_sorted_by_total(client, auth, current_round):
    for name, pontos in [("Alpha", 100), ("Beta", 300), ("Gamma", 200)]:
        p = client.post("/api/players", json={"name": name}, headers=auth).json()
        client.post(f"/api/rounds/{current_round['id']}/players",
                    json={"player_id": p["id"], "pontos": pontos}, headers=auth)

    r = client.get(f"/api/rounds/{current_round['id']}/players")
    assert r.status_code == 200
    totals = [rp["total"] for rp in r.json()]
    assert totals == sorted(totals, reverse=True)


# ── Finalize ────────────────────────────────────────────────────────────────

def test_finalize_round(client, auth, current_round, player):
    client.post(f"/api/rounds/{current_round['id']}/players",
                json={"player_id": player["id"], "buyin": 1, "pontos": 100,
                      "presenca": 10, "pontualidade": 15}, headers=auth)
    # Ensure config exists
    client.get("/api/config")

    r = client.post(f"/api/rounds/{current_round['id']}/finalize", headers=auth)
    assert r.status_code == 200
    data = r.json()
    assert data["round_id"] == current_round["id"]
    assert data["players_count"] == 1
    assert len(data["ranking"]) == 1
    assert data["ranking"][0]["player_id"] == player["id"]


def test_finalize_empty_round_returns_400(client, auth, current_round):
    r = client.post(f"/api/rounds/{current_round['id']}/finalize", headers=auth)
    assert r.status_code == 400


def test_finalize_already_finalized_returns_409(client, auth, current_round, player):
    client.post(f"/api/rounds/{current_round['id']}/players",
                json={"player_id": player["id"]}, headers=auth)
    client.get("/api/config")
    client.post(f"/api/rounds/{current_round['id']}/finalize", headers=auth)
    r = client.post(f"/api/rounds/{current_round['id']}/finalize", headers=auth)
    assert r.status_code == 409


def test_finalize_marks_round_as_not_current(client, auth, current_round, player):
    client.post(f"/api/rounds/{current_round['id']}/players",
                json={"player_id": player["id"]}, headers=auth)
    client.get("/api/config")
    client.post(f"/api/rounds/{current_round['id']}/finalize", headers=auth)
    assert client.get("/api/rounds/current").json() is None


def test_total_points_calculation(client, auth, current_round, player):
    client.post(f"/api/rounds/{current_round['id']}/players",
                json={"player_id": player["id"], "buyin": 1,
                      "pontos": 100, "presenca": 10, "bonus": 5,
                      "indicacao": 3, "pontualidade": 15}, headers=auth)
    rps = client.get(f"/api/rounds/{current_round['id']}/players").json()
    assert rps[0]["total"] == 133  # 100+10+5+3+15
