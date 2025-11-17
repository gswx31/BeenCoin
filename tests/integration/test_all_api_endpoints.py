# ============================================================================
# 파일 위치: tests/integration/test_all_api_endpoints.py
# ============================================================================
# 설명: 모든 API 엔드포인트를 테스트하는 통합 테스트
# 생성 방법:
#   1. 프로젝트 루트에서: mkdir -p tests/integration
#   2. 이 내용을 tests/integration/test_all_api_endpoints.py 에 저장
# ============================================================================

"""
API 통합 테스트 - 모든 엔드포인트 검증
=====================================

테스트 항목:
1. 기본 엔드포인트 (Health, Root, Docs)
2. 인증 API (회원가입, 로그인)
3. 마켓 데이터 API (코인, 가격, 차트)
4. 선물 거래 API (계정, 포지션, 청산)
5. 포트폴리오 API (요약, 통계, 거래내역)
6. 에러 케이스
7. E2E 시나리오
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from datetime import datetime

from app.main import app
from app.models.database import User


@pytest.mark.integration
@pytest.mark.api
class TestAllAPIEndpoints:
    """모든 API 엔드포인트 통합 테스트"""
    
    # =================================================================
    # 1. 기본 엔드포인트
    # =================================================================
    
    def test_health_check(self, client: TestClient):
        """헬스 체크"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_root_endpoint(self, client: TestClient):
        """루트 엔드포인트"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
    
    def test_api_docs(self, client: TestClient):
        """API 문서 접근"""
        # Swagger UI
        response = client.get("/docs")
        assert response.status_code == 200
        
        # ReDoc
        response = client.get("/redoc")
        assert response.status_code == 200
    
    # =================================================================
    # 2. 인증 API
    # =================================================================
    
    def test_user_registration_success(self, client: TestClient):
        """회원가입 성공"""
        username = f"testuser_{datetime.now().timestamp()}"
        response = client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": "testpass123"}
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["username"] == username
    
    def test_user_registration_duplicate_fails(
        self, 
        client: TestClient,
        test_user: User
    ):
        """중복 사용자명 회원가입 실패"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": test_user.username,
                "password": "testpass123"
            }
        )
        assert response.status_code == 400
    
    def test_user_login_success(
        self,
        client: TestClient,
        test_user: User
    ):
        """로그인 성공"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user.username,
                "password": test_user._test_password
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    
    def test_user_login_wrong_password_fails(
        self,
        client: TestClient,
        test_user: User
    ):
        """잘못된 비밀번호 로그인 실패"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user.username,
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401
    
    def test_access_protected_without_auth_fails(
        self,
        client: TestClient
    ):
        """인증 없이 보호된 엔드포인트 접근 실패"""
        response = client.get("/api/v1/futures/account")
        assert response.status_code in [401, 403]
    
    def test_access_with_invalid_token_fails(
        self,
        client: TestClient
    ):
        """잘못된 토큰으로 접근 실패"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/futures/account", headers=headers)
        assert response.status_code == 401
    
    # =================================================================
    # 3. 마켓 데이터 API
    # =================================================================
    
    def test_get_all_coins(self, client: TestClient):
        """모든 코인 정보 조회"""
        response = client.get("/api/v1/market/coins")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
    
    def test_get_btc_info(self, client: TestClient):
        """비트코인 정보 조회"""
        response = client.get("/api/v1/market/coin/BTCUSDT")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BTCUSDT"
        assert "price" in data
    
    def test_get_eth_info(self, client: TestClient):
        """이더리움 정보 조회"""
        response = client.get("/api/v1/market/coin/ETHUSDT")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "ETHUSDT"
    
    def test_get_invalid_coin_fails(self, client: TestClient):
        """존재하지 않는 코인 조회 실패"""
        response = client.get("/api/v1/market/coin/INVALIDCOIN")
        assert response.status_code in [400, 404]
    
    def test_get_historical_data(self, client: TestClient):
        """과거 차트 데이터 조회"""
        response = client.get(
            "/api/v1/market/historical/BTCUSDT",
            params={"interval": "1h", "limit": 24}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_all_prices(self, client: TestClient):
        """모든 코인 가격 조회"""
        response = client.get("/api/v1/market/prices")
        assert response.status_code == 200
        data = response.json()
        assert "BTCUSDT" in data
    
    def test_get_recent_trades(self, client: TestClient):
        """최근 체결 내역 조회"""
        response = client.get(
            "/api/v1/market/trades/BTCUSDT",
            params={"limit": 20}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    # =================================================================
    # 4. 선물 거래 API (인증 필요)
    # =================================================================
    
    def test_get_futures_account(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """선물 계정 조회"""
        response = client.get(
            "/api/v1/futures/account",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "balance" in data
        assert "margin_used" in data
    
    def test_open_long_position(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """롱 포지션 개설"""
        response = client.post(
            "/api/v1/futures/positions/open",
            headers=auth_headers,
            json={
                "symbol": "BTCUSDT",
                "side": "LONG",
                "quantity": "0.001",
                "leverage": 10,
                "order_type": "MARKET"
            }
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["symbol"] == "BTCUSDT"
        assert data["side"] == "LONG"
    
    def test_open_short_position(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """숏 포지션 개설"""
        response = client.post(
            "/api/v1/futures/positions/open",
            headers=auth_headers,
            json={
                "symbol": "ETHUSDT",
                "side": "SHORT",
                "quantity": "0.01",
                "leverage": 5,
                "order_type": "MARKET"
            }
        )
        assert response.status_code in [200, 201]
    
    def test_get_open_positions(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """오픈 포지션 목록 조회"""
        response = client.get(
            "/api/v1/futures/positions",
            params={"status": "OPEN"},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_closed_positions(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """청산된 포지션 목록 조회"""
        response = client.get(
            "/api/v1/futures/positions",
            params={"status": "CLOSED"},
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_get_futures_transactions(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """선물 거래 내역 조회"""
        response = client.get(
            "/api/v1/futures/transactions",
            params={"limit": 10},
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_close_position(
        self,
        client: TestClient,
        auth_headers: dict,
        db_session: Session
    ):
        """포지션 청산"""
        # 포지션 개설
        open_response = client.post(
            "/api/v1/futures/positions/open",
            headers=auth_headers,
            json={
                "symbol": "BTCUSDT",
                "side": "LONG",
                "quantity": "0.001",
                "leverage": 10,
                "order_type": "MARKET"
            }
        )
        assert open_response.status_code in [200, 201]
        position_id = open_response.json()["id"]
        
        # 포지션 청산
        close_response = client.post(
            f"/api/v1/futures/positions/{position_id}/close",
            headers=auth_headers
        )
        assert close_response.status_code == 200
    
    def test_open_position_invalid_symbol_fails(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """잘못된 심볼로 포지션 개설 실패"""
        response = client.post(
            "/api/v1/futures/positions/open",
            headers=auth_headers,
            json={
                "symbol": "INVALID",
                "side": "LONG",
                "quantity": "0.001",
                "leverage": 10,
                "order_type": "MARKET"
            }
        )
        assert response.status_code in [400, 422]
    
    def test_open_position_invalid_leverage_fails(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """잘못된 레버리지로 포지션 개설 실패"""
        response = client.post(
            "/api/v1/futures/positions/open",
            headers=auth_headers,
            json={
                "symbol": "BTCUSDT",
                "side": "LONG",
                "quantity": "0.001",
                "leverage": 200,  # 최대 125배 초과
                "order_type": "MARKET"
            }
        )
        assert response.status_code == 422
    
    # =================================================================
    # 5. 포트폴리오 API
    # =================================================================
    
    def test_get_portfolio_summary(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """포트폴리오 요약 조회"""
        response = client.get(
            "/api/v1/futures/portfolio/summary",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_balance" in data
        assert "open_positions_count" in data
    
    def test_get_portfolio_positions(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """포트폴리오 포지션 상세 조회"""
        response = client.get(
            "/api/v1/futures/portfolio/positions",
            params={"status": "OPEN"},
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_get_portfolio_transactions(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """포트폴리오 거래 내역 조회"""
        response = client.get(
            "/api/v1/futures/portfolio/transactions",
            params={"limit": 20},
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_get_portfolio_stats(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """거래 통계 조회"""
        response = client.get(
            "/api/v1/futures/portfolio/stats",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_trades" in data
        assert "win_rate" in data
    
    # =================================================================
    # 6. E2E 시나리오 테스트
    # =================================================================
    
    def test_complete_trading_flow(
        self,
        client: TestClient,
        db_session: Session
    ):
        """
        완전한 거래 플로우
        1. 회원가입
        2. 로그인
        3. 계정 조회
        4. 포지션 개설
        5. 포지션 조회
        6. 포지션 청산
        7. 거래 내역 확인
        """
        # 1. 회원가입
        username = f"e2euser_{datetime.now().timestamp()}"
        register_response = client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": "testpass123"}
        )
        assert register_response.status_code in [200, 201]
        
        # 2. 로그인
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": "testpass123"}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 3. 계정 조회
        account_response = client.get(
            "/api/v1/futures/account",
            headers=headers
        )
        assert account_response.status_code == 200
        
        # 4. 포지션 개설
        position_response = client.post(
            "/api/v1/futures/positions/open",
            headers=headers,
            json={
                "symbol": "BTCUSDT",
                "side": "LONG",
                "quantity": "0.001",
                "leverage": 10,
                "order_type": "MARKET"
            }
        )
        assert position_response.status_code in [200, 201]
        position_id = position_response.json()["id"]
        
        # 5. 포지션 조회
        positions_response = client.get(
            "/api/v1/futures/positions",
            params={"status": "OPEN"},
            headers=headers
        )
        assert positions_response.status_code == 200
        assert len(positions_response.json()) > 0
        
        # 6. 포지션 청산
        close_response = client.post(
            f"/api/v1/futures/positions/{position_id}/close",
            headers=headers
        )
        assert close_response.status_code == 200
        
        # 7. 거래 내역 확인
        transactions_response = client.get(
            "/api/v1/futures/transactions",
            headers=headers
        )
        assert transactions_response.status_code == 200
        transactions = transactions_response.json()
        assert len(transactions) >= 2  # OPEN + CLOSE


# =================================================================
# Pytest Fixture
# =================================================================

@pytest.fixture
def auth_headers(client: TestClient, test_user: User) -> dict:
    """인증 헤더 생성"""
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "username": test_user.username,
            "password": test_user._test_password
        }
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}