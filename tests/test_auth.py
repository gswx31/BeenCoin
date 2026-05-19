def test_register_creates_user(client):
    res = client.post("/api/v1/auth/register", json={"username": "alice", "password": "password123"})
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == "alice"
    assert "id" in data


def test_register_duplicate_username(client):
    client.post("/api/v1/auth/register", json={"username": "bob", "password": "password123"})
    res = client.post("/api/v1/auth/register", json={"username": "bob", "password": "password123"})
    assert res.status_code == 400


def test_register_short_password(client):
    res = client.post("/api/v1/auth/register", json={"username": "charlie", "password": "short"})
    assert res.status_code == 422


def test_login_success(client):
    client.post("/api/v1/auth/register", json={"username": "dave", "password": "password123"})
    res = client.post("/api/v1/auth/login", json={"username": "dave", "password": "password123"})
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_login_wrong_password(client):
    client.post("/api/v1/auth/register", json={"username": "eve", "password": "password123"})
    res = client.post("/api/v1/auth/login", json={"username": "eve", "password": "wrongpassword"})
    assert res.status_code == 401


def test_login_nonexistent_user(client):
    res = client.post("/api/v1/auth/login", json={"username": "ghost", "password": "password123"})
    assert res.status_code == 401


def test_account_requires_auth(client):
    res = client.get("/api/v1/account")
    assert res.status_code == 401


def test_account_with_valid_token(client, auth_headers):
    res = client.get("/api/v1/account", headers=auth_headers)
    assert res.status_code == 200
    assert "balance" in res.json()


def test_invalid_token_rejected(client):
    res = client.get("/api/v1/account", headers={"Authorization": "Bearer invalid.token.here"})
    assert res.status_code == 401
