# tests/test_websocket.py
"""
WebSocket tests
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from app.models.database import User

def test_websocket_price(client: TestClient):
    """Test WebSocket price updates"""
    with client.websocket_connect("/ws/price/BTCUSDT?interval=1") as websocket:
        # Should receive price update
        data = websocket.receive_json()
        assert data["type"] == "price"
        assert data["symbol"] == "BTCUSDT"
        assert "price" in data
        assert "timestamp" in data

def test_websocket_orderbook(client: TestClient):
    """Test WebSocket orderbook updates"""
    with client.websocket_connect("/ws/orderbook/BTCUSDT?limit=5&interval=1") as websocket:
        # Should receive orderbook update
        data = websocket.receive_json()
        assert data["type"] == "orderbook"
        assert data["symbol"] == "BTCUSDT"
        assert "bids" in data
        assert "asks" in data

def test_websocket_trades(client: TestClient):
    """Test WebSocket trades updates"""
    with client.websocket_connect("/ws/trades/BTCUSDT?limit=10&interval=1") as websocket:
        # Should receive trades update
        data = websocket.receive_json()
        assert data["type"] == "trades"
        assert data["symbol"] == "BTCUSDT"
        assert "trades" in data

def test_websocket_user_auth_invalid(client: TestClient):
    """Test WebSocket user connection with invalid token"""
    # Should close connection with invalid token
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/user?token=invalid_token") as websocket:
            pass

def test_websocket_user_auth_valid(client: TestClient, auth_headers: dict):
    """Test WebSocket user connection with valid token"""
    # Extract token from headers
    token = auth_headers["Authorization"].replace("Bearer ", "")
    
    with client.websocket_connect(f"/ws/user?token={token}") as websocket:
        # Should receive connection message
        data = websocket.receive_json()
        assert data["type"] == "connected"
        assert "message" in data
        
        # Test ping-pong
        websocket.send_json({"type": "ping"})
        response = websocket.receive_json()
        assert response["type"] == "pong"
        
        # Test subscription
        websocket.send_json({
            "type": "subscribe",
            "channel": "orders"
        })
        response = websocket.receive_json()
        assert response["type"] == "subscribed"
        assert response["channel"] == "orders"