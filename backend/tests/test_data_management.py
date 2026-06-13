"""
Tests for data management: bulk operations, integrity constraints,
active-round filtering, and config/financial singleton behaviour.
"""
import pytest


@pytest.fixture
def two_players(client, auth):
    p1 = client.post("/api/players", json={"name": "Alice"}, headers=auth).json()
    p2 = client.post("/api/players", json={"name": "Bob"}, headers=auth).json()
    return p1, p2


# ── Bulk operations ───────────────────────────────────────────────────────────

class TestBulkOperations:
    def test_create_ten_players(self, client, auth):
        for i in range(1, 11):
            r = client.post("/api/players", json={"name": f"Jogador {i}"}, headers=auth)
            assert r.status_code == 201

        players = client.get("/api/players").json()
        assert len(players) == 10

    def test_players_alphabetical_after_bulk_insert(self, client, auth):
        for name in ["Zara", "Alice", "Marcos", "Bruno", "Clara"]:
            client.post("/api/players", json={"name": name}, headers=auth)

        players = client.get("/api/players").json()
        names = [p["name"] for p in players]
        assert names == sorted(names)

    def test_create_multiple_expenses_sum_in_financial(self, client, auth):
        for name, value in [("Mesa", 100.0), ("Fichas", 50.0), ("Bebida", 30.0)]:
            client.post("/api/expenses", json={"name": name, "value": value}, headers=auth)

        fin = client.get("/api/financial").json()
        assert fin["total_despesas"] == pytest.approx(180.0)

    def test_expenses_listed_alphabetically(self, client, auth):
        for name in ["Zebra", "Alpha", "Mesa"]:
            client.post("/api/expenses", json={"name": name, "value": 10}, headers=auth)

        expenses = client.get("/api/expenses").json()
        names = [e["name"] for e in expenses]
        assert names == sorted(names)


# ── Data integrity ────────────────────────────────────────────────────────────

class TestDataIntegrity:
    def test_config_defaults_on_fresh_db(self, client):
        config = client.get("/api/config").json()
        assert config["buyin_value"] == pytest.approx(50.0)
        assert config["addon_value"] == pytest.approx(50.0)
        assert config["prize_pct"] == pytest.approx(70.0)
        assert config["ranking_pct"] == pytest.approx(30.0)
        assert config["presence_points"] == 10
        assert config["punctuality_points"] == 15
        assert config["itm_bonus_points"] == 5

    def test_config_is_singleton(self, client):
        c1 = client.get("/api/config").json()
        c2 = client.get("/api/config").json()
        assert c1["id"] == c2["id"]

    def test_config_changes_persist(self, client, auth):
        client.put("/api/config", json={"buyin_value": 75.0}, headers=auth)
        config = client.get("/api/config").json()
        assert config["buyin_value"] == pytest.approx(75.0)

    def test_expense_rename_to_existing_name_rejected(self, client, auth):
        client.post("/api/expenses", json={"name": "Mesa", "value": 100}, headers=auth)
        r2 = client.post("/api/expenses", json={"name": "Fichas", "value": 50}, headers=auth)
        exp2_id = r2.json()["id"]

        r = client.put(f"/api/expenses/{exp2_id}", json={"name": "Mesa"}, headers=auth)
        assert r.status_code == 409

    def test_round_player_total_includes_all_fields(self, client, auth, player, current_round):
        round_id = current_round["id"]
        player_id = player["id"]

        client.post(f"/api/rounds/{round_id}/players", json={"player_id": player_id}, headers=auth)
        client.put(f"/api/rounds/{round_id}/players/{player_id}", json={
            "pontos": 15, "presenca": 5, "bonus": 10, "indicacao": 2, "pontualidade": 3
        }, headers=auth)

        rps = client.get(f"/api/rounds/{round_id}/players").json()
        rp = next(r for r in rps if r["player_id"] == player_id)
        assert rp["total"] == 35

    def test_round_players_sorted_by_total_descending(self, client, auth, two_players, current_round):
        p1, p2 = two_players
        round_id = current_round["id"]

        client.post(f"/api/rounds/{round_id}/players", json={"player_id": p1["id"]}, headers=auth)
        client.post(f"/api/rounds/{round_id}/players", json={"player_id": p2["id"]}, headers=auth)
        client.put(f"/api/rounds/{round_id}/players/{p1['id']}", json={"pontos": 5}, headers=auth)
        client.put(f"/api/rounds/{round_id}/players/{p2['id']}", json={"pontos": 20}, headers=auth)

        rps = client.get(f"/api/rounds/{round_id}/players").json()
        totals = [rp["total"] for rp in rps]
        assert totals == sorted(totals, reverse=True)

    def test_financial_singleton_stable(self, client):
        for _ in range(5):
            r = client.get("/api/financial")
            assert r.status_code == 200

    def test_only_one_current_round_allowed(self, client, auth):
        client.post("/api/rounds/current", json={}, headers=auth)
        r = client.post("/api/rounds/current", json={}, headers=auth)
        assert r.status_code == 409

    def test_player_cannot_be_added_twice_to_same_round(self, client, auth, player, current_round):
        round_id = current_round["id"]
        player_id = player["id"]

        client.post(f"/api/rounds/{round_id}/players", json={"player_id": player_id}, headers=auth)
        r = client.post(f"/api/rounds/{round_id}/players", json={"player_id": player_id}, headers=auth)
        assert r.status_code == 409


