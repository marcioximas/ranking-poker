"""
Tests for player CRUD including telefone and pix contact fields.
"""


def test_list_players_empty(client):
    r = client.get("/api/players")
    assert r.status_code == 200
    assert r.json() == []


def test_create_player(client, auth):
    r = client.post("/api/players", json={"name": "Mateus"}, headers=auth)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Mateus"
    assert "id" in data


def test_create_player_requires_auth(client):
    r = client.post("/api/players", json={"name": "X"})
    assert r.status_code == 401


def test_create_duplicate_player_returns_409(client, auth):
    client.post("/api/players", json={"name": "Mateus"}, headers=auth)
    r = client.post("/api/players", json={"name": "Mateus"}, headers=auth)
    assert r.status_code == 409


def test_get_player_by_id(client, auth, player):
    r = client.get(f"/api/players/{player['id']}")
    assert r.status_code == 200
    assert r.json()["name"] == player["name"]


def test_get_nonexistent_player_returns_404(client):
    r = client.get("/api/players/9999")
    assert r.status_code == 404


def test_update_player(client, auth, player):
    r = client.put(f"/api/players/{player['id']}",
                   json={"name": "Mateus Renomeado"}, headers=auth)
    assert r.status_code == 200
    assert r.json()["name"] == "Mateus Renomeado"


def test_update_player_to_existing_name_returns_409(client, auth):
    p1 = client.post("/api/players", json={"name": "Alpha"}, headers=auth).json()
    client.post("/api/players", json={"name": "Beta"}, headers=auth)
    r = client.put(f"/api/players/{p1['id']}", json={"name": "Beta"}, headers=auth)
    assert r.status_code == 409


def test_update_nonexistent_player_returns_404(client, auth):
    r = client.put("/api/players/9999", json={"name": "X"}, headers=auth)
    assert r.status_code == 404


def test_delete_player(client, auth, player):
    r = client.delete(f"/api/players/{player['id']}", headers=auth)
    assert r.status_code == 204
    assert client.get(f"/api/players/{player['id']}").status_code == 404


def test_delete_player_requires_auth(client, player):
    r = client.delete(f"/api/players/{player['id']}")
    assert r.status_code == 401


def test_delete_nonexistent_player_returns_404(client, auth):
    r = client.delete("/api/players/9999", headers=auth)
    assert r.status_code == 404


def test_list_players_sorted_alphabetically(client, auth):
    for name in ["Zico", "Abelardo", "Marcos"]:
        client.post("/api/players", json={"name": name}, headers=auth)
    names = [p["name"] for p in client.get("/api/players").json()]
    assert names == sorted(names)


# ── Contact fields (telefone + pix) ──────────────────────────────────────────

def test_create_player_with_contact_fields(client, auth):
    r = client.post(
        "/api/players",
        json={"name": "Alice", "telefone": "11999990000", "pix": "alice@pix.com"},
        headers=auth,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["telefone"] == "11999990000"
    assert data["pix"] == "alice@pix.com"


def test_create_player_name_only_contact_fields_are_null(client, auth):
    r = client.post("/api/players", json={"name": "Bob"}, headers=auth)
    assert r.status_code == 201
    assert r.json()["telefone"] is None
    assert r.json()["pix"] is None


def test_list_players_returns_contact_fields(client, auth):
    client.post(
        "/api/players",
        json={"name": "Carol", "telefone": "11988887777", "pix": "carol@bank"},
        headers=auth,
    )
    players = client.get("/api/players").json()
    carol = next(p for p in players if p["name"] == "Carol")
    assert carol["telefone"] == "11988887777"
    assert carol["pix"] == "carol@bank"


def test_get_player_by_id_returns_contact_fields(client, auth):
    pid = client.post(
        "/api/players",
        json={"name": "Dave", "telefone": "11977776666", "pix": "dave-pix"},
        headers=auth,
    ).json()["id"]
    r = client.get(f"/api/players/{pid}")
    assert r.json()["telefone"] == "11977776666"
    assert r.json()["pix"] == "dave-pix"


def test_update_player_contact_fields(client, auth, player):
    r = client.put(
        f"/api/players/{player['id']}",
        json={"name": player["name"], "telefone": "11966665555", "pix": "new@pix"},
        headers=auth,
    )
    assert r.status_code == 200
    assert r.json()["telefone"] == "11966665555"
    assert r.json()["pix"] == "new@pix"


def test_update_clears_contact_when_null(client, auth):
    pid = client.post(
        "/api/players",
        json={"name": "Eve", "telefone": "11955554444", "pix": "eve@pix"},
        headers=auth,
    ).json()["id"]
    r = client.put(
        f"/api/players/{pid}",
        json={"name": "Eve", "telefone": None, "pix": None},
        headers=auth,
    )
    assert r.status_code == 200
    assert r.json()["telefone"] is None
    assert r.json()["pix"] is None


def test_update_same_name_updates_contact_only(client, auth, player):
    r = client.put(
        f"/api/players/{player['id']}",
        json={"name": player["name"], "pix": "mypix-key"},
        headers=auth,
    )
    assert r.status_code == 200
    assert r.json()["name"] == player["name"]
    assert r.json()["pix"] == "mypix-key"
