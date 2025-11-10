# tests/test_orders.py
"""
Order management tests
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from unittest.mock import patch, AsyncMock
from app.models.database import User, Order, OrderStatus

@pytest.mark.asyncio
async def test_create_market_order(client: TestClient, auth_headers: dict, session: Session):
    """Test creating a market order"""
    with patch('app.services.order_service.get_current_price', new=AsyncMock(return_value=50000.0)):
        response = client.post(
            "/orders/",
            json={
                "symbol": "BTCUSDT",
                "order_type": "MARKET",
                "order_side": "BUY",
                "quantity": 0.01
            },
            headers=auth_headers
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "BTCUSDT"
    assert data["order_type"] == "MARKET"
    assert data["order_side"] == "BUY"
    assert data["order_status"] == "FILLED"

@pytest.mark.asyncio
async def test_create_limit_order(client: TestClient, auth_headers: dict):
    """Test creating a limit order"""
    response = client.post(
        "/orders/",
        json={
            "symbol": "ETHUSDT",
            "order_type": "LIMIT",
            "order_side": "BUY",
            "quantity": 0.1,
            "price": 3000.0
        },
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "ETHUSDT"
    assert data["order_type"] == "LIMIT"
    assert data["price"] == "3000.0"
    assert data["order_status"] == "PENDING"

def test_create_order_without_auth(client: TestClient):
    """Test creating order without authentication"""
    response = client.post(
        "/orders/",
        json={
            "symbol": "BTCUSDT",
            "order_type": "MARKET",
            "order_side": "BUY",
            "quantity": 0.01
        }
    )
    
    assert response.status_code == 403  # Forbidden

def test_create_order_invalid_symbol(client: TestClient, auth_headers: dict):
    """Test creating order with invalid symbol"""
    response = client.post(
        "/orders/",
        json={
            "symbol": "INVALID",
            "order_type": "MARKET",
            "order_side": "BUY",
            "quantity": 0.01
        },
        headers=auth_headers
    )
    
    assert response.status_code == 400
    assert "Unsupported symbol" in response.json()["detail"]

def test_get_orders(client: TestClient, auth_headers: dict):
    """Test getting user orders"""
    response = client.get("/orders/", headers=auth_headers)
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_orders_with_filters(client: TestClient, auth_headers: dict):
    """Test getting orders with filters"""
    response = client.get(
        "/orders/",
        params={"symbol": "BTCUSDT", "status": "PENDING", "limit": 10},
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_cancel_order(client: TestClient, auth_headers: dict, session: Session):
    """Test cancelling an order"""
    # First create a limit order
    response = client.post(
        "/orders/",
        json={
            "symbol": "BTCUSDT",
            "order_type": "LIMIT",
            "order_side": "BUY",
            "quantity": 0.01,
            "price": 40000.0
        },
        headers=auth_headers
    )
    
    order_id = response.json()["id"]
    
    # Cancel the order
    response = client.delete(f"/orders/{order_id}", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["order_status"] == "CANCELLED"

def test_cancel_nonexistent_order(client: TestClient, auth_headers: dict):
    """Test cancelling non-existent order"""
    response = client.delete("/orders/999999", headers=auth_headers)
    
    assert response.status_code == 404
    assert "Order not found" in response.json()["detail"]

@pytest.mark.asyncio
async def test_insufficient_balance(client: TestClient, auth_headers: dict, session: Session):
    """Test order creation with insufficient balance"""
    with patch('app.services.order_service.get_current_price', new=AsyncMock(return_value=50000.0)):
        response = client.post(
            "/orders/",
            json={
                "symbol": "BTCUSDT",
                "order_type": "MARKET",
                "order_side": "BUY",
                "quantity": 10000  # Very large quantity
            },
            headers=auth_headers
        )
    
    assert response.status_code == 400
    assert "Insufficient balance" in response.json()["detail"]

def test_limit_order_missing_price(client: TestClient, auth_headers: dict):
    """Test limit order without price"""
    response = client.post(
        "/orders/",
        json={
            "symbol": "BTCUSDT",
            "order_type": "LIMIT",
            "order_side": "BUY",
            "quantity": 0.01
        },
        headers=auth_headers
    )
    
    assert response.status_code == 422  # Validation error

@pytest.mark.asyncio
async def test_stop_loss_order(client: TestClient, auth_headers: dict):
    """Test creating a stop loss order"""
    response = client.post(
        "/orders/",
        json={
            "symbol": "BTCUSDT",
            "order_type": "STOP_LOSS",
            "order_side": "SELL",
            "quantity": 0.01,
            "stop_price": 45000.0
        },
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["order_type"] == "STOP_LOSS"
    assert data["stop_price"] == "45000.0"