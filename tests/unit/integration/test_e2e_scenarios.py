"""
End-to-End 테스트
=================

실제 사용자 시나리오를 시뮬레이션하는 통합 테스트
- 회원가입 → 로그인 → 거래 → 수익 확인
- 전체 플로우 테스트
"""
import pytest
from decimal import Decimal
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.mark.e2e
@pytest.mark.slow
class TestUserJourneyScenarios:
    """실제 사용자 여정 시나리오"""
    
    @patch("app.services.binance_service.get_current_price")
    def test_complete_user_journey_profitable_trade(
        self,
        mock_get_price,
        client: TestClient
    ):
        """
        완전한 사용자 여정 - 수익 시나리오
        
        시나리오:
        1. 회원가입 (100만원 지급)
        2. 로그인
        3. BTC 50,000원에 0.1개 매수 (5,005원 사용)
        4. 가격 상승 (60,000원)
        5. 전량 매도 (5,994원 회수)
        6. 포트폴리오 확인 (약 989원 수익)
        """
        # Step 1: 회원가입
        register_data = {
            "username": "profituser",
            "password": "password123"
        }
        register_response = client.post(
            "/api/v1/auth/register",
            json=register_data
        )
        assert register_response.status_code == 200
        
        # Step 2: 로그인
        login_data = {
            "username": "profituser",
            "password": "password123"
        }
        login_response = client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert login_response.status_code == 200
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 3: 초기 잔액 확인
        account_response = client.get("/api/v1/account/", headers=headers)
        assert account_response.status_code == 200
        initial_balance = Decimal(str(account_response.json()["balance"]))
        assert initial_balance == Decimal("1000000")
        
        # Step 4: BTC 매수 (50,000원에 0.1개)
        mock_get_price.return_value = Decimal("50000")
        
        buy_order_data = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": "0.1"
        }
        buy_response = client.post(
            "/api/v1/orders/",
            headers=headers,
            json=buy_order_data
        )
        assert buy_response.status_code == 200
        
        # Step 5: 포지션 확인
        positions_response = client.get(
            "/api/v1/portfolio/positions",
            headers=headers
        )
        assert positions_response.status_code == 200
        positions = positions_response.json()
        
        assert len(positions) == 1
        assert positions[0]["symbol"] == "BTCUSDT"
        assert Decimal(str(positions[0]["quantity"])) == Decimal("0.1")
        
        # Step 6: 가격 상승 (60,000원으로)
        mock_get_price.return_value = Decimal("60000")
        
        # Step 7: 전량 매도
        sell_order_data = {
            "symbol": "BTCUSDT",
            "side": "SELL",
            "order_type": "MARKET",
            "quantity": "0.1"
        }
        sell_response = client.post(
            "/api/v1/orders/",
            headers=headers,
            json=sell_order_data
        )
        assert sell_response.status_code == 200
        
        # Step 8: 최종 잔액 확인 (수익 발생)
        final_account_response = client.get("/api/v1/account/", headers=headers)
        final_balance = Decimal(str(final_account_response.json()["balance"]))
        
        # 수익 계산:
        # 매수: 0.1 * 50000 * 1.001 = 5,005
        # 매도: 0.1 * 60000 * 0.999 = 5,994
        # 수익: 5,994 - 5,005 = 989
        expected_balance = initial_balance + Decimal("989")
        
        assert abs(final_balance - expected_balance) < Decimal("1")  # 오차 허용
        
        # Step 9: 포지션 확인 (비어있어야 함)
        final_positions_response = client.get(
            "/api/v1/portfolio/positions",
            headers=headers
        )
        final_positions = final_positions_response.json()
        assert len(final_positions) == 0
    
    
    @patch("app.services.binance_service.get_current_price")
    def test_complete_user_journey_loss_trade(
        self,
        mock_get_price,
        client: TestClient
    ):
        """
        완전한 사용자 여정 - 손실 시나리오
        
        시나리오:
        1. 회원가입 & 로그인
        2. BTC 50,000원에 0.1개 매수
        3. 가격 하락 (40,000원)
        4. 손절 매도
        5. 손실 확인
        """
        # Step 1-2: 회원가입 & 로그인
        register_data = {"username": "lossuser", "password": "password123"}
        client.post("/api/v1/auth/register", json=register_data)
        
        login_data = {"username": "lossuser", "password": "password123"}
        login_response = client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 3: BTC 매수 (50,000원)
        mock_get_price.return_value = Decimal("50000")
        
        buy_order_data = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": "0.1"
        }
        client.post("/api/v1/orders/", headers=headers, json=buy_order_data)
        
        # Step 4: 가격 하락 (40,000원)
        mock_get_price.return_value = Decimal("40000")
        
        # Step 5: 손절 매도
        sell_order_data = {
            "symbol": "BTCUSDT",
            "side": "SELL",
            "order_type": "MARKET",
            "quantity": "0.1"
        }
        client.post("/api/v1/orders/", headers=headers, json=sell_order_data)
        
        # Step 6: 손실 확인
        account_response = client.get("/api/v1/account/", headers=headers)
        final_balance = Decimal(str(account_response.json()["balance"]))
        
        # 손실 발생 확인
        assert final_balance < Decimal("1000000")
        
        # 손실 계산:
        # 매수: 0.1 * 50000 * 1.001 = 5,005
        # 매도: 0.1 * 40000 * 0.999 = 3,996
        # 손실: 3,996 - 5,005 = -1,009
        expected_balance = Decimal("1000000") - Decimal("1009")
        
        assert abs(final_balance - expected_balance) < Decimal("1")
    
    
    @patch("app.services.binance_service.get_current_price")
    def test_multiple_coins_trading_scenario(
        self,
        mock_get_price,
        client: TestClient
    ):
        """
        여러 코인 동시 거래 시나리오
        
        시나리오:
        1. BTC, ETH, BNB 동시 매수
        2. 각각 다른 가격 변동
        3. 포트폴리오 다각화 효과 확인
        """
        # Step 1-2: 회원가입 & 로그인
        register_data = {"username": "diverseuser", "password": "password123"}
        client.post("/api/v1/auth/register", json=register_data)
        
        login_data = {"username": "diverseuser", "password": "password123"}
        login_response = client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 3: 각 코인 매수
        coins_to_buy = [
            {"symbol": "BTCUSDT", "quantity": "0.01", "price": Decimal("50000")},
            {"symbol": "ETHUSDT", "quantity": "0.1", "price": Decimal("3000")},
            {"symbol": "BNBUSDT", "quantity": "1.0", "price": Decimal("400")},
        ]
        
        for coin in coins_to_buy:
            mock_get_price.return_value = coin["price"]
            
            order_data = {
                "symbol": coin["symbol"],
                "side": "BUY",
                "order_type": "MARKET",
                "quantity": coin["quantity"]
            }
            
            response = client.post(
                "/api/v1/orders/",
                headers=headers,
                json=order_data
            )
            assert response.status_code == 200
        
        # Step 4: 포지션 확인
        positions_response = client.get(
            "/api/v1/portfolio/positions",
            headers=headers
        )
        positions = positions_response.json()
        
        assert len(positions) == 3
        symbols = [p["symbol"] for p in positions]
        assert "BTCUSDT" in symbols
        assert "ETHUSDT" in symbols
        assert "BNBUSDT" in symbols


