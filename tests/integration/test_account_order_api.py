# tests/integration/test_account_order_api.py
"""
계정 및 주문 API 통합 테스트
"""
import pytest
from decimal import Decimal
from unittest.mock import patch


class TestAccountAPI:
    """계정 관련 API 테스트"""
    
    def test_get_account_summary(self, client, auth_headers, test_account):
        """계정 요약 정보 조회 테스트"""
        response = client.get("/api/v1/account/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "balance" in data
        assert "total_profit" in data
        assert "positions" in data
        assert float(data["balance"]) == 1000000.0
    
    
    def test_get_transactions(self, client, auth_headers):
        """거래 내역 조회 테스트"""
        response = client.get("/api/v1/account/transactions", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestOrderAPI:
    """주문 관련 API 테스트"""
    
    def test_create_market_buy_order(self, client, auth_headers, test_account):
        """시장가 매수 주문 생성 API 테스트"""
        with patch("app.services.order_service.get_current_price") as mock_price:
            mock_price.return_value = Decimal("50000")
            
            response = client.post(
                "/api/v1/orders/",
                headers=auth_headers,
                json={
                    "symbol": "BTCUSDT",
                    "side": "BUY",
                    "order_type": "MARKET",
                    "quantity": "0.01"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "BTCUSDT"
            assert data["side"] == "BUY"
            assert data["status"] == "FILLED"
            assert "id" in data
    
    
    def test_create_limit_order(self, client, auth_headers):
        """지정가 주문 생성 API 테스트"""
        response = client.post(
            "/api/v1/orders/",
            headers=auth_headers,
            json={
                "symbol": "ETHUSDT",
                "side": "BUY",
                "order_type": "LIMIT",
                "quantity": "0.5",
                "price": "2000"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "PENDING"
        assert float(data["price"]) == 2000.0
    
    
    def test_create_order_without_price_for_limit(self, client, auth_headers):
        """지정가 주문 시 가격 미입력 에러 테스트"""
        response = client.post(
            "/api/v1/orders/",
            headers=auth_headers,
            json={
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "LIMIT",
                "quantity": "0.1"
                # price 누락
            }
        )
        
        # 422 (Validation Error) 또는 400 (Bad Request)
        assert response.status_code in [400, 422]
    
    
    def test_create_sell_order_without_position(self, client, auth_headers):
        """보유하지 않은 코인 매도 시도 테스트"""
        with patch("app.services.order_service.get_current_price") as mock_price:
            mock_price.return_value = Decimal("2000")
            
            response = client.post(
                "/api/v1/orders/",
                headers=auth_headers,
                json={
                    "symbol": "ETHUSDT",
                    "side": "SELL",
                    "order_type": "MARKET",
                    "quantity": "1.0"
                }
            )
            
            assert response.status_code == 400
            assert "포지션" in response.json()["detail"] or "position" in response.json()["detail"].lower()
    
    
    def test_get_orders_list(self, client, auth_headers):
        """주문 목록 조회 테스트"""
        response = client.get("/api/v1/orders/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    
    def test_get_orders_with_filters(self, client, auth_headers):
        """필터링된 주문 목록 조회 테스트"""
        # 특정 심볼 필터
        response = client.get(
            "/api/v1/orders/?symbol=BTCUSDT",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # 특정 상태 필터
        response = client.get(
            "/api/v1/orders/?status=FILLED",
            headers=auth_headers
        )
        assert response.status_code == 200


class TestMarketAPI:
    """마켓 데이터 API 테스트"""
    
    def test_get_all_coins(self, client):
        """모든 코인 정보 조회 (인증 불필요)"""
        with patch("app.services.binance_service.get_multiple_prices") as mock_prices:
            mock_prices.return_value = {
                "BTCUSDT": {"price": "50000", "change": "5.2"},
                "ETHUSDT": {"price": "3000", "change": "-2.1"}
            }
            
            response = client.get("/api/v1/market/coins")
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) > 0
    
    
    def test_get_coin_detail(self, client):
        """특정 코인 상세 정보 조회"""
        with patch("app.services.binance_service.get_current_price") as mock_price:
            mock_price.return_value = Decimal("50000")
            
            response = client.get("/api/v1/market/coin/BTCUSDT")
            
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "BTCUSDT"
            assert "price" in data
    
    
    def test_get_historical_data(self, client):
        """과거 가격 데이터 조회"""
        with patch("app.services.binance_service.get_historical_klines") as mock_klines:
            mock_klines.return_value = [
                {"timestamp": "2024-01-01", "open": "50000", "high": "51000", 
                 "low": "49000", "close": "50500", "volume": "1000"}
            ]
            
            response = client.get("/api/v1/market/historical/BTCUSDT?interval=1d&limit=30")
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)


class TestValidation:
    """입력 검증 테스트"""
    
    def test_invalid_symbol(self, client, auth_headers):
        """유효하지 않은 심볼로 주문 시도"""
        response = client.post(
            "/api/v1/orders/",
            headers=auth_headers,
            json={
                "symbol": "INVALID",
                "side": "BUY",
                "order_type": "MARKET",
                "quantity": "0.1"
            }
        )
        
        assert response.status_code in [400, 422]
    
    
    def test_negative_quantity(self, client, auth_headers):
        """음수 수량으로 주문 시도"""
        response = client.post(
            "/api/v1/orders/",
            headers=auth_headers,
            json={
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "MARKET",
                "quantity": "-0.1"  # 음수
            }
        )
        
        assert response.status_code == 422
    
    
    def test_zero_quantity(self, client, auth_headers):
        """0 수량으로 주문 시도"""
        response = client.post(
            "/api/v1/orders/",
            headers=auth_headers,
            json={
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "MARKET",
                "quantity": "0"
            }
        )
        
        assert response.status_code == 422