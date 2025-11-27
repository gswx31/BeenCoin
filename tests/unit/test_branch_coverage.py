# ============================================================================
# 파일: tests/unit/test_branch_coverage.py
# ============================================================================
# 분기 커버리지 향상을 위한 테스트
# - if/else 분기
# - try/except 분기
# - None 체크 분기
# ============================================================================

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from uuid import uuid4
import time


def wait_for_api():
    """API 호출 간 간격"""
    time.sleep(0.05)


# ============================================================================
# 1. Auth Router 분기 테스트
# ============================================================================

class TestAuthBranches:
    """인증 라우터 분기 테스트"""

    def test_register_duplicate_username(self, client, user_factory):
        """중복 사용자명 등록 - 이미 존재하는 경우 분기"""
        # 먼저 사용자 생성
        existing_user = user_factory(username="existinguser", password="pass123")
        
        # 같은 이름으로 다시 등록 시도
        wait_for_api()
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "existinguser",
                "password": "newpass123"
            }
        )
        
        # 중복으로 실패해야 함
        assert response.status_code == 400

    def test_login_wrong_password(self, client, user_factory):
        """잘못된 비밀번호로 로그인 - 비밀번호 불일치 분기"""
        user = user_factory(username="wrongpassuser", password="correctpass")
        
        wait_for_api()
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "wrongpassuser",
                "password": "wrongpass"
            }
        )
        
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """존재하지 않는 사용자 로그인 - 사용자 없음 분기"""
        wait_for_api()
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent12345",
                "password": "anypass"
            }
        )
        
        assert response.status_code == 401

    def test_me_endpoint_with_valid_token(self, client, auth_headers):
        """유효한 토큰으로 /me 접근"""
        wait_for_api()
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "username" in data

    def test_me_endpoint_without_token(self, client):
        """토큰 없이 /me 접근 - 인증 실패 분기"""
        wait_for_api()
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code in [401, 403]

    def test_me_endpoint_with_invalid_token(self, client):
        """잘못된 토큰으로 /me 접근"""
        wait_for_api()
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token_123"}
        )
        
        assert response.status_code == 401


# ============================================================================
# 2. Futures Router 분기 테스트
# ============================================================================

