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
