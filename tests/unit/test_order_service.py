"""
주문 서비스 API 테스트 - 백엔드 완전 연동 버전
===========================================

현재 백엔드 API 구조:
- POST /api/v1/orders/ (주문 생성)
- GET  /api/v1/orders/ (주문 목록)
- GET  /api/v1/orders/{order_id} (주문 조회)
- DELETE /api/v1/orders/{order_id} (주문 취소)

주요 수정:
1. 실제 API 엔드포인트 사용
2. 비동기 주문 서비스 함수 호출
3. Enum 타입 처리
4. locked_balance 로직 반영
5. 최근 체결 내역 Mock 추가
"""
import pytest
from fastapi.testclient import TestClient
from decimal import Decimal
from unittest.mock import patch, AsyncMock
from datetime import datetime

from app.models.database import User, TradingAccount, Order, Position, OrderSide, OrderType, OrderStatus
from sqlmodel import Session, select


# =============================================================================
# 주문 생성 API 테스트
# =============================================================================

@pytest.mark.integration
@pytest.mark.order
class TestOrderCreationAPI:
    """주문 생성 API 테스트"""
    
    @patch("app.services.binance_service.get_current_price")
    @patch("app.services.binance_service.get_recent_trades")
    def test_create_market_buy_order_success(
        self,
        mock_get_trades,
        mock_get_price,
        client: TestClient,
        db_session: Session
    ):
        """
        시장가 매수 주문 생성 성공
        
        POST /api/v1/orders/
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        mock_get_trades.return_value = [
            {"price": "50000", "qty": "0.1"},
        ]
        
        # 사용자 생성 & 로그인
        client.post(
            "/api/v1/auth/register",
            json={"username": "trader1", "password": "password123"}
        )
        
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "trader1", "password": "password123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        order_data = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": 0.1
        }
        
        # Act
        response = client.post(
            "/api/v1/orders/",
            headers=headers,
            json=order_data
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["symbol"] == "BTCUSDT"
        assert data["side"] == "BUY"
        assert data["order_status"] == "FILLED"
        assert data["filled_quantity"] == 0.1
        assert data["average_price"] is not None
    
    
    @patch("app.services.binance_service.get_current_price")
    def test_create_limit_order_pending(
        self,
        mock_get_price,
        client: TestClient
    ):
        """
        지정가 주문 생성 (PENDING 상태)
        
        POST /api/v1/orders/
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        
        # 사용자 생성 & 로그인
        client.post(
            "/api/v1/auth/register",
            json={"username": "trader2", "password": "password123"}
        )
        
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "trader2", "password": "password123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        order_data = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "order_type": "LIMIT",
            "price": 49000,  # 현재가보다 낮음
            "quantity": 0.1
        }
        
        # Act
        response = client.post(
            "/api/v1/orders/",
            headers=headers,
            json=order_data
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["order_status"] == "PENDING"
        assert data["price"] == 49000
        assert data["filled_quantity"] == 0
    
    
    @patch("app.services.binance_service.get_current_price")
    def test_create_order_insufficient_balance(
        self,
        mock_get_price,
        client: TestClient,
        db_session: Session
    ):
        """
        잔액 부족 시 주문 실패
        
        POST /api/v1/orders/ → 400
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        
        # 사용자 생성
        client.post(
            "/api/v1/auth/register",
            json={"username": "poortrader", "password": "password123"}
        )
        
        # 잔액을 1000원으로 감소
        user = db_session.exec(
            select(User).where(User.username == "poortrader")
        ).first()
        
        account = db_session.exec(
            select(TradingAccount).where(TradingAccount.user_id == user.id)
        ).first()
        account.balance = Decimal("1000")
        db_session.add(account)
        db_session.commit()
        
        # 로그인
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "poortrader", "password": "password123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        order_data = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": 10  # 50만원 상당
        }
        
        # Act
        response = client.post(
            "/api/v1/orders/",
            headers=headers,
            json=order_data
        )
        
        # Assert
        assert response.status_code == 400
        assert "잔액" in response.json()["detail"]
    
    
    @patch("app.services.binance_service.get_current_price")
    @patch("app.services.binance_service.get_recent_trades")
    def test_create_sell_order_success(
        self,
        mock_get_trades,
        mock_get_price,
        client: TestClient,
        db_session: Session
    ):
        """
        매도 주문 생성 성공
        
        POST /api/v1/orders/
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        mock_get_trades.return_value = [
            {"price": "50000", "qty": "0.1"},
        ]
        
        # 사용자 생성 & 로그인
        client.post(
            "/api/v1/auth/register",
            json={"username": "seller1", "password": "password123"}
        )
        
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "seller1", "password": "password123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 먼저 매수하여 포지션 생성
        buy_order_data = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": 0.1
        }
        client.post("/api/v1/orders/", headers=headers, json=buy_order_data)
        
        # Act - 매도
        sell_order_data = {
            "symbol": "BTCUSDT",
            "side": "SELL",
            "order_type": "MARKET",
            "quantity": 0.1
        }
        response = client.post(
            "/api/v1/orders/",
            headers=headers,
            json=sell_order_data
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["side"] == "SELL"
        assert data["order_status"] == "FILLED"
    
    
    @patch("app.services.binance_service.get_current_price")
    def test_create_sell_order_insufficient_quantity(
        self,
        mock_get_price,
        client: TestClient
    ):
        """
        수량 부족 시 매도 실패
        
        POST /api/v1/orders/ → 400
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        
        # 사용자 생성 & 로그인
        client.post(
            "/api/v1/auth/register",
            json={"username": "noseller", "password": "password123"}
        )
        
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "noseller", "password": "password123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 보유하지 않은 코인 매도 시도
        sell_order_data = {
            "symbol": "BTCUSDT",
            "side": "SELL",
            "order_type": "MARKET",
            "quantity": 0.1
        }
        
        # Act
        response = client.post(
            "/api/v1/orders/",
            headers=headers,
            json=sell_order_data
        )
        
        # Assert
        assert response.status_code == 400
        assert "수량" in response.json()["detail"] or "insufficient" in response.json()["detail"].lower()


# =============================================================================
# 주문 조회 API 테스트
# =============================================================================

@pytest.mark.integration
@pytest.mark.order
class TestOrderRetrievalAPI:
    """주문 조회 API 테스트"""
    
    @patch("app.services.binance_service.get_current_price")
    @patch("app.services.binance_service.get_recent_trades")
    def test_get_orders_list(
        self,
        mock_get_trades,
        mock_get_price,
        client: TestClient
    ):
        """
        주문 목록 조회
        
        GET /api/v1/orders/
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        mock_get_trades.return_value = [
            {"price": "50000", "qty": "0.01"},
        ]
        
        # 사용자 생성 & 로그인
        client.post(
            "/api/v1/auth/register",
            json={"username": "listuser", "password": "password123"}
        )
        
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "listuser", "password": "password123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 여러 주문 생성
        for i in range(3):
            order_data = {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "MARKET",
                "quantity": 0.01
            }
            client.post("/api/v1/orders/", headers=headers, json=order_data)
        
        # Act
        response = client.get("/api/v1/orders/", headers=headers)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3
        assert all("id" in order for order in data)
        assert all("symbol" in order for order in data)
    
    
    @patch("app.services.binance_service.get_current_price")
    def test_get_orders_by_symbol(
        self,
        mock_get_price,
        client: TestClient
    ):
        """
        특정 심볼 필터링
        
        GET /api/v1/orders/?symbol=BTCUSDT
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        
        # 사용자 생성 & 로그인
        client.post(
            "/api/v1/auth/register",
            json={"username": "filteruser", "password": "password123"}
        )
        
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "filteruser", "password": "password123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Act
        response = client.get(
            "/api/v1/orders/?symbol=BTCUSDT",
            headers=headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert all(order["symbol"] == "BTCUSDT" for order in data)
    
    
    @patch("app.services.binance_service.get_current_price")
    @patch("app.services.binance_service.get_recent_trades")
    def test_get_single_order(
        self,
        mock_get_trades,
        mock_get_price,
        client: TestClient
    ):
        """
        특정 주문 조회
        
        GET /api/v1/orders/{order_id}
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        mock_get_trades.return_value = [
            {"price": "50000", "qty": "0.1"},
        ]
        
        # 사용자 생성 & 로그인
        client.post(
            "/api/v1/auth/register",
            json={"username": "singleuser", "password": "password123"}
        )
        
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "singleuser", "password": "password123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 주문 생성
        order_response = client.post(
            "/api/v1/orders/",
            headers=headers,
            json={
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "MARKET",
                "quantity": 0.1
            }
        )
        order_id = order_response.json()["id"]
        
        # Act
        response = client.get(f"/api/v1/orders/{order_id}", headers=headers)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == order_id
        assert data["symbol"] == "BTCUSDT"


# =============================================================================
# 주문 취소 API 테스트
# =============================================================================

@pytest.mark.integration
@pytest.mark.order
class TestOrderCancellationAPI:
    """주문 취소 API 테스트"""
    
    @patch("app.services.binance_service.get_current_price")
    def test_cancel_pending_order_success(
        self,
        mock_get_price,
        client: TestClient
    ):
        """
        대기 주문 취소 성공
        
        DELETE /api/v1/orders/{order_id}
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        
        # 사용자 생성 & 로그인
        client.post(
            "/api/v1/auth/register",
            json={"username": "canceluser", "password": "password123"}
        )
        
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "canceluser", "password": "password123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 지정가 주문 생성 (PENDING)
        order_response = client.post(
            "/api/v1/orders/",
            headers=headers,
            json={
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "LIMIT",
                "price": 49000,
                "quantity": 0.1
            }
        )
        order_id = order_response.json()["id"]
        
        # Act
        response = client.delete(f"/api/v1/orders/{order_id}", headers=headers)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["order_status"] == "CANCELLED"
    
    
    @patch("app.services.binance_service.get_current_price")
    @patch("app.services.binance_service.get_recent_trades")
    def test_cancel_filled_order_fails(
        self,
        mock_get_trades,
        mock_get_price,
        client: TestClient
    ):
        """
        체결된 주문 취소 실패
        
        DELETE /api/v1/orders/{order_id} → 400
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        mock_get_trades.return_value = [
            {"price": "50000", "qty": "0.1"},
        ]
        
        # 사용자 생성 & 로그인
        client.post(
            "/api/v1/auth/register",
            json={"username": "filleduser", "password": "password123"}
        )
        
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "filleduser", "password": "password123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 시장가 주문 생성 (즉시 체결)
        order_response = client.post(
            "/api/v1/orders/",
            headers=headers,
            json={
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "MARKET",
                "quantity": 0.1
            }
        )
        order_id = order_response.json()["id"]
        
        # Act
        response = client.delete(f"/api/v1/orders/{order_id}", headers=headers)
        
        # Assert
        assert response.status_code == 400
        assert "취소할 수 없는" in response.json()["detail"]
    
    
    @patch("app.services.binance_service.get_current_price")
    def test_cancel_other_users_order_fails(
        self,
        mock_get_price,
        client: TestClient
    ):
        """
        다른 사용자의 주문 취소 실패
        
        DELETE /api/v1/orders/{order_id} → 403
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        
        # 첫 번째 사용자 - 주문 생성
        client.post(
            "/api/v1/auth/register",
            json={"username": "owner", "password": "password123"}
        )
        
        login1 = client.post(
            "/api/v1/auth/login",
            data={"username": "owner", "password": "password123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        token1 = login1.json()["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}
        
        order_response = client.post(
            "/api/v1/orders/",
            headers=headers1,
            json={
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "LIMIT",
                "price": 49000,
                "quantity": 0.1
            }
        )
        order_id = order_response.json()["id"]
        
        # 두 번째 사용자 - 취소 시도
        client.post(
            "/api/v1/auth/register",
            json={"username": "hacker", "password": "password123"}
        )
        
        login2 = client.post(
            "/api/v1/auth/login",
            data={"username": "hacker", "password": "password123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        token2 = login2.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        # Act
        response = client.delete(f"/api/v1/orders/{order_id}", headers=headers2)
        
        # Assert
        assert response.status_code == 403
        assert "권한" in response.json()["detail"]


# =============================================================================
# E2E 시나리오 테스트
# =============================================================================

@pytest.mark.e2e
@pytest.mark.order
class TestOrderEndToEnd:
    """주문 전체 플로우 테스트"""
    
    @patch("app.services.binance_service.get_current_price")
    @patch("app.services.binance_service.get_recent_trades")
    def test_complete_trading_cycle(
        self,
        mock_get_trades,
        mock_get_price,
        client: TestClient
    ):
        """
        완전한 거래 사이클
        
        1. 회원가입
        2. 로그인
        3. 매수 주문
        4. 주문 확인
        5. 매도 주문
        6. 최종 확인
        """
        # Setup
        mock_get_price.return_value = Decimal("50000")
        mock_get_trades.return_value = [
            {"price": "50000", "qty": "0.1"},
        ]
        
        # Step 1: 회원가입
        register_response = client.post(
            "/api/v1/auth/register",
            json={"username": "fullcycle", "password": "password123"}
        )
        assert register_response.status_code == 200
        
        # Step 2: 로그인
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "fullcycle", "password": "password123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 3: 매수 주문
        buy_response = client.post(
            "/api/v1/orders/",
            headers=headers,
            json={
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "MARKET",
                "quantity": 0.1
            }
        )
        assert buy_response.status_code == 201
        
        # Step 4: 주문 확인
        orders_response = client.get("/api/v1/orders/", headers=headers)
        assert orders_response.status_code == 200
        assert len(orders_response.json()) >= 1
        
        # Step 5: 매도 주문
        sell_response = client.post(
            "/api/v1/orders/",
            headers=headers,
            json={
                "symbol": "BTCUSDT",
                "side": "SELL",
                "order_type": "MARKET",
                "quantity": 0.1
            }
        )
        assert sell_response.status_code == 201
        
        # Step 6: 최종 확인
        final_orders = client.get("/api/v1/orders/", headers=headers)
        assert len(final_orders.json()) >= 2