"""
Integration tests for complete business workflows across multiple API layers.
Tests the middle of the pyramid: real HTTP + real DB, but no browser.
"""
import pytest


@pytest.fixture
def two_players(client, auth):
    p1 = client.post("/api/players", json={"name": "Alice"}, headers=auth).json()
    p2 = client.post("/api/players", json={"name": "Bob"}, headers=auth).json()
    return p1, p2


# ── Full round lifecycle ──────────────────────────────────────────────────────

class TestFullRoundLifecycle:
    def test_create_add_finalize_check_ranking(self, client, auth, two_players):
        p1, p2 = two_players

        r = client.post("/api/rounds/current", json={"label": "Rodada Workflow"}, headers=auth)
        assert r.status_code == 201
        round_id = r.json()["id"]

        client.post(f"/api/rounds/{round_id}/players", json={"player_id": p1["id"]}, headers=auth)
        client.post(f"/api/rounds/{round_id}/players", json={"player_id": p2["id"]}, headers=auth)

        client.put(f"/api/rounds/{round_id}/players/{p1['id']}", json={"colocacao": 1, "presenca": 5}, headers=auth)
        client.put(f"/api/rounds/{round_id}/players/{p2['id']}", json={"colocacao": 2, "presenca": 5}, headers=auth)

        r = client.post(f"/api/rounds/{round_id}/finalize", headers=auth)
        assert r.status_code == 200
        result = r.json()
        assert result["players_count"] == 2
        assert result["ranking"][0]["player_id"] == p1["id"]  # 1st place scores more than 2nd
        assert result["ranking"][0]["prize"] == pytest.approx(result["premiacao_total"] * 0.7)
        assert result["ranking"][1]["prize"] == pytest.approx(result["premiacao_total"] * 0.3)

        ranking = client.get("/api/ranking").json()
        p1_row = next(row for row in ranking["rows"] if row["player_id"] == p1["id"])
        # 2 buyins × R$50 = R$100 arrecadado; prize_pool = R$85
        # 1st: int(85 × 0.70) // 10 = 59 // 10 = 5; presença = 5; total = 10
        assert p1_row["total"] == 10

    def test_round_is_not_current_after_finalize(self, client, auth, two_players):
        p1, p2 = two_players
        round_id = client.post("/api/rounds/current", json={}, headers=auth).json()["id"]
        for p in [p1, p2]:
            client.post(f"/api/rounds/{round_id}/players", json={"player_id": p["id"]}, headers=auth)

        client.post(f"/api/rounds/{round_id}/finalize", headers=auth)

        assert client.get("/api/rounds/current").json() is None

    def test_finalized_round_appears_in_ranking(self, client, auth, two_players):
        p1, p2 = two_players
        round_id = client.post("/api/rounds/current", json={"label": "R1"}, headers=auth).json()["id"]
        for p in [p1, p2]:
            client.post(f"/api/rounds/{round_id}/players", json={"player_id": p["id"]}, headers=auth)

        client.post(f"/api/rounds/{round_id}/finalize", headers=auth)

        ranking = client.get("/api/ranking").json()
        assert len(ranking["rounds"]) == 1
        assert ranking["rounds"][0]["id"] == round_id
        assert round_id in ranking["active_round_ids"]

    def test_new_round_can_start_after_finalize(self, client, auth, two_players):
        p1, p2 = two_players
        round_id = client.post("/api/rounds/current", json={}, headers=auth).json()["id"]
        for p in [p1, p2]:
            client.post(f"/api/rounds/{round_id}/players", json={"player_id": p["id"]}, headers=auth)
        client.post(f"/api/rounds/{round_id}/finalize", headers=auth)

        r2 = client.post("/api/rounds/current", json={"label": "Rodada 2"}, headers=auth)
        assert r2.status_code == 201
        assert r2.json()["is_current"] is True

    def test_financial_reflects_current_round_buyins(self, client, auth, two_players):
        p1, p2 = two_players
        round_id = client.post("/api/rounds/current", json={}, headers=auth).json()["id"]

        client.post(f"/api/rounds/{round_id}/players", json={"player_id": p1["id"], "buyin": 2}, headers=auth)
        client.post(f"/api/rounds/{round_id}/players", json={"player_id": p2["id"], "buyin": 1, "addon": 1}, headers=auth)

        fin = client.get("/api/financial").json()
        assert fin["total_buyins"] == 3
        assert fin["total_addons"] == 1
        assert fin["caixa_noite"] == pytest.approx(3 * 50.0 + 1 * 50.0)  # default config: buyin=50, addon=50

    def test_historical_round_does_not_affect_financial(self, client, auth, two_players):
        """Finalized rounds don't contribute to current financial summary."""
        p1, p2 = two_players
        round_id = client.post("/api/rounds/current", json={}, headers=auth).json()["id"]
        for p in [p1, p2]:
            client.post(f"/api/rounds/{round_id}/players", json={"player_id": p["id"], "buyin": 3}, headers=auth)
        client.post(f"/api/rounds/{round_id}/finalize", headers=auth)

        # No current round now
        fin = client.get("/api/financial").json()
        assert fin["total_buyins"] == 0
        assert fin["caixa_noite"] == pytest.approx(0.0)


# ── Cascade deletes ───────────────────────────────────────────────────────────

