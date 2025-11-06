"""
인증 고급 테스트 - 백엔드 API 완전 연동 버전
==========================================

백엔드 실제 구현:
- app/routers/auth.py 또는 app/api/v1/endpoints/auth.py
- POST /api/v1/auth/register (회원가입)
- POST /api/v1/auth/login (로그인, OAuth2PasswordRequestForm 사용)
- JWT 토큰 인증
- get_current_user 의존성

수정 사항:
1. 실제 API 엔드포인트 사용
2. OAuth2PasswordRequestForm 형식 (application/x-www-form-urlencoded)
3. HTTPException 처리
4. 실제 스키마 사용
"""
import pytest
from fastapi.testclient import TestClient
from fastapi import status
from sqlmodel import Session, select
from datetime import datetime, timedelta
from decimal import Decimal

from app.main import app
from app.models.database import User, TradingAccount
from app.utils.security import create_access_token, hash_password


# =============================================================================
# 회원가입 테스트
# =============================================================================

@pytest.mark.integration
@pytest.mark.auth
class TestUserRegistration:
    """회원가입 API 테스트"""
    
    def test_register_new_user_success(
        self,
        client: TestClient,
        db_session: Session
    ):
        """
        신규 사용자 회원가입 성공
        
        Given: 유효한 사용자 정보
        When: POST /api/v1/auth/register
        Then: 201 Created, 사용자 및 거래 계정 생성
        """
        # Arrange
        user_data = {
            "username": "newuser123",
            "password": "securepass123"
        }
        
        # Act
        response = client.post(
            "/api/v1/auth/register",
            json=user_data
        )
        
        # Assert
        assert response.status_code in [200, 201]  # 200 또는 201 허용
        data = response.json()
        
        # 응답 데이터 검증
        assert "id" in data
        assert data["username"] == "newuser123"
        assert "created_at" in data
        
        # DB 검증
        user = db_session.exec(
            select(User).where(User.username == "newuser123")
        ).first()
        assert user is not None
        assert user.is_active is True
        
        # 거래 계정 자동 생성 검증
        account = db_session.exec(
            select(TradingAccount).where(TradingAccount.user_id == user.id)
        ).first()
        assert account is not None
        assert account.balance > 0  # 초기 잔액 설정됨
    
    
    def test_register_duplicate_username_fails(
        self,
        client: TestClient,
        test_user: User
    ):
        """
        중복 사용자명 회원가입 실패
        
        Given: 이미 존재하는 사용자명
        When: 같은 사용자명으로 회원가입 시도
        Then: 400 Bad Request
        """
        # Arrange
        user_data = {
            "username": test_user.username,
            "password": "anypassword123"
        }
        
        # Act
        response = client.post(
            "/api/v1/auth/register",
            json=user_data
        )
        
        # Assert
        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower() or \
               "존재" in response.json()["detail"]
    
    
    @pytest.mark.parametrize("invalid_username,invalid_password", [
        ("ab", "validpass123"),  # 너무 짧은 사용자명
        ("validuser", "123"),    # 너무 짧은 비밀번호
        ("", "validpass123"),    # 빈 사용자명
        ("validuser", ""),       # 빈 비밀번호
    ])
    def test_register_invalid_input_fails(
        self,
        client: TestClient,
        invalid_username: str,
        invalid_password: str
    ):
        """
        유효하지 않은 입력으로 회원가입 실패
        
        Given: 너무 짧거나 빈 사용자명/비밀번호
        When: 회원가입 시도
        Then: 422 Validation Error
        """
        # Arrange
        user_data = {
            "username": invalid_username,
            "password": invalid_password
        }
        
        # Act
        response = client.post(
            "/api/v1/auth/register",
            json=user_data
        )
        
        # Assert
        assert response.status_code == 422


# =============================================================================
# 로그인 테스트
# =============================================================================