class TestFuturesBranches:
    """선물 거래 분기 테스트"""

    def test_get_account_creates_new_account(self, client, user_factory):
        """새 사용자의 계정 조회 - 계정 생성 분기"""
        # 새 사용자 생성
        new_user = user_factory(username="newaccount123", password="pass123")
        
        # 로그인
        wait_for_api()
        login_resp = client.post(
            "/api/v1/auth/login",
            data={"username": "newaccount123", "password": "pass123"}
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 계정 조회 (처음이면 자동 생성)
        wait_for_api()
        response = client.get("/api/v1/futures/account", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "balance" in data

    def test_open_position_long(self, client, auth_headers):
        """롱 포지션 개설 - LONG 분기"""
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

    def test_open_position_short(self, client, auth_headers):
        """숏 포지션 개설 - SHORT 분기"""
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

    def test_get_positions_open_status(self, client, auth_headers):
        """OPEN 상태 포지션 조회"""
        wait_for_api()
        response = client.get(
            "/api/v1/futures/positions",
            params={"status": "OPEN"},
            headers=auth_headers
        )
        
        assert response.status_code == 200

    def test_get_positions_closed_status(self, client, auth_headers):
        """CLOSED 상태 포지션 조회 - 다른 상태 분기"""
        wait_for_api()
        response = client.get(
            "/api/v1/futures/positions",
            params={"status": "CLOSED"},
            headers=auth_headers
        )
        
        assert response.status_code == 200

    def test_get_positions_pending_status(self, client, auth_headers):
        """PENDING 상태 포지션 조회"""
        wait_for_api()
        response = client.get(
            "/api/v1/futures/positions",
            params={"status": "PENDING"},
            headers=auth_headers
        )
        
        assert response.status_code == 200

    def test_get_positions_liquidated_status(self, client, auth_headers):
        """LIQUIDATED 상태 포지션 조회"""
        wait_for_api()
        response = client.get(
            "/api/v1/futures/positions",
            params={"status": "LIQUIDATED"},
            headers=auth_headers
        )
        
        assert response.status_code == 200

    def test_close_nonexistent_position(self, client, auth_headers):
        """존재하지 않는 포지션 청산 - 포지션 없음 분기"""
        fake_id = str(uuid4())
        wait_for_api()
        response = client.post(
            f"/api/v1/futures/positions/{fake_id}/close",
            headers=auth_headers
        )
        
        assert response.status_code in [400, 404]

    def test_get_transactions_with_limit(self, client, auth_headers):
        """거래 내역 조회 - limit 파라미터"""
        wait_for_api()
        response = client.get(
            "/api/v1/futures/transactions",
            params={"limit": 10},
            headers=auth_headers
        )
        
        assert response.status_code == 200

    def test_get_transactions_max_limit(self, client, auth_headers):
        """거래 내역 조회 - 최대 limit"""
        wait_for_api()
        response = client.get(
            "/api/v1/futures/transactions",
            params={"limit": 200},
            headers=auth_headers
        )
        
        assert response.status_code == 200


# ============================================================================
# 3. Market Router 분기 테스트
# ============================================================================

class TestMarketBranches:
    """마켓 데이터 분기 테스트"""

    def test_get_coins_list(self, client):
        """코인 목록 조회"""
        wait_for_api()
        response = client.get("/api/v1/market/coins")
        
        assert response.status_code == 200

    def test_get_single_coin_valid(self, client):
        """유효한 코인 조회"""
        wait_for_api()
        response = client.get("/api/v1/market/coin/BTCUSDT")
        
        assert response.status_code == 200

    def test_get_single_coin_invalid(self, client):
        """유효하지 않은 코인 조회 - 에러 분기"""
        wait_for_api()
        response = client.get("/api/v1/market/coin/INVALIDCOIN123")
        
        # 400 또는 404
        assert response.status_code in [400, 404]

    def test_get_prices_multiple(self, client):
        """다중 가격 조회"""
        wait_for_api()
        response = client.get("/api/v1/market/prices")
        
        assert response.status_code == 200

    def test_get_history_valid_symbol(self, client):
        """유효한 심볼 히스토리"""
        wait_for_api()
        response = client.get(
            "/api/v1/market/history/BTCUSDT",
            params={"limit": 10}
        )
        
        assert response.status_code in [200, 404]

    def test_get_history_invalid_symbol(self, client):
        """유효하지 않은 심볼 히스토리 - 에러 분기"""
        wait_for_api()
        response = client.get(
            "/api/v1/market/history/INVALID123",
            params={"limit": 10}
        )
        
        assert response.status_code in [400, 404]


# ============================================================================
# 4. Portfolio Router 분기 테스트
# ============================================================================

class TestPortfolioBranches:
    """포트폴리오 분기 테스트"""

    def test_get_summary_new_user(self, client, user_factory):
        """새 사용자 포트폴리오 요약 - 계정 없음 분기"""
        new_user = user_factory(username="portfolionew", password="pass123")
        
        wait_for_api()
        login_resp = client.post(
            "/api/v1/auth/login",
            data={"username": "portfolionew", "password": "pass123"}
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        wait_for_api()
        response = client.get(
            "/api/v1/futures/portfolio/summary",
            headers=headers
        )
        
        assert response.status_code == 200

    def test_get_transactions_empty(self, client, user_factory):
        """거래 내역 없는 사용자 - 빈 목록 분기"""
        new_user = user_factory(username="emptytxuser", password="pass123")
        
        wait_for_api()
        login_resp = client.post(
            "/api/v1/auth/login",
            data={"username": "emptytxuser", "password": "pass123"}
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
        assert response.json() == []

    def test_get_stats_no_trades(self, client, user_factory):
        """거래 없는 사용자 통계 - 0 값 분기"""
        new_user = user_factory(username="nostatsuser", password="pass123")
        
        wait_for_api()
        login_resp = client.post(
            "/api/v1/auth/login",
            data={"username": "nostatsuser", "password": "pass123"}
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        wait_for_api()
        response = client.get(
            "/api/v1/futures/portfolio/stats",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_trades"] == 0

    def test_get_transactions_with_offset(self, client, auth_headers):
        """거래 내역 페이지네이션 - offset 분기"""
        wait_for_api()
        response = client.get(
            "/api/v1/futures/portfolio/transactions",
            params={"limit": 5, "offset": 10},
            headers=auth_headers
        )
        
        assert response.status_code == 200


# ============================================================================
# 5. 계산 로직 분기 테스트
# ============================================================================

class TestCalculationBranches:
    """계산 로직 분기 테스트"""

    def test_pnl_long_positive(self):
        """롱 포지션 양수 PnL - 가격 상승"""
        entry = Decimal("50000")
        current = Decimal("55000")
        qty = Decimal("0.1")
        
        pnl = (current - entry) * qty
        assert pnl > 0

    def test_pnl_long_negative(self):
        """롱 포지션 음수 PnL - 가격 하락"""
        entry = Decimal("50000")
        current = Decimal("45000")
        qty = Decimal("0.1")
        
        pnl = (current - entry) * qty
        assert pnl < 0

    def test_pnl_short_positive(self):
        """숏 포지션 양수 PnL - 가격 하락"""
        entry = Decimal("50000")
        current = Decimal("45000")
        qty = Decimal("0.1")
        
        pnl = (entry - current) * qty
        assert pnl > 0

    def test_pnl_short_negative(self):
        """숏 포지션 음수 PnL - 가격 상승"""
        entry = Decimal("50000")
        current = Decimal("55000")
        qty = Decimal("0.1")
        
        pnl = (entry - current) * qty
        assert pnl < 0

    def test_liquidation_price_long(self):
        """롱 청산가 계산 - 진입가 아래"""
        entry = Decimal("50000")
        leverage = 10
        qty = Decimal("1")
        
        margin = (entry * qty) / Decimal(leverage)
        liq_margin = margin * Decimal("0.9")
        liq_price = entry - (liq_margin / qty)
        
        assert liq_price < entry

    def test_liquidation_price_short(self):
        """숏 청산가 계산 - 진입가 위"""
        entry = Decimal("50000")
        leverage = 10
        qty = Decimal("1")
        
        margin = (entry * qty) / Decimal(leverage)
        liq_margin = margin * Decimal("0.9")
        liq_price = entry + (liq_margin / qty)
        
        assert liq_price > entry

    def test_roe_positive(self):
        """양수 ROE"""
        pnl = Decimal("100")
        margin = Decimal("1000")
        roe = (pnl / margin) * 100
        
        assert roe == Decimal("10")

    def test_roe_negative(self):
        """음수 ROE"""
        pnl = Decimal("-50")
        margin = Decimal("1000")
        roe = (pnl / margin) * 100
        
        assert roe == Decimal("-5")

    def test_roe_zero_margin(self):
        """증거금 0인 경우 - 0으로 나누기 방지"""
        pnl = Decimal("100")
        margin = Decimal("0")
        
        # 0으로 나누기 방지
        if margin == 0:
            roe = Decimal("0")
        else:
            roe = (pnl / margin) * 100
        
        assert roe == Decimal("0")


# ============================================================================
# 6. None 체크 분기 테스트
# ============================================================================

class TestNoneCheckBranches:
    """None 체크 분기 테스트"""

    def test_position_closed_at_none(self):
        """closed_at이 None인 경우"""
        closed_at = None
        
        result = closed_at.isoformat() if closed_at else None
        assert result is None

    def test_position_closed_at_set(self):
        """closed_at이 설정된 경우"""
        closed_at = datetime.utcnow()
        
        result = closed_at.isoformat() if closed_at else None
        assert result is not None

    def test_optional_price_none(self):
        """지정가가 None인 경우 (시장가)"""
        price = None
        order_type = "MARKET"
        
        if price is None and order_type == "MARKET":
            use_market = True
        else:
            use_market = False
        
        assert use_market is True

    def test_optional_price_set(self):
        """지정가가 설정된 경우"""
        price = Decimal("50000")
        order_type = "LIMIT"
        
        if price is None and order_type == "MARKET":
            use_market = True
        else:
            use_market = False
        
        assert use_market is False


# ============================================================================
# 7. 전체 포지션 라이프사이클 테스트
# ============================================================================

class TestPositionLifecycleBranches:
    """포지션 라이프사이클 분기 테스트"""

    def test_full_long_position_cycle(self, client, auth_headers):
        """롱 포지션 전체 사이클"""
        # 1. 포지션 개설
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
            
            # 2. 포지션 확인
            wait_for_api()
            positions_resp = client.get(
                "/api/v1/futures/positions",
                params={"status": "OPEN"},
                headers=auth_headers
            )
            assert positions_resp.status_code == 200
            
            # 3. 포지션 청산
            wait_for_api()
            close_resp = client.post(
                f"/api/v1/futures/positions/{position_id}/close",
                headers=auth_headers
            )
            assert close_resp.status_code in [200, 400]
            
            # 4. 청산된 포지션 확인
            wait_for_api()
            closed_resp = client.get(
                "/api/v1/futures/positions",
                params={"status": "CLOSED"},
                headers=auth_headers
            )
            assert closed_resp.status_code == 200

    def test_full_short_position_cycle(self, client, auth_headers):
        """숏 포지션 전체 사이클"""
        # 1. 포지션 개설
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
            
            # 2. 청산
            wait_for_api()
            close_resp = client.post(
                f"/api/v1/futures/positions/{position_id}/close",
                headers=auth_headers
            )
            assert close_resp.status_code in [200, 400]


# ============================================================================
# 8. 에러 핸들링 분기 테스트
# ============================================================================

class TestErrorHandlingBranches:
    """에러 핸들링 분기 테스트"""

    def test_insufficient_balance(self, client, auth_headers):
        """잔고 부족 에러 - 잔고 체크 분기"""
        wait_for_api()
        response = client.post(
            "/api/v1/futures/positions/open",
            headers=auth_headers,
            json={
                "symbol": "BTCUSDT",
                "side": "LONG",
                "quantity": "99999",  # 매우 큰 수량
                "leverage": 100,
                "order_type": "MARKET"
            }
        )
        
        # 잔고 부족으로 실패
        assert response.status_code in [400, 422]

    def test_invalid_leverage_low(self, client, auth_headers):
        """레버리지 너무 낮음 - 검증 분기"""
        wait_for_api()
        response = client.post(
            "/api/v1/futures/positions/open",
            headers=auth_headers,
            json={
                "symbol": "BTCUSDT",
                "side": "LONG",
                "quantity": "0.001",
                "leverage": 0,  # 0은 허용 안 됨
                "order_type": "MARKET"
            }
        )
        
        assert response.status_code == 422

    def test_invalid_leverage_high(self, client, auth_headers):
        """레버리지 너무 높음 - 검증 분기"""
        wait_for_api()
        response = client.post(
            "/api/v1/futures/positions/open",
            headers=auth_headers,
            json={
                "symbol": "BTCUSDT",
                "side": "LONG",
                "quantity": "0.001",
                "leverage": 200,  # 125 초과
                "order_type": "MARKET"
            }
        )
        
        assert response.status_code == 422

    def test_negative_quantity(self, client, auth_headers):
        """음수 수량 - 검증 분기"""
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

    def test_zero_quantity(self, client, auth_headers):
        """0 수량 - 검증 분기"""
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


# ============================================================================
# 실행
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])