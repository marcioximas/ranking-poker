def test_get_ranking_empty(client):
    r = client.get("/api/ranking")
    assert r.status_code == 200
    data = r.json()
    assert data["rounds"] == []
    assert data["active_round_ids"] == []
    assert data["rows"] == []


def test_ranking_shows_finalized_rounds_only(client, auth, current_round, player):
    # current_round is NOT finalized — should not appear in ranking
    r = client.get("/api/ranking")
    assert r.json()["rounds"] == []

    # Finalize it
    client.post(f"/api/rounds/{current_round['id']}/players",
                json={"player_id": player["id"]}, headers=auth)
    client.get("/api/config")
    client.post(f"/api/rounds/{current_round['id']}/finalize", headers=auth)

    r = client.get("/api/ranking")
    assert len(r.json()["rounds"]) == 1


def test_ranking_scores_after_finalize(client, auth, current_round, player):
    client.post(f"/api/rounds/{current_round['id']}/players",
                json={"player_id": player["id"], "pontos": 200, "presenca": 10,
                      "pontualidade": 15}, headers=auth)
    client.get("/api/config")
    client.post(f"/api/rounds/{current_round['id']}/finalize", headers=auth)

    r = client.get("/api/ranking")
    data = r.json()
    row = next(row for row in data["rows"] if row["player_id"] == player["id"])
    assert row["scores"][str(current_round["id"])] == 225  # 200+10+15


def test_set_active_rounds_requires_auth(client, finalized_round):
    r = client.put("/api/ranking/active-rounds",
                   json={"round_ids": [finalized_round["id"]]})
    assert r.status_code == 401


def test_set_active_rounds(client, auth, finalized_round):
    r = client.put("/api/ranking/active-rounds",
                   json={"round_ids": [finalized_round["id"]]}, headers=auth)
    assert r.status_code == 200
    assert finalized_round["id"] in r.json()["active_round_ids"]


def test_update_score_requires_auth(client, auth, finalized_round, player):
    r = client.put(f"/api/ranking/{player['id']}/{finalized_round['id']}",
                   json={"score": 99})
    assert r.status_code == 401


def test_update_score(client, auth, finalized_round, player):
    r = client.put(f"/api/ranking/{player['id']}/{finalized_round['id']}",
                   json={"score": 99}, headers=auth)
    assert r.status_code == 200
    assert r.json()["score"] == 99

    # Verify ranking reflects updated score
    ranking = client.get("/api/ranking").json()
    row = next(row for row in ranking["rows"] if row["player_id"] == player["id"])
    assert row["scores"][str(finalized_round["id"])] == 99


def test_update_score_nonexistent_player_returns_404(client, auth, finalized_round):
    r = client.put(f"/api/ranking/9999/{finalized_round['id']}",
                   json={"score": 10}, headers=auth)
    assert r.status_code == 404
