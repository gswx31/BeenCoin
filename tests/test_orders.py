from decimal import Decimal


def test_market_buy_order_fills(client, auth_headers):
    res = client.post("/api/v1/orders", json={
        "symbol": "BTCUSDT", "side": "BUY",
        "order_type": "MARKET", "quantity": "0.001",
    }, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["order_status"] == "FILLED"
    assert float(data["filled_quantity"]) == 0.001


def test_market_buy_deducts_balance(client, auth_headers):
    before = float(client.get("/api/v1/account", headers=auth_headers).json()["balance"])
    client.post("/api/v1/orders", json={
        "symbol": "BTCUSDT", "side": "BUY",
        "order_type": "MARKET", "quantity": "0.01",
    }, headers=auth_headers)
    after = float(client.get("/api/v1/account", headers=auth_headers).json()["balance"])
    assert after < before
    # 약 500달러 + 수수료 차감
    diff = before - after
    assert 499 < diff < 502


def test_insufficient_balance_rejected(client, auth_headers):
    res = client.post("/api/v1/orders", json={
        "symbol": "BTCUSDT", "side": "BUY",
        "order_type": "MARKET", "quantity": "1000",
    }, headers=auth_headers)
    assert res.status_code == 400
    assert "Insufficient" in res.json()["detail"]


def test_sell_without_position_rejected(client, auth_headers):
    res = client.post("/api/v1/orders", json={
        "symbol": "BTCUSDT", "side": "SELL",
        "order_type": "MARKET", "quantity": "0.01",
    }, headers=auth_headers)
    assert res.status_code == 400


def test_sell_creates_realized_pnl(client, auth_headers):
    # 매수 후 매도
    client.post("/api/v1/orders", json={
        "symbol": "BTCUSDT", "side": "BUY",
        "order_type": "MARKET", "quantity": "0.01",
    }, headers=auth_headers)
    res = client.post("/api/v1/orders", json={
        "symbol": "BTCUSDT", "side": "SELL",
        "order_type": "MARKET", "quantity": "0.01",
    }, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["order_status"] == "FILLED"


def test_limit_order_stays_pending(client, auth_headers):
    res = client.post("/api/v1/orders", json={
        "symbol": "BTCUSDT", "side": "BUY",
        "order_type": "LIMIT", "quantity": "0.001",
        "price": "10000",  # 현재가($50000) 훨씬 아래
    }, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["order_status"] == "PENDING"


def test_unsupported_symbol_rejected(client, auth_headers):
    res = client.post("/api/v1/orders", json={
        "symbol": "DOGEUSDT", "side": "BUY",
        "order_type": "MARKET", "quantity": "100",
    }, headers=auth_headers)
    assert res.status_code == 422


def test_min_quantity_validation(client, auth_headers):
    res = client.post("/api/v1/orders", json={
        "symbol": "BTCUSDT", "side": "BUY",
        "order_type": "MARKET", "quantity": "0.0000001",  # below minQty
    }, headers=auth_headers)
    assert res.status_code == 400


def test_cancel_pending_order(client, auth_headers):
    res = client.post("/api/v1/orders", json={
        "symbol": "BTCUSDT", "side": "BUY",
        "order_type": "LIMIT", "quantity": "0.001", "price": "10000",
    }, headers=auth_headers)
    order_id = res.json()["id"]

    cancel = client.delete(f"/api/v1/orders/{order_id}", headers=auth_headers)
    assert cancel.status_code == 200
    assert cancel.json()["order_status"] == "CANCELLED"


def test_cannot_cancel_filled_order(client, auth_headers):
    res = client.post("/api/v1/orders", json={
        "symbol": "BTCUSDT", "side": "BUY",
        "order_type": "MARKET", "quantity": "0.001",
    }, headers=auth_headers)
    order_id = res.json()["id"]
    cancel = client.delete(f"/api/v1/orders/{order_id}", headers=auth_headers)
    assert cancel.status_code == 400


def test_list_orders(client, auth_headers):
    client.post("/api/v1/orders", json={
        "symbol": "BTCUSDT", "side": "BUY",
        "order_type": "MARKET", "quantity": "0.001",
    }, headers=auth_headers)
    res = client.get("/api/v1/orders", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1
