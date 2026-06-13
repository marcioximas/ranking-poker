def test_verify_correct_password(client, auth):
    r = client.post("/api/auth/verify", json={"password": "test-password"})
    assert r.status_code == 200
    assert r.json() == {"valid": True}


def test_verify_wrong_password(client):
    r = client.post("/api/auth/verify", json={"password": "errada"})
    assert r.status_code == 200
    assert r.json() == {"valid": False}


def test_verify_empty_password(client):
    r = client.post("/api/auth/verify", json={"password": ""})
    assert r.status_code == 200
    assert r.json() == {"valid": False}


def test_protected_endpoint_without_header_returns_401(client):
    r = client.post("/api/players", json={"name": "X"})
    assert r.status_code == 401


def test_protected_endpoint_with_wrong_header_returns_401(client):
    r = client.post("/api/players", json={"name": "X"},
                    headers={"X-Admin-Password": "errada"})
    assert r.status_code == 401


def test_protected_endpoint_with_correct_header_succeeds(client, auth):
    r = client.post("/api/players", json={"name": "X"}, headers=auth)
    assert r.status_code == 201
