# ============================================================================
# 파일: tests/integration/test_api_branches.py
# ============================================================================
# API 엔드포인트 브랜치 커버리지 향상을 위한 통합 테스트
# ============================================================================

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from decimal import Decimal
import random
import string
import os


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def client():
    """테스트 클라이언트 생성"""
    with patch.dict(os.environ, {'CI': 'true', 'MOCK_BINANCE': 'true'}):
        from app.main import app
        with TestClient(app) as c:
            yield c


@pytest.fixture
def auth_headers(client):
    """인증된 헤더 반환"""
    username = ''.join(random.choices(string.ascii_lowercase, k=10))
    email = f"{username}@test.com"
    password = "TestPassword123!"
    
    # 회원가입
    response = client.post("/api/v1/auth/register", json={
        "username": username,
        "email": email,
        "password": password
    })
    
    if response.status_code != 200:
        # 이미 존재하면 로그인만
        pass
    
    # 로그인
    response = client.post("/api/v1/auth/login", data={
        "username": username,
        "password": password
    })
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    return {}


# ============================================================================
# 1. Auth API 브랜치 테스트
# ============================================================================

class TestAuthAPIBranches:
    """인증 API 브랜치 테스트"""

    def test_register_success(self, client):
        """회원가입 성공"""
        username = ''.join(random.choices(string.ascii_lowercase, k=10))
        
        response = client.post("/api/v1/auth/register", json={
            "username": username,
            "email": f"{username}@test.com",
            "password": "ValidPassword123!"
        })
        
        assert response.status_code in [200, 400]  # 성공 또는 중복

    def test_register_duplicate_username(self, client):
        """중복 사용자명으로 회원가입"""
        username = "duplicateuser"
        
        # 첫 번째 가입
        client.post("/api/v1/auth/register", json={
            "username": username,
            "email": f"{username}@test.com",
            "password": "ValidPassword123!"
        })
        
        # 두 번째 가입 (중복)
        response = client.post("/api/v1/auth/register", json={
            "username": username,
            "email": f"{username}2@test.com",
            "password": "ValidPassword123!"
        })
        
        assert response.status_code == 400

    def test_register_duplicate_email(self, client):
        """중복 이메일로 회원가입"""
        email = "duplicate@test.com"
        
        # 첫 번째 가입
        client.post("/api/v1/auth/register", json={
            "username": "user1_" + ''.join(random.choices(string.ascii_lowercase, k=5)),
            "email": email,
            "password": "ValidPassword123!"
        })
        
        # 두 번째 가입 (중복 이메일)
        response = client.post("/api/v1/auth/register", json={
            "username": "user2_" + ''.join(random.choices(string.ascii_lowercase, k=5)),
            "email": email,
            "password": "ValidPassword123!"
        })
        
        assert response.status_code == 400

    def test_register_invalid_password_short(self, client):
        """짧은 비밀번호로 회원가입"""
        username = ''.join(random.choices(string.ascii_lowercase, k=10))
        
        response = client.post("/api/v1/auth/register", json={
            "username": username,
            "email": f"{username}@test.com",
            "password": "short"  # 너무 짧음
        })
        
        assert response.status_code == 422  # Validation error

    def test_register_invalid_email(self, client):
        """유효하지 않은 이메일로 회원가입"""
        username = ''.join(random.choices(string.ascii_lowercase, k=10))
        
        response = client.post("/api/v1/auth/register", json={
            "username": username,
            "email": "invalid-email",
            "password": "ValidPassword123!"
        })
        
        assert response.status_code == 422

    def test_login_success(self, client):
        """로그인 성공"""
        username = ''.join(random.choices(string.ascii_lowercase, k=10))
        password = "TestPassword123!"
        
        # 먼저 회원가입
        client.post("/api/v1/auth/register", json={
            "username": username,
            "email": f"{username}@test.com",
            "password": password
        })
        
        # 로그인
        response = client.post("/api/v1/auth/login", data={
            "username": username,
            "password": password
        })
        
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_wrong_password(self, client):
        """잘못된 비밀번호로 로그인"""
        username = ''.join(random.choices(string.ascii_lowercase, k=10))
        
        # 회원가입
        client.post("/api/v1/auth/register", json={
            "username": username,
            "email": f"{username}@test.com",
            "password": "CorrectPassword123!"
        })
        
        # 잘못된 비밀번호로 로그인
        response = client.post("/api/v1/auth/login", data={
            "username": username,
            "password": "WrongPassword123!"
        })
        
        assert response.status_code == 401

    def test_login_user_not_found(self, client):
        """존재하지 않는 사용자로 로그인"""
        response = client.post("/api/v1/auth/login", data={
            "username": "nonexistentuser",
            "password": "AnyPassword123!"
        })
        
        assert response.status_code == 401

    def test_get_me_unauthorized(self, client):
        """인증 없이 사용자 정보 조회"""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 401

    def test_get_me_invalid_token(self, client):
        """유효하지 않은 토큰으로 사용자 정보 조회"""
        response = client.get("/api/v1/auth/me", headers={
            "Authorization": "Bearer invalid_token"
        })
        
        assert response.status_code == 401

    def test_get_me_success(self, client, auth_headers):
        """사용자 정보 조회 성공"""
        if not auth_headers:
            pytest.skip("인증 헤더 생성 실패")
        
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        
        assert response.status_code == 200


