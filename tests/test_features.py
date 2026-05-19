def test_get_account_summary(client, auth_headers):
    res = client.get("/api/v1/account", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "balance" in data
    assert "total_profit" in data
    assert "positions" in data
    assert "fee_info" in data


def test_get_symbol_rules(client, auth_headers):
    res = client.get("/api/v1/account/symbol-rules", headers=auth_headers)
    assert res.status_code == 200
    assert "BTCUSDT" in res.json()


def test_toggle_bnb_fee(client, auth_headers):
    res = client.post("/api/v1/account/bnb-fee", json={"use_bnb": True}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["bnb_discount"] is True


def test_create_price_alert(client, auth_headers):
    res = client.post("/api/v1/alerts", json={
        "symbol": "BTCUSDT", "target_price": "60000",
        "condition": "ABOVE", "memo": "test alert",
    }, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["target_price"] == "60000.00000000"


def test_list_alerts(client, auth_headers):
    client.post("/api/v1/alerts", json={
        "symbol": "BTCUSDT", "target_price": "60000", "condition": "ABOVE",
    }, headers=auth_headers)
    res = client.get("/api/v1/alerts", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_delete_alert(client, auth_headers):
    create = client.post("/api/v1/alerts", json={
        "symbol": "BTCUSDT", "target_price": "60000", "condition": "ABOVE",
    }, headers=auth_headers)
    alert_id = create.json()["id"]
    res = client.delete(f"/api/v1/alerts/{alert_id}", headers=auth_headers)
    assert res.status_code == 200


def test_analytics_empty(client, auth_headers):
    res = client.get("/api/v1/analytics", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_trades"] == 0
    assert data["win_rate"] == 0


def test_leaderboard_includes_users(client, auth_headers):
    res = client.get("/api/v1/leaderboard")
    assert res.status_code == 200
    data = res.json()
    assert any(u["username"] == "tester" for u in data)


def test_daily_missions_created(client, auth_headers):
    res = client.get("/api/v1/achievements/missions", headers=auth_headers)
    assert res.status_code == 200
    missions = res.json()
    assert len(missions) == 3  # DAILY_MISSION_COUNT


def test_achievement_list(client, auth_headers):
    res = client.get("/api/v1/achievements", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "achievements" in data
    assert data["total_count"] > 0


def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
