# tests/test_integration.py
"""
Integration tests for the complete flow
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from unittest.mock import patch, AsyncMock
from decimal import Decimal

@pytest.mark.asyncio
async def test_complete_trading_flow(client: TestClient, session: Session):
    """Test complete trading flow from registration to order execution"""
    
    # 1. Register user
    register_response = client.post(
        "/auth/register",
        json={
            "username": "trader",
            "email": "trader@example.com",
            "password": "TraderPass123!"
        }
    )
    assert register_response.status_code == 200
    
    # 2. Login
    login_response = client.post(
        "/auth/login",
        json={
            "username": "trader",
            "password": "TraderPass123!"
        }
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Check account
    account_response = client.get("/account/summary", headers=headers)
    assert account_response.status_code == 200
    assert account_response.json()["balance"] == "100000.0"
    
    # 4. Get market data
    with patch('app.services.binance_service.httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"price": "50000.0"}
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        
        price_response = client.get("/market/price/BTCUSDT")
        assert price_response.status_code == 200
        assert price_response.json()["price"] == 50000.0
    
    # 5. Create buy order
    with patch('app.services.order_service.get_current_price', new=AsyncMock(return_value=50000.0)):
        order_response = client.post(
            "/orders/",
            json={
                "symbol": "BTCUSDT",
                "order_type": "MARKET",
                "order_side": "BUY",
                "quantity": 0.1
            },
            headers=headers
        )
    assert order_response.status_code == 200
    assert order_response.json()["order_status"] == "FILLED"
    
    # 6. Check positions
    positions_response = client.get("/account/positions", headers=headers)
    assert positions_response.status_code == 200
    positions = positions_response.json()
    assert len(positions) > 0
    assert positions[0]["symbol"] == "BTCUSDT"
    
    # 7. Create price alert
    alert_response = client.post(
        "/alerts/",
        json={
            "symbol": "BTCUSDT",
            "target_price": 55000.0,
            "condition": "ABOVE"
        },
        headers=headers
    )
    assert alert_response.status_code == 200
    
    # 8. Open futures position
    futures_response = client.post(
        "/futures/open-position",
        json={
            "symbol": "ETHUSDT",
            "side": "LONG",
            "quantity": 1.0,
            "leverage": 10
        },
        headers=headers
    )
    assert futures_response.status_code == 200

@pytest.mark.asyncio
async def test_order_validation(client: TestClient, auth_headers: dict):
    """Test order validation and error handling"""
    
    # Test invalid symbol
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
    
    # Test limit order without price
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
    assert response.status_code == 422
    
    # Test negative quantity
    response = client.post(
        "/orders/",
        json={
            "symbol": "BTCUSDT",
            "order_type": "MARKET",
            "order_side": "BUY",
            "quantity": -0.01
        },
        headers=auth_headers
    )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_portfolio_management(client: TestClient, auth_headers: dict):
    """Test portfolio and position management"""
    
    # Create multiple positions
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    
    for symbol in symbols:
        with patch('app.services.order_service.get_current_price', new=AsyncMock(return_value=1000.0)):
            response = client.post(
                "/orders/",
                json={
                    "symbol": symbol,
                    "order_type": "MARKET",
                    "order_side": "BUY",
                    "quantity": 1.0
                },
                headers=auth_headers
            )
            assert response.status_code == 200
    
    # Get portfolio
    portfolio_response = client.get("/account/portfolio", headers=auth_headers)
    assert portfolio_response.status_code == 200
    portfolio = portfolio_response.json()
    assert len(portfolio) >= len(symbols)
    
    # Check transactions
    transactions_response = client.get("/account/transactions", headers=auth_headers)
    assert transactions_response.status_code == 200
    transactions = transactions_response.json()
    assert len(transactions) >= len(symbols)

@pytest.mark.asyncio
async def test_futures_trading(client: TestClient, auth_headers: dict):
    """Test futures trading functionality"""
    
    # Get futures account
    account_response = client.get("/futures/account", headers=auth_headers)
    assert account_response.status_code == 200
    initial_balance = account_response.json()["usdt_balance"]
    
    # Open long position
    with patch('app.services.futures_service.get_current_price', new=AsyncMock(return_value=3000.0)):
        open_response = client.post(
            "/futures/open-position",
            json={
                "symbol": "ETHUSDT",
                "side": "LONG",
                "quantity": 1.0,
                "leverage": 5,
                "stop_loss": 2900.0,
                "take_profit": 3300.0
            },
            headers=auth_headers
        )
    assert open_response.status_code == 200
    position_id = open_response.json()["id"]
    
    # Get position details
    position_response = client.get(f"/futures/positions/{position_id}", headers=auth_headers)
    assert position_response.status_code == 200
    
    # Close position
    with patch('app.services.futures_service.get_current_price', new=AsyncMock(return_value=3100.0)):
        close_response = client.post(
            "/futures/close-position",
            json={"position_id": position_id},
            headers=auth_headers
        )
    assert close_response.status_code == 200
    assert close_response.json()["status"] == "CLOSED"
    
    # Check PnL
    final_account = client.get("/futures/account", headers=auth_headers)
    final_balance = final_account.json()["usdt_balance"]
    # Should have profit since price went from 3000 to 3100
    assert float(final_balance) > float(initial_balance)

def test_rate_limiting_simulation(client: TestClient, auth_headers: dict):
    """Test API behavior under high load"""
    
    # Simulate multiple rapid requests
    for _ in range(10):
        response = client.get("/account/summary", headers=auth_headers)
        assert response.status_code == 200