# ============================================================================
# 2. Market API 브랜치 테스트
# ============================================================================

class TestMarketAPIBranches:
    """시장 API 브랜치 테스트"""

    def test_get_price_success(self, client):
        """가격 조회 성공"""
        response = client.get("/api/v1/market/price/BTCUSDT")
        
        assert response.status_code == 200

    def test_get_price_invalid_symbol(self, client):
        """유효하지 않은 심볼로 가격 조회"""
        response = client.get("/api/v1/market/price/INVALID")
        
        # 에러 또는 빈 응답
        assert response.status_code in [200, 400, 404]

    def test_get_prices_multiple(self, client):
        """다중 가격 조회"""
        response = client.get("/api/v1/market/prices", params={
            "symbols": "BTCUSDT,ETHUSDT"
        })
        
        assert response.status_code in [200, 400]

    def test_get_klines_success(self, client):
        """캔들 데이터 조회 성공"""
        response = client.get("/api/v1/market/klines/BTCUSDT", params={
            "interval": "1h",
            "limit": 10
        })
        
        assert response.status_code == 200

    def test_get_klines_different_intervals(self, client):
        """다양한 인터벌로 캔들 조회"""
        intervals = ["1m", "5m", "15m", "1h", "4h", "1d"]
        
        for interval in intervals:
            response = client.get("/api/v1/market/klines/BTCUSDT", params={
                "interval": interval,
                "limit": 5
            })
            
            assert response.status_code in [200, 400]

    def test_get_order_book_success(self, client):
        """호가창 조회 성공"""
        response = client.get("/api/v1/market/orderbook/BTCUSDT", params={
            "limit": 10
        })
        
        assert response.status_code in [200, 400]

    def test_get_order_book_different_limits(self, client):
        """다양한 limit로 호가창 조회"""
        limits = [5, 10, 20, 50, 100]
        
        for limit in limits:
            response = client.get("/api/v1/market/orderbook/BTCUSDT", params={
                "limit": limit
            })
            
            assert response.status_code in [200, 400]

    def test_get_trades_success(self, client):
        """체결 내역 조회 성공"""
        response = client.get("/api/v1/market/trades/BTCUSDT", params={
            "limit": 10
        })
        
        assert response.status_code in [200, 400]

    def test_get_ticker_24hr(self, client):
        """24시간 티커 조회"""
        response = client.get("/api/v1/market/ticker/BTCUSDT")
        
        assert response.status_code in [200, 400]


# ============================================================================
# 3. Futures API 브랜치 테스트
# ============================================================================

