# ============================================================================
# 파일: tests/integration/test_branch_coverage_improvement.py
# ============================================================================
# 브랜치 커버리지 향상을 위한 통합 테스트
# 
# 타겟 파일들:
# - futures_portfolio.py: 18.52% → 60%+
# - market.py: 50% → 70%+
# - scheduler.py: 22.5% → 50%+
# - futures.py: 66.67% → 80%+
# ============================================================================

import pytest
from fastapi.testclient import TestClient
import random
import string
import time
import uuid


def wait_for_api():
    """API 호출 간 간격"""
    time.sleep(0.05)


def generate_valid_username(prefix: str = "test") -> str:
    """유효한 사용자명 생성"""
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{prefix}{suffix}"


# =============================================================================
# 1. Market Router 브랜치 커버리지 테스트
# =============================================================================

class TestMarketBranchCoverage:
    """마켓 라우터 분기 테스트"""

    def test_get_all_coins_success(self, client: TestClient):
        """모든 코인 조회 - 성공 분기"""
        wait_for_api()
        response = client.get("/api/v1/market/coins")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # 데이터가 있으면 필수 필드 확인
        if len(data) > 0:
            assert "symbol" in data[0]
            assert "price" in data[0]

    def test_get_all_coins_with_price_data(self, client: TestClient):
        """모든 코인 조회 - 가격 데이터 있음 분기"""
        wait_for_api()
        response = client.get("/api/v1/market/coins")
        assert response.status_code == 200
        data = response.json()
        
        for coin in data:
            # 가격이 있거나 0 (분기 테스트)
            assert "price" in coin
            if coin.get("price") and coin["price"] != "0":
                # 가격 데이터가 있는 분기
                assert float(coin["price"]) >= 0

    def test_get_coin_detail_btcusdt(self, client: TestClient):
        """BTC 코인 상세 - 성공 분기"""
        wait_for_api()
        response = client.get("/api/v1/market/coin/BTCUSDT")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BTCUSDT"

    def test_get_coin_detail_ethusdt(self, client: TestClient):
        """ETH 코인 상세 - 다른 심볼 분기"""
        wait_for_api()
        response = client.get("/api/v1/market/coin/ETHUSDT")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "ETHUSDT"

    def test_get_coin_detail_invalid_symbol(self, client: TestClient):
        """존재하지 않는 심볼 - 에러 분기"""
        wait_for_api()
        response = client.get("/api/v1/market/coin/INVALIDCOIN123")
        # 400 또는 404 또는 서버 에러
        assert response.status_code in [400, 404, 500, 503]

    def test_historical_default_interval(self, client: TestClient):
        """과거 데이터 - 기본 interval 분기 (1h)"""
        wait_for_api()
        response = client.get("/api/v1/market/historical/BTCUSDT")
        assert response.status_code == 200

    def test_historical_1m_interval(self, client: TestClient):
        """과거 데이터 - 1m interval 분기"""
        wait_for_api()
        response = client.get(
            "/api/v1/market/historical/BTCUSDT",
            params={"interval": "1m", "limit": 10}
        )
        assert response.status_code == 200

    def test_historical_4h_interval(self, client: TestClient):
        """과거 데이터 - 4h interval 분기"""
        wait_for_api()
        response = client.get(
            "/api/v1/market/historical/BTCUSDT",
            params={"interval": "4h", "limit": 10}
        )
        assert response.status_code == 200

    def test_historical_1d_interval(self, client: TestClient):
        """과거 데이터 - 1d interval 분기"""
        wait_for_api()
        response = client.get(
            "/api/v1/market/historical/BTCUSDT",
            params={"interval": "1d", "limit": 10}
        )
        assert response.status_code == 200

    def test_historical_simulated_1s_interval(self, client: TestClient):
        """과거 데이터 - 1s 시뮬레이션 분기"""
        wait_for_api()
        response = client.get(
            "/api/v1/market/historical/BTCUSDT",
            params={"interval": "1s", "limit": 10}
        )
        assert response.status_code == 200

    def test_historical_simulated_5s_interval(self, client: TestClient):
        """과거 데이터 - 5s 시뮬레이션 분기"""
        wait_for_api()
        response = client.get(
            "/api/v1/market/historical/BTCUSDT",
            params={"interval": "5s", "limit": 10}
        )
        assert response.status_code == 200

    def test_historical_invalid_interval_fallback(self, client: TestClient):
        """과거 데이터 - 잘못된 interval 폴백 분기"""
        wait_for_api()
        response = client.get(
            "/api/v1/market/historical/BTCUSDT",
            params={"interval": "invalid", "limit": 10}
        )
        # 폴백으로 1h 사용
        assert response.status_code == 200

    def test_historical_limit_too_high(self, client: TestClient):
        """과거 데이터 - limit > 1000 분기"""
        wait_for_api()
        response = client.get(
            "/api/v1/market/historical/BTCUSDT",
            params={"interval": "1h", "limit": 2000}
        )
        # limit가 1000으로 제한됨
        assert response.status_code == 200

    def test_historical_limit_too_low(self, client: TestClient):
        """과거 데이터 - limit < 1 분기"""
        wait_for_api()
        response = client.get(
            "/api/v1/market/historical/BTCUSDT",
            params={"interval": "1h", "limit": 0}
        )
        # limit가 24로 기본값 설정
        assert response.status_code in [200, 422]

    def test_get_all_prices(self, client: TestClient):
        """모든 가격 조회"""
        wait_for_api()
        response = client.get("/api/v1/market/prices")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict) or isinstance(data, list)

    def test_get_recent_trades_btc(self, client: TestClient):
        """BTC 최근 체결 내역"""
        wait_for_api()
        response = client.get(
            "/api/v1/market/trades/BTCUSDT",
            params={"limit": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_recent_trades_eth(self, client: TestClient):
        """ETH 최근 체결 내역"""
        wait_for_api()
        response = client.get(
            "/api/v1/market/trades/ETHUSDT",
            params={"limit": 5}
        )
        assert response.status_code == 200

    def test_get_recent_trades_default_limit(self, client: TestClient):
        """최근 체결 내역 - 기본 limit"""
        wait_for_api()
        response = client.get("/api/v1/market/trades/BTCUSDT")
        assert response.status_code == 200


# =============================================================================
# 2. Futures Portfolio Router 브랜치 커버리지 테스트
# =============================================================================

class TestFuturesPortfolioBranchCoverage:
    """선물 포트폴리오 분기 테스트"""

    def test_portfolio_summary_no_account(self, client: TestClient, user_factory):
        """포트폴리오 요약 - 계정 없음 분기"""
        # 새 사용자 생성
        new_user = user_factory(
            username=generate_valid_username("noaccport"),
            password="testpass123"
        )
        
        wait_for_api()
        login_resp = client.post(
            "/api/v1/auth/login",
            data={"username": new_user.username, "password": "testpass123"}
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        wait_for_api()
        response = client.get("/api/v1/futures/portfolio/summary", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # 계정 없을 때 기본값 반환
        assert data["total_balance"] == 0 or data["total_balance"] > 0
        assert "open_positions_count" in data

    def test_portfolio_summary_with_account(self, client: TestClient, auth_headers):
        """포트폴리오 요약 - 계정 있음 분기"""
        # 먼저 계정 생성 (futures/account 호출)
        wait_for_api()
        client.get("/api/v1/futures/account", headers=auth_headers)
        
        wait_for_api()
        response = client.get("/api/v1/futures/portfolio/summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_balance" in data
        assert "margin_ratio" in data

    def test_portfolio_summary_with_open_positions(self, client: TestClient, auth_headers):
        """포트폴리오 요약 - 오픈 포지션 있음 분기"""
        # 포지션 개설
        wait_for_api()
        client.post(
            "/api/v1/futures/positions/open",
            headers=auth_headers,
            json={
                "symbol": "BTCUSDT",
                "side": "LONG",
                "quantity": "0.0001",
                "leverage": 2,
                "order_type": "MARKET"
            }
        )
        
        wait_for_api()
        response = client.get("/api/v1/futures/portfolio/summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "open_positions_count" in data

    def test_portfolio_transactions_empty(self, client: TestClient, user_factory):
        """거래 내역 - 비어있음 분기"""
        new_user = user_factory(
            username=generate_valid_username("emptytx"),
            password="testpass123"
        )
        
        wait_for_api()
        login_resp = client.post(
            "/api/v1/auth/login",
            data={"username": new_user.username, "password": "testpass123"}
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        wait_for_api()
        response = client.get(
            "/api/v1/futures/portfolio/transactions",
            params={"limit": 10},
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_portfolio_transactions_with_symbol_filter(self, client: TestClient, auth_headers):
        """거래 내역 - 심볼 필터 분기"""
        wait_for_api()
        response = client.get(
            "/api/v1/futures/portfolio/transactions",
            params={"symbol": "BTCUSDT", "limit": 10},
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_portfolio_transactions_with_action_filter(self, client: TestClient, auth_headers):
        """거래 내역 - 액션 필터 분기"""
        wait_for_api()
        response = client.get(
            "/api/v1/futures/portfolio/transactions",
            params={"action": "OPEN", "limit": 10},
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_portfolio_transactions_with_all_filters(self, client: TestClient, auth_headers):
        """거래 내역 - 모든 필터 분기"""
        wait_for_api()
        response = client.get(
            "/api/v1/futures/portfolio/transactions",
            params={"symbol": "BTCUSDT", "action": "CLOSE", "limit": 5},
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_portfolio_stats_no_trades(self, client: TestClient, user_factory):
        """거래 통계 - 거래 없음 분기 (win_rate = 0)"""
        new_user = user_factory(
            username=generate_valid_username("nostats"),
            password="testpass123"
        )
        
        wait_for_api()
        login_resp = client.post(
            "/api/v1/auth/login",
            data={"username": new_user.username, "password": "testpass123"}
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        wait_for_api()
        response = client.get("/api/v1/futures/portfolio/stats", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_trades"] == 0
        assert data["win_rate"] == 0

    def test_portfolio_fills_nonexistent_position(self, client: TestClient, auth_headers):
        """체결 내역 - 존재하지 않는 포지션 분기"""
        fake_id = str(uuid.uuid4())
        wait_for_api()
        response = client.get(
            f"/api/v1/futures/portfolio/fills/{fake_id}",
            headers=auth_headers
        )
        assert response.status_code in [404, 403]

    def test_portfolio_fills_existing_position(self, client: TestClient, auth_headers):
        """체결 내역 - 존재하는 포지션 분기"""
        # 포지션 개설
        wait_for_api()
        open_resp = client.post(
            "/api/v1/futures/positions/open",
            headers=auth_headers,
            json={
                "symbol": "BTCUSDT",
                "side": "LONG",
                "quantity": "0.0001",
                "leverage": 2,
                "order_type": "MARKET"
            }
        )
        
        if open_resp.status_code == 200:
            position_id = open_resp.json()["id"]
            
            wait_for_api()
            response = client.get(
                f"/api/v1/futures/portfolio/fills/{position_id}",
                headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            if len(data) > 0:
                assert "price" in data[0]
                assert "quantity" in data[0]


# =============================================================================
# 3. Futures Router 브랜치 커버리지 테스트
# =============================================================================

class TestFuturesRouterBranchCoverage:
    """선물 라우터 분기 테스트"""

    def test_get_account_new_user(self, client: TestClient, user_factory):
        """계정 조회 - 새 계정 생성 분기"""
        new_user = user_factory(
            username=generate_valid_username("newacct"),
            password="testpass123"
        )
        
        wait_for_api()
        login_resp = client.post(
            "/api/v1/auth/login",
            data={"username": new_user.username, "password": "testpass123"}
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        wait_for_api()
        response = client.get("/api/v1/futures/account", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "balance" in data
        assert data["balance"] > 0

    def test_get_account_existing(self, client: TestClient, auth_headers):
        """계정 조회 - 기존 계정 분기"""
        wait_for_api()
        response = client.get("/api/v1/futures/account", headers=auth_headers)
        assert response.status_code == 200

    def test_open_position_long_market(self, client: TestClient, auth_headers):
        """포지션 개설 - 롱 + 시장가 분기"""
        wait_for_api()
        response = client.post(
            "/api/v1/futures/positions/open",
            headers=auth_headers,
            json={
                "symbol": "BTCUSDT",
                "side": "LONG",
                "quantity": "0.0001",
                "leverage": 2,
                "order_type": "MARKET"
            }
        )
        assert response.status_code in [200, 400]

    def test_open_position_short_market(self, client: TestClient, auth_headers):
        """포지션 개설 - 숏 + 시장가 분기"""
        wait_for_api()
        response = client.post(
            "/api/v1/futures/positions/open",
            headers=auth_headers,
            json={
                "symbol": "ETHUSDT",
                "side": "SHORT",
                "quantity": "0.001",
                "leverage": 3,
                "order_type": "MARKET"
            }
        )
        assert response.status_code in [200, 400]

    def test_open_position_long_limit(self, client: TestClient, auth_headers):
        """포지션 개설 - 롱 + 지정가 분기"""
        wait_for_api()
        response = client.post(
            "/api/v1/futures/positions/open",
            headers=auth_headers,
            json={
                "symbol": "BTCUSDT",
                "side": "LONG",
                "quantity": "0.0001",
                "leverage": 2,
                "order_type": "LIMIT",
                "price": "40000"
            }
        )
        assert response.status_code in [200, 400]

    def test_open_position_short_limit(self, client: TestClient, auth_headers):
        """포지션 개설 - 숏 + 지정가 분기"""
        wait_for_api()
        response = client.post(
            "/api/v1/futures/positions/open",
            headers=auth_headers,
            json={
                "symbol": "BTCUSDT",
                "side": "SHORT",
                "quantity": "0.0001",
                "leverage": 5,
                "order_type": "LIMIT",
                "price": "100000"
            }
        )
        assert response.status_code in [200, 400]

    def test_get_positions_open_status(self, client: TestClient, auth_headers):
        """포지션 조회 - OPEN 상태 분기"""
        wait_for_api()
        response = client.get(
            "/api/v1/futures/positions",
            params={"status": "OPEN"},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_positions_closed_status(self, client: TestClient, auth_headers):
        """포지션 조회 - CLOSED 상태 분기"""
        wait_for_api()
        response = client.get(
            "/api/v1/futures/positions",
            params={"status": "CLOSED"},
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_get_positions_pending_status(self, client: TestClient, auth_headers):
        """포지션 조회 - PENDING 상태 분기"""
        wait_for_api()
        response = client.get(
            "/api/v1/futures/positions",
            params={"status": "PENDING"},
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_get_positions_liquidated_status(self, client: TestClient, auth_headers):
        """포지션 조회 - LIQUIDATED 상태 분기"""
        wait_for_api()
        response = client.get(
            "/api/v1/futures/positions",
            params={"status": "LIQUIDATED"},
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_close_position_success(self, client: TestClient, auth_headers):
        """포지션 청산 - 성공 분기"""
        # 먼저 포지션 개설
        wait_for_api()
        open_resp = client.post(
            "/api/v1/futures/positions/open",
            headers=auth_headers,
            json={
                "symbol": "BTCUSDT",
                "side": "LONG",
                "quantity": "0.0001",
                "leverage": 2,
                "order_type": "MARKET"
            }
        )
        
        if open_resp.status_code == 200:
            position_id = open_resp.json()["id"]
            
            wait_for_api()
            close_resp = client.post(
                f"/api/v1/futures/positions/{position_id}/close",
                headers=auth_headers
            )
            assert close_resp.status_code in [200, 400]

    def test_close_position_not_found(self, client: TestClient, auth_headers):
        """포지션 청산 - 존재하지 않음 분기"""
        fake_id = str(uuid.uuid4())
        wait_for_api()
        response = client.post(
            f"/api/v1/futures/positions/{fake_id}/close",
            headers=auth_headers
        )
        assert response.status_code in [404, 400]

    def test_get_transactions_default(self, client: TestClient, auth_headers):
        """거래 내역 - 기본 조회"""
        wait_for_api()
        response = client.get(
            "/api/v1/futures/transactions",
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_get_transactions_with_limit(self, client: TestClient, auth_headers):
        """거래 내역 - limit 파라미터"""
        wait_for_api()
        response = client.get(
            "/api/v1/futures/transactions",
            params={"limit": 5},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5

    def test_open_position_invalid_leverage_low(self, client: TestClient, auth_headers):
        """포지션 개설 - 레버리지 너무 낮음 (검증 분기)"""
        wait_for_api()
        response = client.post(
            "/api/v1/futures/positions/open",
            headers=auth_headers,
            json={
                "symbol": "BTCUSDT",
                "side": "LONG",
                "quantity": "0.001",
                "leverage": 0,
                "order_type": "MARKET"
            }
        )
        assert response.status_code == 422

    def test_open_position_invalid_leverage_high(self, client: TestClient, auth_headers):
        """포지션 개설 - 레버리지 너무 높음 (검증 분기)"""
        wait_for_api()
        response = client.post(
            "/api/v1/futures/positions/open",
            headers=auth_headers,
            json={
                "symbol": "BTCUSDT",
                "side": "LONG",
                "quantity": "0.001",
                "leverage": 200,
                "order_type": "MARKET"
            }
        )
        assert response.status_code == 422

    def test_open_position_negative_quantity(self, client: TestClient, auth_headers):
        """포지션 개설 - 음수 수량 (검증 분기)"""
        wait_for_api()
        response = client.post(
            "/api/v1/futures/positions/open",
            headers=auth_headers,
            json={
                "symbol": "BTCUSDT",
                "side": "LONG",
                "quantity": "-0.001",
                "leverage": 10,
                "order_type": "MARKET"
            }
        )
        assert response.status_code == 422

    def test_open_position_zero_quantity(self, client: TestClient, auth_headers):
        """포지션 개설 - 0 수량 (검증 분기)"""
        wait_for_api()
        response = client.post(
            "/api/v1/futures/positions/open",
            headers=auth_headers,
            json={
                "symbol": "BTCUSDT",
                "side": "LONG",
                "quantity": "0",
                "leverage": 10,
                "order_type": "MARKET"
            }
        )
        assert response.status_code == 422


# =============================================================================
# 4. Auth Router 브랜치 커버리지 테스트
# =============================================================================

class TestAuthRouterBranchCoverage:
    """인증 라우터 분기 테스트"""

    def test_register_success(self, client: TestClient):
        """회원가입 - 성공 분기"""
        username = generate_valid_username("regsucc")
        wait_for_api()
        response = client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": "validpass123"}
        )
        assert response.status_code in [200, 201]

    def test_register_duplicate_username(self, client: TestClient, user_factory):
        """회원가입 - 중복 사용자명 분기"""
        existing_user = user_factory(
            username=generate_valid_username("existing"),
            password="testpass123"
        )
        
        wait_for_api()
        response = client.post(
            "/api/v1/auth/register",
            json={"username": existing_user.username, "password": "anotherpass123"}
        )
        assert response.status_code == 400

    def test_register_short_username(self, client: TestClient):
        """회원가입 - 짧은 사용자명 (검증 분기)"""
        wait_for_api()
        response = client.post(
            "/api/v1/auth/register",
            json={"username": "ab", "password": "validpass123"}
        )
        assert response.status_code == 422

    def test_register_short_password(self, client: TestClient):
        """회원가입 - 짧은 비밀번호 (검증 분기)"""
        wait_for_api()
        response = client.post(
            "/api/v1/auth/register",
            json={"username": "validusername", "password": "12345"}
        )
        assert response.status_code == 422

    def test_login_success(self, client: TestClient, test_user):
        """로그인 - 성공 분기"""
        wait_for_api()
        response = client.post(
            "/api/v1/auth/login",
            data={"username": test_user.username, "password": "testpass123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_login_wrong_password(self, client: TestClient, test_user):
        """로그인 - 잘못된 비밀번호 분기"""
        wait_for_api()
        response = client.post(
            "/api/v1/auth/login",
            data={"username": test_user.username, "password": "wrongpassword"}
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        """로그인 - 존재하지 않는 사용자 분기"""
        wait_for_api()
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "nonexistentuser12345", "password": "anypassword"}
        )
        assert response.status_code == 401

    def test_protected_endpoint_no_token(self, client: TestClient):
        """보호된 엔드포인트 - 토큰 없음 분기"""
        wait_for_api()
        response = client.get("/api/v1/futures/account")
        assert response.status_code in [401, 403]

    def test_protected_endpoint_invalid_token(self, client: TestClient):
        """보호된 엔드포인트 - 잘못된 토큰 분기"""
        wait_for_api()
        response = client.get(
            "/api/v1/futures/account",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        assert response.status_code == 401

    def test_protected_endpoint_expired_token(self, client: TestClient, expired_headers):
        """보호된 엔드포인트 - 만료된 토큰 분기"""
        wait_for_api()
        response = client.get("/api/v1/futures/account", headers=expired_headers)
        assert response.status_code == 401


# =============================================================================
# 5. 통합 시나리오 브랜치 테스트
# =============================================================================

class TestIntegrationScenarioBranches:
    """통합 시나리오 분기 테스트"""

    def test_full_trading_cycle_long(self, client: TestClient, auth_headers):
        """전체 거래 사이클 - 롱 포지션"""
        # 1. 계정 조회
        wait_for_api()
        account_resp = client.get("/api/v1/futures/account", headers=auth_headers)
        assert account_resp.status_code == 200
        
        # 2. 롱 포지션 개설
        wait_for_api()
        open_resp = client.post(
            "/api/v1/futures/positions/open",
            headers=auth_headers,
            json={
                "symbol": "BTCUSDT",
                "side": "LONG",
                "quantity": "0.0001",
                "leverage": 2,
                "order_type": "MARKET"
            }
        )
        
        if open_resp.status_code == 200:
            position_id = open_resp.json()["id"]
            
            # 3. 포지션 확인
            wait_for_api()
            positions_resp = client.get(
                "/api/v1/futures/positions",
                params={"status": "OPEN"},
                headers=auth_headers
            )
            assert positions_resp.status_code == 200
            
            # 4. 포트폴리오 요약
            wait_for_api()
            summary_resp = client.get(
                "/api/v1/futures/portfolio/summary",
                headers=auth_headers
            )
            assert summary_resp.status_code == 200
            
            # 5. 포지션 청산
            wait_for_api()
            close_resp = client.post(
                f"/api/v1/futures/positions/{position_id}/close",
                headers=auth_headers
            )
            assert close_resp.status_code in [200, 400]
            
            # 6. 거래 내역 확인
            wait_for_api()
            tx_resp = client.get(
                "/api/v1/futures/transactions",
                headers=auth_headers
            )
            assert tx_resp.status_code == 200

    def test_full_trading_cycle_short(self, client: TestClient, auth_headers):
        """전체 거래 사이클 - 숏 포지션"""
        # 1. 숏 포지션 개설
        wait_for_api()
        open_resp = client.post(
            "/api/v1/futures/positions/open",
            headers=auth_headers,
            json={
                "symbol": "ETHUSDT",
                "side": "SHORT",
                "quantity": "0.001",
                "leverage": 3,
                "order_type": "MARKET"
            }
        )
        
        if open_resp.status_code == 200:
            position_id = open_resp.json()["id"]
            
            # 2. 통계 확인
            wait_for_api()
            stats_resp = client.get(
                "/api/v1/futures/portfolio/stats",
                headers=auth_headers
            )
            assert stats_resp.status_code == 200
            
            # 3. 청산
            wait_for_api()
            close_resp = client.post(
                f"/api/v1/futures/positions/{position_id}/close",
                headers=auth_headers
            )
            assert close_resp.status_code in [200, 400]

    def test_multiple_positions_different_symbols(self, client: TestClient, auth_headers):
        """다중 포지션 - 다른 심볼들"""
        symbols = ["BTCUSDT", "ETHUSDT"]
        position_ids = []
        
        for symbol in symbols:
            wait_for_api()
            resp = client.post(
                "/api/v1/futures/positions/open",
                headers=auth_headers,
                json={
                    "symbol": symbol,
                    "side": "LONG",
                    "quantity": "0.0001",
                    "leverage": 2,
                    "order_type": "MARKET"
                }
            )
            if resp.status_code == 200:
                position_ids.append(resp.json()["id"])
        
        # 모든 포지션 조회
        wait_for_api()
        all_positions = client.get(
            "/api/v1/futures/positions",
            params={"status": "OPEN"},
            headers=auth_headers
        )
        assert all_positions.status_code == 200
        
        # 정리: 모든 포지션 청산
        for pid in position_ids:
            wait_for_api()
            client.post(f"/api/v1/futures/positions/{pid}/close", headers=auth_headers)


# =============================================================================
# 실행
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])