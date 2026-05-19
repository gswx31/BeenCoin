"""Refresh Token Rotation 테스트."""


def test_login_returns_refresh_token(client):
    client.post("/api/v1/auth/register", json={"username": "rt_user", "password": "password123"})
    res = client.post("/api/v1/auth/login", json={"username": "rt_user", "password": "password123"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_refresh_issues_new_tokens(client, user_tokens):
    old_refresh = user_tokens["refresh_token"]
    res = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert res.status_code == 200
    data = res.json()
    # Refresh token은 반드시 회전 (rotation)
    assert data["refresh_token"] != old_refresh
    assert "access_token" in data


def test_refresh_token_reuse_revokes_all(client, user_tokens):
    """Refresh Token Rotation 핵심: 재사용 감지 시 전체 무효화."""
    old_refresh = user_tokens["refresh_token"]
    # 첫 refresh — 성공
    first = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert first.status_code == 200
    new_refresh = first.json()["refresh_token"]

    # 두 번째로 old_refresh 재사용 시도 — 실패 + 모든 세션 무효화
    reuse = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse.status_code == 401

    # 정상적으로 발급된 new_refresh도 무효화됐어야 함
    after = client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert after.status_code == 401


def test_invalid_refresh_token(client):
    res = client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid_token_xyz"})
    assert res.status_code == 401


def test_logout_revokes_token(client, user_tokens):
    refresh = user_tokens["refresh_token"]
    logout = client.post("/api/v1/auth/logout", json={"refresh_token": refresh})
    assert logout.status_code == 200

    # 로그아웃 후 refresh 시도 → 실패
    after = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert after.status_code == 401