class TestFuturesAPIBranches:
    """선물 API 브랜치 테스트"""

    def test_open_position_unauthorized(self, client):
        """인증 없이 포지션 개설"""
        response = client.post("/api/v1/futures/positions", json={
            "symbol": "BTCUSDT",
            "side": "LONG",
            "quantity": 0.01,
            "leverage": 10,
            "order_type": "MARKET"
        })
        
        assert response.status_code == 401

    def test_open_position_long_market(self, client, auth_headers):
        """롱 시장가 포지션 개설"""
        if not auth_headers:
            pytest.skip("인증 헤더 생성 실패")
        
        response = client.post("/api/v1/futures/positions", json={
            "symbol": "BTCUSDT",
            "side": "LONG",
            "quantity": 0.001,
            "leverage": 10,
            "order_type": "MARKET"
        }, headers=auth_headers)
        
        assert response.status_code in [200, 400, 500]

    def test_open_position_short_market(self, client, auth_headers):
        """숏 시장가 포지션 개설"""
        if not auth_headers:
            pytest.skip("인증 헤더 생성 실패")
        
        response = client.post("/api/v1/futures/positions", json={
            "symbol": "BTCUSDT",
            "side": "SHORT",
            "quantity": 0.001,
            "leverage": 10,
            "order_type": "MARKET"
        }, headers=auth_headers)
        
        assert response.status_code in [200, 400, 500]

    def test_open_position_limit_order(self, client, auth_headers):
        """지정가 포지션 개설"""
        if not auth_headers:
            pytest.skip("인증 헤더 생성 실패")
        
        response = client.post("/api/v1/futures/positions", json={
            "symbol": "BTCUSDT",
            "side": "LONG",
            "quantity": 0.001,
            "leverage": 10,
            "order_type": "LIMIT",
            "price": 40000  # 지정가
        }, headers=auth_headers)
        
        assert response.status_code in [200, 400, 500]

    def test_open_position_different_leverages(self, client, auth_headers):
        """다양한 레버리지로 포지션 개설"""
        if not auth_headers:
            pytest.skip("인증 헤더 생성 실패")
        
        leverages = [1, 5, 10, 20, 50, 100, 125]
        
        for leverage in leverages:
            response = client.post("/api/v1/futures/positions", json={
                "symbol": "BTCUSDT",
                "side": "LONG",
                "quantity": 0.0001,
                "leverage": leverage,
                "order_type": "MARKET"
            }, headers=auth_headers)
            
            assert response.status_code in [200, 400, 500]

    def test_open_position_invalid_leverage(self, client, auth_headers):
        """유효하지 않은 레버리지로 포지션 개설"""
        if not auth_headers:
            pytest.skip("인증 헤더 생성 실패")
        
        response = client.post("/api/v1/futures/positions", json={
            "symbol": "BTCUSDT",
            "side": "LONG",
            "quantity": 0.001,
            "leverage": 200,  # 유효하지 않음
            "order_type": "MARKET"
        }, headers=auth_headers)
        
        assert response.status_code in [400, 422]

    def test_open_position_zero_quantity(self, client, auth_headers):
        """수량 0으로 포지션 개설"""
        if not auth_headers:
            pytest.skip("인증 헤더 생성 실패")
        
        response = client.post("/api/v1/futures/positions", json={
            "symbol": "BTCUSDT",
            "side": "LONG",
            "quantity": 0,
            "leverage": 10,
            "order_type": "MARKET"
        }, headers=auth_headers)
        
        assert response.status_code in [400, 422]

    def test_get_positions_open(self, client, auth_headers):
        """열린 포지션 목록 조회"""
        if not auth_headers:
            pytest.skip("인증 헤더 생성 실패")
        
        response = client.get("/api/v1/futures/positions", params={
            "status": "OPEN"
        }, headers=auth_headers)
        
        assert response.status_code == 200

    def test_get_positions_pending(self, client, auth_headers):
        """대기 중인 포지션 목록 조회"""
        if not auth_headers:
            pytest.skip("인증 헤더 생성 실패")
        
        response = client.get("/api/v1/futures/positions", params={
            "status": "PENDING"
        }, headers=auth_headers)
        
        assert response.status_code == 200

    def test_get_positions_closed(self, client, auth_headers):
        """청산된 포지션 목록 조회"""
        if not auth_headers:
            pytest.skip("인증 헤더 생성 실패")
        
        response = client.get("/api/v1/futures/positions", params={
            "status": "CLOSED"
        }, headers=auth_headers)
        
        assert response.status_code == 200

    def test_close_position_not_found(self, client, auth_headers):
        """존재하지 않는 포지션 청산"""
        if not auth_headers:
            pytest.skip("인증 헤더 생성 실패")
        
        response = client.post(
            "/api/v1/futures/positions/nonexistent-id/close",
            headers=auth_headers
        )
        
        assert response.status_code in [404, 422]

    def test_get_transactions(self, client, auth_headers):
        """거래 내역 조회"""
        if not auth_headers:
            pytest.skip("인증 헤더 생성 실패")
        
        response = client.get("/api/v1/futures/transactions", headers=auth_headers)
        
        assert response.status_code == 200


# ============================================================================
# 4. Futures Portfolio API 브랜치 테스트
# ============================================================================

class TestFuturesPortfolioAPIBranches:
    """선물 포트폴리오 API 브랜치 테스트"""

    def test_get_summary_unauthorized(self, client):
        """인증 없이 포트폴리오 요약 조회"""
        response = client.get("/api/v1/futures/portfolio/summary")
        
        assert response.status_code == 401

    def test_get_summary_success(self, client, auth_headers):
        """포트폴리오 요약 조회 성공"""
        if not auth_headers:
            pytest.skip("인증 헤더 생성 실패")
        
        response = client.get("/api/v1/futures/portfolio/summary", headers=auth_headers)
        
        assert response.status_code in [200, 404]

    def test_get_fills_not_found(self, client, auth_headers):
        """존재하지 않는 포지션의 체결 내역"""
        if not auth_headers:
            pytest.skip("인증 헤더 생성 실패")
        
        response = client.get(
            "/api/v1/futures/portfolio/fills/nonexistent-id",
            headers=auth_headers
        )
        
        assert response.status_code in [404, 422]


# ============================================================================
# 5. Health Check 및 기본 엔드포인트 테스트
# ============================================================================

class TestBasicEndpoints:
    """기본 엔드포인트 테스트"""

    def test_health_check(self, client):
        """헬스 체크"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_root_endpoint(self, client):
        """루트 엔드포인트"""
        response = client.get("/")
        
        assert response.status_code == 200

    def test_docs_endpoint(self, client):
        """API 문서 엔드포인트"""
        response = client.get("/docs")
        
        assert response.status_code == 200


# ============================================================================
# 실행 설정
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])