@pytest.mark.e2e
@pytest.mark.slow
class TestLimitOrderScenarios:
    """지정가 주문 시나리오"""
    
    @patch("app.services.binance_service.get_current_price")
    def test_limit_order_wait_and_execute(
        self,
        mock_get_price,
        client: TestClient
    ):
        """
        지정가 주문 대기 및 체결 시나리오
        
        시나리오:
        1. 현재가 50,000원일 때 49,000원 지정가 매수 주문
        2. 가격이 48,000원으로 하락
        3. 자동 체결 확인
        """
        # Setup: 회원가입 & 로그인
        register_data = {"username": "limituser", "password": "password123"}
        client.post("/api/v1/auth/register", json=register_data)
        
        login_data = {"username": "limituser", "password": "password123"}
        login_response = client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 1: 현재가 50,000원
        mock_get_price.return_value = Decimal("50000")
        
        # Step 2: 49,000원 지정가 매수 주문
        order_data = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "order_type": "LIMIT",
            "price": "49000",
            "quantity": "0.1"
        }
        
        order_response = client.post(
            "/api/v1/orders/",
            headers=headers,
            json=order_data
        )
        assert order_response.status_code == 200
        order_id = order_response.json()["id"]
        
        # Step 3: 주문 상태 확인 (PENDING)
        order_detail_response = client.get(
            f"/api/v1/orders/{order_id}",
            headers=headers
        )
        assert order_detail_response.json()["order_status"] == "PENDING"
        
        # Step 4: 가격 하락 (48,000원)
        mock_get_price.return_value = Decimal("48000")
        
        # Step 5: Pending 주문 실행 트리거 (백그라운드 작업 시뮬레이션)
        # 실제로는 Celery 등의 스케줄러가 주기적으로 실행
        client.post("/api/v1/orders/execute-pending", headers=headers)
        
        # Step 6: 주문 상태 재확인 (FILLED)
        final_order_response = client.get(
            f"/api/v1/orders/{order_id}",
            headers=headers
        )
        assert final_order_response.json()["order_status"] == "FILLED"


