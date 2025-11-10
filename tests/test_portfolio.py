# tests/test_portfolio.py
"""
Portfolio management tests
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_portfolio_summary(client: TestClient, auth_headers: dict):
    """Test portfolio summary endpoint"""
    response = client.get("/account/portfolio/summary", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "total_value" in data
    assert "balance" in data
    assert "positions_value" in data
    assert "total_profit" in data
    assert "profit_rate" in data
    assert "positions" in data
    assert isinstance(data["positions"], list)

@pytest.mark.asyncio
async def test_portfolio_performance(client: TestClient, auth_headers: dict):
    """Test portfolio performance metrics"""
    response = client.get(
        "/account/portfolio/performance?period_days=30",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["period_days"] == 30
    assert "total_trades" in data
    assert "winning_trades" in data
    assert "losing_trades" in data
    assert "win_rate" in data
    assert "profit_factor" in data
    assert "net_profit" in data

@pytest.mark.asyncio
async def test_portfolio_allocation(client: TestClient, auth_headers: dict):
    """Test portfolio allocation breakdown"""
    # First create some positions
    with patch('app.services.order_service.get_current_price', new=AsyncMock(return_value=50000.0)):
        order_response = client.post(
            "/orders/",
            json={
                "symbol": "BTCUSDT",
                "order_type": "MARKET",
                "order_side": "BUY",
                "quantity": 0.1
            },
            headers=auth_headers
        )
        assert order_response.status_code == 200
    
    # Get allocation
    response = client.get("/account/portfolio/allocation", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    # Should have at least USDT allocation
    usdt_allocation = next((a for a in data if a["asset"] == "USDT"), None)
    assert usdt_allocation is not None
    assert usdt_allocation["percentage"] >= 0

@pytest.mark.asyncio
async def test_portfolio_with_multiple_positions(client: TestClient, auth_headers: dict):
    """Test portfolio with multiple positions"""
    symbols = ["ETHUSDT", "BNBUSDT", "SOLUSDT"]
    
    # Create multiple positions
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
    
    # Get portfolio summary
    response = client.get("/account/portfolio/summary", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have positions for all symbols
    assert len(data["positions"]) >= len(symbols)
    assert data["positions_value"] > 0
    
    # Check individual position details
    for position in data["positions"]:
        assert "symbol" in position
        assert "quantity" in position
        assert "current_price" in position
        assert "unrealized_pnl" in position
        assert "unrealized_pnl_percentage" in position

@pytest.mark.asyncio
async def test_portfolio_empty(client: TestClient, auth_headers: dict):
    """Test portfolio when user has no positions"""
    response = client.get("/account/portfolio/summary", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have balance but no positions
    assert data["balance"] > 0  # Initial balance
    assert data["positions_value"] == 0
    assert len(data["positions"]) == 0