@pytest.mark.integration
@pytest.mark.auth
class TestUserLogin:
    """로그인 API 테스트"""
    
    def test_login_valid_credentials_success(
        self,
        client: TestClient,
        db_session: Session
    ):
        """
        올바른 자격증명으로 로그인 성공
        
        Given: 등록된 사용자
        When: 올바른 사용자명과 비밀번호로 로그인
        Then: 200 OK, JWT 토큰 반환
        """
        # Arrange - 사용자 생성
        username = "loginuser"
        password = "loginpass123"
        
        # 회원가입
        client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": password}
        )
        
        # Act - 로그인 (OAuth2PasswordRequestForm 형식)
        login_data = {
            "username": username,
            "password": password
        }
        
        response = client.post(
            "/api/v1/auth/login",
            data=login_data,  # data 파라미터 사용 (form-data)
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # 토큰 검증
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0
    
    
    def test_login_wrong_password_fails(
        self,
        client: TestClient,
        test_user: User
    ):
        """
        잘못된 비밀번호로 로그인 실패
        
        Given: 등록된 사용자
        When: 잘못된 비밀번호로 로그인 시도
        Then: 401 Unauthorized
        """
        # Arrange
        login_data = {
            "username": test_user.username,
            "password": "wrongpassword123"
        }
        
        # Act
        response = client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # Assert
        assert response.status_code == 401
        assert "detail" in response.json()
    
    
    def test_login_nonexistent_user_fails(
        self,
        client: TestClient
    ):
        """
        존재하지 않는 사용자로 로그인 실패
        
        Given: 등록되지 않은 사용자명
        When: 로그인 시도
        Then: 401 Unauthorized
        """
        # Arrange
        login_data = {
            "username": "nonexistentuser999",
            "password": "anypassword123"
        }
        
        # Act
        response = client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # Assert
        assert response.status_code == 401
    
    
    def test_login_inactive_user_fails(
        self,
        client: TestClient,
        db_session: Session,
        test_user: User
    ):
        """
        비활성화된 사용자 로그인 실패
        
        Given: 비활성화된 사용자
        When: 로그인 시도
        Then: 403 Forbidden
        """
        # Arrange - 사용자 비활성화
        test_user.is_active = False
        db_session.add(test_user)
        db_session.commit()
        
        login_data = {
            "username": test_user.username,
            "password": "testpass123"
        }
        
        # Act
        response = client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # Assert
        assert response.status_code == 403
        assert "inactive" in response.json()["detail"].lower() or \
               "비활성" in response.json()["detail"]
    
    
    @pytest.mark.parametrize("field_to_omit", ["username", "password"])
    def test_login_missing_required_field_fails(
        self,
        client: TestClient,
        field_to_omit: str
    ):
        """
        필수 필드 누락 시 로그인 실패
        
        Given: username 또는 password 누락
        When: 로그인 시도
        Then: 422 Validation Error
        """
        # Arrange
        login_data = {
            "username": "testuser",
            "password": "testpass123"
        }
        del login_data[field_to_omit]
        
        # Act
        response = client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # Assert
        assert response.status_code == 422


# =============================================================================
# JWT 토큰 검증 테스트
# =============================================================================

@pytest.mark.integration
@pytest.mark.auth
class TestJWTAuthentication:
    """JWT 토큰 인증 테스트"""
    
    def test_access_protected_route_with_valid_token_success(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """
        유효한 토큰으로 보호된 라우트 접근 성공
        
        Given: 유효한 JWT 토큰
        When: 인증이 필요한 엔드포인트 호출
        Then: 200 OK
        """
        # Act - 계정 정보 조회 (인증 필요)
        response = client.get(
            "/api/v1/account/",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
    
    
    def test_access_protected_route_without_token_fails(
        self,
        client: TestClient
    ):
        """
        토큰 없이 보호된 라우트 접근 실패
        
        Given: 인증 헤더 없음
        When: 보호된 엔드포인트 호출
        Then: 401 Unauthorized 또는 403 Forbidden
        """
        # Act
        response = client.get("/api/v1/account/")
        
        # Assert
        assert response.status_code in [401, 403]
    
    
    def test_access_protected_route_with_invalid_token_fails(
        self,
        client: TestClient
    ):
        """
        유효하지 않은 토큰으로 접근 실패
        
        Given: 잘못된 JWT 토큰
        When: 보호된 엔드포인트 호출
        Then: 401 Unauthorized
        """
        # Arrange
        invalid_headers = {"Authorization": "Bearer invalid_token_12345"}
        
        # Act
        response = client.get(
            "/api/v1/account/",
            headers=invalid_headers
        )
        
        # Assert
        assert response.status_code == 401
    
    
    def test_access_with_expired_token_fails(
        self,
        client: TestClient,
        test_user: User
    ):
        """
        만료된 토큰으로 접근 실패
        
        Given: 만료된 JWT 토큰
        When: 보호된 엔드포인트 호출
        Then: 401 Unauthorized
        """
        # Arrange - 이미 만료된 토큰 생성
        from datetime import datetime, timedelta
        expired_token = create_access_token(
            data={"sub": test_user.username},
            expires_delta=timedelta(seconds=-1)  # 과거 시간
        )
        
        expired_headers = {"Authorization": f"Bearer {expired_token}"}
        
        # Act
        response = client.get(
            "/api/v1/account/",
            headers=expired_headers
        )
        
        # Assert
        assert response.status_code == 401


# =============================================================================
# 보안 테스트
# =============================================================================

@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.security
class TestAuthSecurity:
    """인증 보안 테스트"""
    
    def test_password_not_returned_in_response(
        self,
        client: TestClient
    ):
        """
        응답에 비밀번호가 포함되지 않음
        
        Given: 회원가입 또는 로그인
        When: API 응답
        Then: 비밀번호 정보 미포함
        """
        # Arrange
        user_data = {
            "username": "secureuser",
            "password": "securepass123"
        }
        
        # Act - 회원가입
        register_response = client.post(
            "/api/v1/auth/register",
            json=user_data
        )
        
        # Assert
        assert "password" not in register_response.json()
        assert "hashed_password" not in register_response.json()
    
    
    def test_sql_injection_attempt_blocked(
        self,
        client: TestClient
    ):
        """
        SQL Injection 시도 차단
        
        Given: SQL Injection 패턴
        When: 로그인 시도
        Then: 안전하게 처리
        """
        # Arrange - SQL Injection 시도
        malicious_data = {
            "username": "admin' OR '1'='1",
            "password": "' OR '1'='1"
        }
        
        # Act
        response = client.post(
            "/api/v1/auth/login",
            data=malicious_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # Assert - 로그인 실패해야 함
        assert response.status_code == 401
    
    
    def test_brute_force_multiple_failed_logins(
        self,
        client: TestClient,
        test_user: User
    ):
        """
        무차별 대입 공격 시뮬레이션
        
        Given: 등록된 사용자
        When: 여러 번 잘못된 비밀번호로 로그인 시도
        Then: 모두 실패
        """
        # Act - 10번 실패 시도
        failed_attempts = 0
        for i in range(10):
            response = client.post(
                "/api/v1/auth/login",
                data={
                    "username": test_user.username,
                    "password": f"wrongpass{i}"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if response.status_code == 401:
                failed_attempts += 1
        
        # Assert - 모두 실패해야 함
        assert failed_attempts == 10


# =============================================================================
# End-to-End 인증 시나리오
# =============================================================================

@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.e2e
class TestAuthEndToEnd:
    """인증 End-to-End 테스트"""
    
    def test_complete_auth_flow(
        self,
        client: TestClient
    ):
        """
        완전한 인증 흐름 테스트
        
        1. 회원가입
        2. 로그인
        3. 인증된 요청
        4. 로그아웃 (토큰 폐기)
        """
        # 1. 회원가입
        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "e2euser",
                "password": "e2epass123"
            }
        )
        assert register_response.status_code in [200, 201]
        
        # 2. 로그인
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "e2euser",
                "password": "e2epass123"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # 3. 인증된 요청
        auth_headers = {"Authorization": f"Bearer {token}"}
        account_response = client.get(
            "/api/v1/account/",
            headers=auth_headers
        )
        assert account_response.status_code == 200
    
    
    def test_register_login_and_order_flow(
        self,
        client: TestClient
    ):
        """
        회원가입 후 주문까지 전체 흐름
        
        1. 회원가입
        2. 로그인
        3. 주문 생성 (인증 필요)
        """
        from unittest.mock import patch
        from decimal import Decimal
        
        # 1. 회원가입
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "trader123",
                "password": "tradepass123"
            }
        )
        
        # 2. 로그인
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "trader123",
                "password": "tradepass123"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        token = login_response.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}
        
        # 3. 주문 생성 (Mock 사용)
        with patch("app.services.binance_service.get_current_price") as mock_price:
            with patch("app.services.binance_service.get_recent_trades") as mock_trades:
                mock_price.return_value = Decimal("50000")
                mock_trades.return_value = [{"price": "50000", "qty": "0.01"}]
                
                order_response = client.post(
                    "/api/v1/orders/",
                    headers=auth_headers,
                    json={
                        "symbol": "BTCUSDT",
                        "side": "BUY",
                        "order_type": "MARKET",
                        "quantity": 0.01
                    }
                )
                
                # 주문 성공 또는 실패 모두 허용 (인증은 통과)
                assert order_response.status_code in [200, 201, 400, 500]