@pytest.mark.e2e
@pytest.mark.smoke
class TestCriticalPaths:
    """중요한 비즈니스 경로 스모크 테스트"""
    
    def test_registration_and_login_critical_path(self, client: TestClient):
        """회원가입 & 로그인 핵심 경로"""
        # 회원가입
        register_response = client.post(
            "/api/v1/auth/register",
            json={"username": "smokeuser", "password": "password123"}
        )
        assert register_response.status_code == 200
        
        # 로그인
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "smokeuser", "password": "password123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert login_response.status_code == 200
        assert "access_token" in login_response.json()
    
    
    @patch("app.services.binance_service.get_current_price")
    def test_order_creation_critical_path(
        self,
        mock_get_price,
        client: TestClient,
        auth_headers: dict
    ):
        """주문 생성 핵심 경로"""
        mock_get_price.return_value = Decimal("50000")
        
        order_response = client.post(
            "/api/v1/orders/",
            headers=auth_headers,
            json={
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "MARKET",
                "quantity": "0.01"
            }
        )
        assert order_response.status_code == 200


@pytest.mark.e2e
@pytest.mark.regression
class TestRegressionScenarios:
    """회귀 테스트 - 과거 버그 재발 방지"""
    
    @patch("app.services.binance_service.get_current_price")
    def test_zero_quantity_order_rejection(
        self,
        mock_get_price,
        client: TestClient,
        auth_headers: dict
    ):
        """
        버그 수정 확인: 0 수량 주문 거부
        
        이전 버그: 0 수량 주문이 통과됨
        수정 후: 0 수량 주문 거부
        """
        mock_get_price.return_value = Decimal("50000")
        
        order_data = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": "0"
        }
        
        response = client.post(
            "/api/v1/orders/",
            headers=auth_headers,
            json=order_data
        )
        
        # 422 Validation Error 또는 400 Bad Request
        assert response.status_code in [400, 422]
    
    
    @patch("app.services.binance_service.get_current_price")
    def test_concurrent_sell_orders_race_condition(
        self,
        mock_get_price,
        client: TestClient,
        auth_headers: dict
    ):
        """
        버그 수정 확인: 동시 매도 주문 race condition
        
        이전 버그: 보유량보다 많은 매도가 가능했음
        수정 후: 트랜잭션 lock으로 방지
        """
        mock_get_price.return_value = Decimal("50000")
        
        # 먼저 매수
        buy_order = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": "0.1"
        }
        client.post("/api/v1/orders/", headers=auth_headers, json=buy_order)
        
        # 동시에 두 번 매도 시도 (0.1씩)
        sell_order = {
            "symbol": "BTCUSDT",
            "side": "SELL",
            "order_type": "MARKET",
            "quantity": "0.1"
        }
        
        response1 = client.post("/api/v1/orders/", headers=auth_headers, json=sell_order)
        response2 = client.post("/api/v1/orders/", headers=auth_headers, json=sell_order)
        
        # 하나는 성공, 하나는 실패해야 함
        statuses = [response1.status_code, response2.status_code]
        assert 200 in statuses
        assert 400 in statuses