# tests/integration/test_account_order_api.py
"""
계정 및 주문 API 통합 테스트
거래 계정 조회, 주문 생성/조회, 포지션 관리 테스트
"""
import pytest
from decimal import Decimal
from unittest.mock import patch


class TestAccountAPI:
    """거래 계정 관련 API 테스트"""
    
    def test_get_account_success(self, client, auth_headers, test_account):
        """계정 정보 조회 성공 테스트"""
        response = client.get("/api/v1/account/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # 필수 필드 확인
        assert "balance" in data
        assert "total_profit" in data
        assert "user_id" in data
        assert "created_at" in data
        
        # 초기 잔액 확인
        assert Decimal(str(data["balance"])) == Decimal("1000000")
        assert Decimal(str(data["total_profit"])) == Decimal("0")
    
    
    def test_get_account_without_auth(self, client):
        """인증 없이 계정 조회 시도 시 실패"""
        response = client.get("/api/v1/account/")
        assert response.status_code == 401
    
    
    def test_get_account_with_invalid_token(self, client):
        """잘못된 토큰으로 계정 조회 시도 시 실패"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/account/", headers=headers)
        assert response.status_code == 401
    
    
    def test_account_balance_after_order(self, client, auth_headers, test_account):
        """주문 후 잔액 변화 확인"""
        with patch("app.services.binance_service.get_current_price") as mock_price:
            mock_price.return_value = Decimal("50000")
            
            # 매수 주문 생성
            order_response = client.post(
                "/api/v1/orders/",
                headers=auth_headers,
                json={
                    "symbol": "BTCUSDT",
                    "side": "BUY",
                    "order_type": "MARKET",
                    "quantity": "0.1"
                }
            )
            assert order_response.status_code == 200
            
            # 계정 잔액 확인
            account_response = client.get("/api/v1/account/", headers=auth_headers)
            data = account_response.json()
            
            # 잔액이 감소했는지 확인
            balance = Decimal(str(data["balance"]))
            assert balance < Decimal("1000000")
            
            # 예상 잔액 계산 (초기 잔액 - 주문금액 - 수수료)
            order_cost = Decimal("50000") * Decimal("0.1")
            fee = order_cost * Decimal("0.001")
            expected_balance = Decimal("1000000") - order_cost - fee
            assert balance == expected_balance


class TestPositionAPI:
    """포지션 관련 API 테스트"""
    
    def test_get_positions_empty(self, client, auth_headers, test_account):
        """포지션이 없을 때 빈 리스트 반환"""
        response = client.get("/api/v1/positions/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    
    def test_get_positions_with_data(self, client, auth_headers, test_position):
        """포지션이 있을 때 정상 반환"""
        response = client.get("/api/v1/positions/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        
        position = data[0]
        assert position["symbol"] == "BTCUSDT"
        assert Decimal(str(position["quantity"])) == Decimal("0.1")
        assert Decimal(str(position["average_price"])) == Decimal("50000")
    
    
    def test_get_positions_multiple(self, client, auth_headers, test_multiple_positions):
        """여러 포지션 조회"""
        response = client.get("/api/v1/positions/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        
        # 심볼 확인
        symbols = [pos["symbol"] for pos in data]
        assert "BTCUSDT" in symbols
        assert "ETHUSDT" in symbols
        assert "BNBUSDT" in symbols
    
    
    def test_get_single_position(self, client, auth_headers, test_position):
        """특정 심볼의 포지션 조회"""
        response = client.get("/api/v1/positions/BTCUSDT", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["symbol"] == "BTCUSDT"
        assert Decimal(str(data["quantity"])) == Decimal("0.1")
    
    
    def test_get_nonexistent_position(self, client, auth_headers, test_account):
        """존재하지 않는 포지션 조회 시 404"""
        response = client.get("/api/v1/positions/ETHUSDT", headers=auth_headers)
        assert response.status_code == 404
    
    
    def test_positions_without_auth(self, client):
        """인증 없이 포지션 조회 시도 시 실패"""
        response = client.get("/api/v1/positions/")
        assert response.status_code == 401
    
    
    def test_position_unrealized_profit(self, client, auth_headers, test_position):
        """포지션의 미실현 손익 확인"""
        with patch("app.services.binance_service.get_current_price") as mock_price:
            # 현재가가 상승한 상황
            mock_price.return_value = Decimal("55000")
            
            response = client.get("/api/v1/positions/BTCUSDT", headers=auth_headers)
            data = response.json()
            
            # 미실현 손익 = (현재가 - 평균가) * 수량
            expected_profit = (Decimal("55000") - Decimal("50000")) * Decimal("0.1")
            
            # 실제 계산된 미실현 손익 확인
            if "unrealized_profit" in data:
                actual_profit = Decimal(str(data["unrealized_profit"]))
                assert actual_profit == expected_profit


class TestOrderAPI:
    """주문 관련 API 테스트"""
    
    def test_create_buy_market_order_success(self, client, auth_headers, test_account):
        """시장가 매수 주문 생성 성공"""
        with patch("app.services.binance_service.get_current_price") as mock_price:
            mock_price.return_value = Decimal("50000")
            
            response = client.post(
                "/api/v1/orders/",
                headers=auth_headers,
                json={
                    "symbol": "BTCUSDT",
                    "side": "BUY",
                    "order_type": "MARKET",
                    "quantity": "0.1"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["symbol"] == "BTCUSDT"
            assert data["side"] == "BUY"
            assert data["status"] == "FILLED"
            assert Decimal(str(data["quantity"])) == Decimal("0.1")
    
    
    def test_create_sell_market_order_success(self, client, auth_headers, test_position):
        """시장가 매도 주문 생성 성공"""
        with patch("app.services.binance_service.get_current_price") as mock_price:
            mock_price.return_value = Decimal("51000")
            
            response = client.post(
                "/api/v1/orders/",
                headers=auth_headers,
                json={
                    "symbol": "BTCUSDT",
                    "side": "SELL",
                    "order_type": "MARKET",
                    "quantity": "0.05"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["side"] == "SELL"
            assert data["status"] == "FILLED"
    
    
    def test_create_limit_order(self, client, auth_headers, test_account):
        """지정가 주문 생성"""
        response = client.post(
            "/api/v1/orders/",
            headers=auth_headers,
            json={
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "LIMIT",
                "quantity": "0.1",
                "price": "48000"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["order_type"] == "LIMIT"
        assert data["status"] == "PENDING"
        assert Decimal(str(data["price"])) == Decimal("48000")
    
    
    def test_create_order_insufficient_balance(self, client, auth_headers, test_account_low_balance):
        """잔액 부족 시 주문 생성 실패"""
        with patch("app.services.binance_service.get_current_price") as mock_price:
            mock_price.return_value = Decimal("50000")
            
            response = client.post(
                "/api/v1/orders/",
                headers=auth_headers,
                json={
                    "symbol": "BTCUSDT",
                    "side": "BUY",
                    "order_type": "MARKET",
                    "quantity": "1.0"  # 50000원 필요, 잔액 1000원
                }
            )
            
            assert response.status_code in [400, 422]
            assert "insufficient" in response.json()["detail"].lower() or "부족" in response.json()["detail"]
    
    
    def test_create_order_insufficient_position(self, client, auth_headers, test_position):
        """보유량 부족 시 매도 주문 실패"""
        with patch("app.services.binance_service.get_current_price") as mock_price:
            mock_price.return_value = Decimal("50000")
            
            response = client.post(
                "/api/v1/orders/",
                headers=auth_headers,
                json={
                    "symbol": "BTCUSDT",
                    "side": "SELL",
                    "order_type": "MARKET",
                    "quantity": "1.0"  # 보유량 0.1개보다 많음
                }
            )
            
            assert response.status_code in [400, 422]
    
    
    def test_create_order_invalid_symbol(self, client, auth_headers, test_account):
        """유효하지 않은 심볼로 주문 생성 시도"""
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
    
    
    def test_create_order_invalid_quantity(self, client, auth_headers, test_account):
        """잘못된 수량으로 주문 생성 시도"""
        # 음수 수량
        response = client.post(
            "/api/v1/orders/",
            headers=auth_headers,
            json={
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "MARKET",
                "quantity": "-0.1"
            }
        )
        assert response.status_code == 422
        
        # 0 수량
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
    
    
    def test_create_order_missing_fields(self, client, auth_headers, test_account):
        """필수 필드 누락 시 주문 생성 실패"""
        # symbol 누락
        response = client.post(
            "/api/v1/orders/",
            headers=auth_headers,
            json={
                "side": "BUY",
                "order_type": "MARKET",
                "quantity": "0.1"
            }
        )
        assert response.status_code == 422
        
        # quantity 누락
        response = client.post(
            "/api/v1/orders/",
            headers=auth_headers,
            json={
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "MARKET"
            }
        )
        assert response.status_code == 422
    
    
    def test_create_order_without_auth(self, client):
        """인증 없이 주문 생성 시도 시 실패"""
        response = client.post(
            "/api/v1/orders/",
            json={
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "MARKET",
                "quantity": "0.1"
            }
        )
        assert response.status_code == 401
    
    
    def test_get_orders_empty(self, client, auth_headers, test_account):
        """주문 목록 조회 - 주문 없을 때"""
        response = client.get("/api/v1/orders/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    
    def test_get_orders_with_data(self, client, auth_headers, test_filled_order):
        """주문 목록 조회 - 주문 있을 때"""
        response = client.get("/api/v1/orders/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        order = data[0]
        assert "symbol" in order
        assert "side" in order
        assert "status" in order
    
    
    def test_get_orders_with_symbol_filter(self, client, auth_headers, test_multiple_orders):
        """특정 심볼로 주문 목록 필터링"""
        response = client.get(
            "/api/v1/orders/?symbol=BTCUSDT",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 모든 주문이 BTCUSDT인지 확인
        for order in data:
            assert order["symbol"] == "BTCUSDT"
    
    
    def test_get_orders_with_status_filter(self, client, auth_headers, test_multiple_orders):
        """특정 상태로 주문 목록 필터링"""
        response = client.get(
            "/api/v1/orders/?status=FILLED",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 모든 주문이 FILLED 상태인지 확인
        for order in data:
            assert order["status"] == "FILLED"
    
    
    def test_get_orders_with_multiple_filters(self, client, auth_headers, test_multiple_orders):
        """여러 필터 동시 적용"""
        response = client.get(
            "/api/v1/orders/?symbol=BTCUSDT&status=FILLED",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for order in data:
            assert order["symbol"] == "BTCUSDT"
            assert order["status"] == "FILLED"
    
    
    def test_get_single_order(self, client, auth_headers, test_filled_order):
        """특정 주문 조회"""
        order_id = test_filled_order.id
        response = client.get(f"/api/v1/orders/{order_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == order_id
        assert data["symbol"] == "BTCUSDT"
    
    
    def test_get_nonexistent_order(self, client, auth_headers, test_account):
        """존재하지 않는 주문 조회 시 404"""
        response = client.get("/api/v1/orders/99999", headers=auth_headers)
        assert response.status_code == 404
    
    
    def test_cancel_pending_order(self, client, auth_headers, test_pending_order):
        """대기 중인 주문 취소"""
        order_id = test_pending_order.id
        response = client.delete(f"/api/v1/orders/{order_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "CANCELLED"
    
    
    def test_cancel_filled_order(self, client, auth_headers, test_filled_order):
        """체결된 주문 취소 시도 시 실패"""
        order_id = test_filled_order.id
        response = client.delete(f"/api/v1/orders/{order_id}", headers=auth_headers)
        
        assert response.status_code in [400, 422]


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
            assert len(data) >= 2
            
            # BTC 정보 확인
            btc = next((coin for coin in data if coin["symbol"] == "BTCUSDT"), None)
            assert btc is not None
            assert "price" in btc
            assert "change" in btc
    
    
    def test_get_coin_detail(self, client):
        """특정 코인 상세 정보 조회"""
        with patch("app.services.binance_service.get_current_price") as mock_price:
            mock_price.return_value = Decimal("50000")
            
            response = client.get("/api/v1/market/coin/BTCUSDT")
            
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "BTCUSDT"
            assert "price" in data
            assert Decimal(str(data["price"])) == Decimal("50000")
    
    
    def test_get_coin_detail_invalid_symbol(self, client):
        """유효하지 않은 심볼로 코인 조회 시도"""
        response = client.get("/api/v1/market/coin/INVALID")
        assert response.status_code in [400, 404]
    
    
    def test_get_historical_data(self, client):
        """과거 가격 데이터 조회"""
        with patch("app.services.binance_service.get_historical_klines") as mock_klines:
            mock_klines.return_value = [
                {"timestamp": 1609459200, "open": 29000, "high": 29500, "low": 28500, "close": 29200, "volume": 1000},
                {"timestamp": 1609545600, "open": 29200, "high": 30000, "low": 29000, "close": 29800, "volume": 1200}
            ]
            
            response = client.get("/api/v1/market/history/BTCUSDT?interval=1d&limit=2")
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 2
            
            # 데이터 구조 확인
            candle = data[0]
            assert "timestamp" in candle
            assert "open" in candle
            assert "high" in candle
            assert "low" in candle
            assert "close" in candle
            assert "volume" in candle