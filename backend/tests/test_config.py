def test_get_config_returns_defaults(client):
    r = client.get("/api/config")
    assert r.status_code == 200
    data = r.json()
    assert data["buyin_value"] == 50.0
    assert data["prize_pct"] == 70.0
    assert data["presence_points"] == 10


def test_get_config_is_idempotent(client):
    """Multiple GETs return the same config without creating duplicates."""
    r1 = client.get("/api/config")
    r2 = client.get("/api/config")
    assert r1.json()["id"] == r2.json()["id"]


def test_update_config_requires_auth(client):
    r = client.put("/api/config", json={"tournament_name": "X", "buyin_value": 100,
                                         "addon_value": 50, "presence_points": 10,
                                         "punctuality_points": 15, "itm_bonus_points": 5,
                                         "prize_pct": 70, "ranking_pct": 30})
    assert r.status_code == 401


def test_update_config_persists_changes(client, auth):
    payload = {"tournament_name": "Liga A", "buyin_value": 100.0, "addon_value": 75.0,
               "presence_points": 20, "punctuality_points": 25, "itm_bonus_points": 10,
               "prize_pct": 65.0, "ranking_pct": 35.0}
    r = client.put("/api/config", json=payload, headers=auth)
    assert r.status_code == 200
    data = r.json()
    assert data["tournament_name"] == "Liga A"
    assert data["buyin_value"] == 100.0
    assert data["prize_pct"] == 65.0

    # Verify GET reflects the update
    r2 = client.get("/api/config")
    assert r2.json()["tournament_name"] == "Liga A"
