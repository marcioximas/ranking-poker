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
                json={"player_id": player["id"], "colocacao": 1, "presenca": 10,
                      "pontualidade": 15}, headers=auth)
    client.post(f"/api/rounds/{current_round['id']}/finalize", headers=auth)

    r = client.get("/api/ranking")
    data = r.json()
    row = next(row for row in data["rows"] if row["player_id"] == player["id"])
    # 1 buyin × R$50 = R$50; prize_pool = R$42.5; 1st = int(42.5 × 0.70) // 10 = 2
    # score = 2 (pontos) + 10 (presenca) + 15 (pontualidade) = 27
    assert row["scores"][str(current_round["id"])] == 27
    assert row["buyins"][str(current_round["id"])] == 1
    assert row["rebuys"][str(current_round["id"])] == 0
    assert row["addons"][str(current_round["id"])] == 0


def test_ranking_shows_buyins_rebuys_addons_per_round(client, auth, current_round, player):
    client.post(
        f"/api/rounds/{current_round['id']}/players",
        json={"player_id": player["id"], "buyin": 3, "addon": 2, "colocacao": 1},
        headers=auth,
    )
    client.post(f"/api/rounds/{current_round['id']}/finalize", headers=auth)

    ranking = client.get("/api/ranking").json()
    row = next(r for r in ranking["rows"] if r["player_id"] == player["id"])
    rid = str(current_round["id"])

    assert row["buyins"][rid] == 3
    assert row["rebuys"][rid] == 2
    assert row["addons"][rid] == 2


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