class TestCascadeDeletes:
    def test_delete_player_removes_from_active_round(self, client, auth, player, current_round):
        round_id = current_round["id"]
        player_id = player["id"]

        client.post(f"/api/rounds/{round_id}/players", json={"player_id": player_id}, headers=auth)
        rps = client.get(f"/api/rounds/{round_id}/players").json()
        assert any(rp["player_id"] == player_id for rp in rps)

        client.delete(f"/api/players/{player_id}", headers=auth)

        rps_after = client.get(f"/api/rounds/{round_id}/players").json()
        assert not any(rp["player_id"] == player_id for rp in rps_after)

    def test_delete_player_removes_semestral_score(self, client, auth, two_players):
        p1, p2 = two_players
        round_id = client.post("/api/rounds/current", json={}, headers=auth).json()["id"]
        for p in [p1, p2]:
            client.post(f"/api/rounds/{round_id}/players", json={"player_id": p["id"]}, headers=auth)
        client.post(f"/api/rounds/{round_id}/finalize", headers=auth)

        ranking_before = client.get("/api/ranking").json()
        assert any(row["player_id"] == p1["id"] for row in ranking_before["rows"])

        client.delete(f"/api/players/{p1['id']}", headers=auth)

        ranking_after = client.get("/api/ranking").json()
        assert not any(row["player_id"] == p1["id"] for row in ranking_after["rows"])

    def test_delete_round_removes_its_players(self, client, auth, player, current_round):
        round_id = current_round["id"]
        client.post(f"/api/rounds/{round_id}/players", json={"player_id": player["id"]}, headers=auth)

        client.delete(f"/api/rounds/{round_id}", headers=auth)

        assert client.get(f"/api/rounds/{round_id}").status_code == 404

    def test_delete_all_players_leaves_empty_ranking(self, client, auth, two_players):
        p1, p2 = two_players
        round_id = client.post("/api/rounds/current", json={}, headers=auth).json()["id"]
        for p in [p1, p2]:
            client.post(f"/api/rounds/{round_id}/players", json={"player_id": p["id"]}, headers=auth)
        client.post(f"/api/rounds/{round_id}/finalize", headers=auth)

        for p in [p1, p2]:
            client.delete(f"/api/players/{p['id']}", headers=auth)

        ranking = client.get("/api/ranking").json()
        assert ranking["rows"] == []


# ── Multi-round ranking ───────────────────────────────────────────────────────

class TestMultipleRoundsRanking:
    def test_scores_sum_across_two_rounds(self, client, auth, two_players):
        p1, p2 = two_players

        for label in ["Rodada 1", "Rodada 2"]:
            round_id = client.post("/api/rounds/current", json={"label": label}, headers=auth).json()["id"]
            for p in [p1, p2]:
                client.post(f"/api/rounds/{round_id}/players", json={"player_id": p["id"]}, headers=auth)
            client.put(f"/api/rounds/{round_id}/players/{p1['id']}", json={"colocacao": 1}, headers=auth)
            client.post(f"/api/rounds/{round_id}/finalize", headers=auth)

        ranking = client.get("/api/ranking").json()
        p1_row = next(row for row in ranking["rows"] if row["player_id"] == p1["id"])
        # Each round: 2 buyins × R$50 = R$100; prize_pool = R$85
        # 1st: int(85 × 0.70) // 10 = 5 pts × 2 rounds = 10
        assert p1_row["total"] == 10

    def test_inactive_round_excluded_from_total(self, client, auth, two_players):
        p1, p2 = two_players
        round_ids = []

        for label in ["R-A", "R-B"]:
            round_id = client.post("/api/rounds/current", json={"label": label}, headers=auth).json()["id"]
            round_ids.append(round_id)
            for p in [p1, p2]:
                client.post(f"/api/rounds/{round_id}/players", json={"player_id": p["id"]}, headers=auth)
            client.put(f"/api/rounds/{round_id}/players/{p1['id']}", json={"colocacao": 1}, headers=auth)
            client.post(f"/api/rounds/{round_id}/finalize", headers=auth)

        client.put("/api/ranking/active-rounds", json={"round_ids": [round_ids[0]]}, headers=auth)

        ranking = client.get("/api/ranking").json()
        p1_row = next(row for row in ranking["rows"] if row["player_id"] == p1["id"])
        # Only first round active: int(85 × 0.70) // 10 = 5
        assert p1_row["total"] == 5

    def test_ranking_sorted_by_total_descending(self, client, auth, two_players):
        p1, p2 = two_players
        round_id = client.post("/api/rounds/current", json={}, headers=auth).json()["id"]
        for p in [p1, p2]:
            client.post(f"/api/rounds/{round_id}/players", json={"player_id": p["id"]}, headers=auth)
        client.put(f"/api/rounds/{round_id}/players/{p2['id']}", json={"colocacao": 1}, headers=auth)
        client.put(f"/api/rounds/{round_id}/players/{p1['id']}", json={"colocacao": 2}, headers=auth)
        client.post(f"/api/rounds/{round_id}/finalize", headers=auth)

        ranking = client.get("/api/ranking").json()
        totals = [row["total"] for row in ranking["rows"]]
        assert totals == sorted(totals, reverse=True)

    def test_manual_score_edit_reflects_in_total(self, client, auth, two_players):
        p1, p2 = two_players
        round_id = client.post("/api/rounds/current", json={}, headers=auth).json()["id"]
        for p in [p1, p2]:
            client.post(f"/api/rounds/{round_id}/players", json={"player_id": p["id"]}, headers=auth)
        client.put(f"/api/rounds/{round_id}/players/{p1['id']}", json={"colocacao": 1}, headers=auth)
        client.post(f"/api/rounds/{round_id}/finalize", headers=auth)

        client.put(f"/api/ranking/{p1['id']}/{round_id}", json={"score": 99}, headers=auth)

        ranking = client.get("/api/ranking").json()
        p1_row = next(row for row in ranking["rows"] if row["player_id"] == p1["id"])
        assert p1_row["total"] == 99