# ── Active-rounds management ─────────────────────────────────────────────────

class TestActiveRoundsManagement:
    def _finalize_round_with_player(self, client, auth, label, p1, p2, pontos):
        round_id = client.post("/api/rounds/current", json={"label": label}, headers=auth).json()["id"]
        for p in [p1, p2]:
            client.post(f"/api/rounds/{round_id}/players", json={"player_id": p["id"]}, headers=auth)
        client.put(f"/api/rounds/{round_id}/players/{p1['id']}", json={"pontos": pontos}, headers=auth)
        client.post(f"/api/rounds/{round_id}/finalize", headers=auth)
        return round_id

    def test_all_rounds_active_by_default(self, client, auth, two_players):
        p1, p2 = two_players
        r1 = self._finalize_round_with_player(client, auth, "R1", p1, p2, 10)
        r2 = self._finalize_round_with_player(client, auth, "R2", p1, p2, 20)

        ranking = client.get("/api/ranking").json()
        assert set(ranking["active_round_ids"]) == {r1, r2}

    def test_deactivating_round_reduces_total(self, client, auth, two_players):
        p1, p2 = two_players
        r1 = self._finalize_round_with_player(client, auth, "R1", p1, p2, 10)
        r2 = self._finalize_round_with_player(client, auth, "R2", p1, p2, 20)

        # total should be 30
        ranking_full = client.get("/api/ranking").json()
        p1_full = next(r for r in ranking_full["rows"] if r["player_id"] == p1["id"])
        assert p1_full["total"] == 30

        # deactivate R2
        client.put("/api/ranking/active-rounds", json={"round_ids": [r1]}, headers=auth)
        ranking_partial = client.get("/api/ranking").json()
        p1_partial = next(r for r in ranking_partial["rows"] if r["player_id"] == p1["id"])
        assert p1_partial["total"] == 10

    def test_no_active_rounds_gives_zero_total(self, client, auth, two_players):
        p1, p2 = two_players
        self._finalize_round_with_player(client, auth, "R1", p1, p2, 10)

        client.put("/api/ranking/active-rounds", json={"round_ids": []}, headers=auth)
        ranking = client.get("/api/ranking").json()
        p1_row = next(r for r in ranking["rows"] if r["player_id"] == p1["id"])
        assert p1_row["total"] == 0

    def test_three_rounds_selective_activation(self, client, auth, two_players):
        p1, p2 = two_players
        r1 = self._finalize_round_with_player(client, auth, "R1", p1, p2, 10)
        r2 = self._finalize_round_with_player(client, auth, "R2", p1, p2, 20)
        r3 = self._finalize_round_with_player(client, auth, "R3", p1, p2, 30)

        # activate only R1 and R3 (skip R2)
        client.put("/api/ranking/active-rounds", json={"round_ids": [r1, r3]}, headers=auth)
        ranking = client.get("/api/ranking").json()
        p1_row = next(r for r in ranking["rows"] if r["player_id"] == p1["id"])
        assert p1_row["total"] == 40  # 10 + 30
        assert ranking["active_round_ids"] == [r1, r3]

    def test_current_round_never_in_ranking(self, client, auth, two_players):
        p1, p2 = two_players
        round_id = client.post("/api/rounds/current", json={"label": "Em andamento"}, headers=auth).json()["id"]
        for p in [p1, p2]:
            client.post(f"/api/rounds/{round_id}/players", json={"player_id": p["id"]}, headers=auth)

        ranking = client.get("/api/ranking").json()
        assert not any(r["id"] == round_id for r in ranking["rounds"])
