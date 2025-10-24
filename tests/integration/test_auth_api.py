# tests/integration/test_auth_api.py
"""
인증 API 통합 테스트
회원가입, 로그인, 인증된 라우트 접근 테스트
"""
import pytest
from fastapi.testclient import TestClient


class TestAuthAPI:
    """인증 관련 API 테스트"""
    
    def test_register_success(self, client):
        """회원가입 성공 테스트"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "password": "newpass123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newuser"
        assert "id" in data
        assert "hashed_password" not in data  # 비밀번호는 반환되지 않음
        assert "created_at" in data
    
    
    def test_register_duplicate_username(self, client, test_user):
        """중복 사용자명으로 회원가입 실패 테스트"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",  # 이미 존재하는 사용자
                "password": "testpass123"
            }
        )
        
        assert response.status_code == 400
        error_detail = response.json()["detail"].lower()
        assert "이미 존재" in error_detail or "already exists" in error_detail or "duplicate" in error_detail
    
    
    def test_register_invalid_username_too_short(self, client):
        """너무 짧은 사용자명으로 회원가입 실패"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "ab",  # 3자 미만
                "password": "testpass123"
            }
        )
        assert response.status_code == 422
        
    
    def test_register_invalid_username_too_long(self, client):
        """너무 긴 사용자명으로 회원가입 실패"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "a" * 51,  # 50자 초과
                "password": "testpass123"
            }
        )
        assert response.status_code == 422
    
    
    def test_register_invalid_username_special_chars(self, client):
        """특수문자 포함 사용자명으로 회원가입 실패"""
        invalid_usernames = ["user@name", "user#123", "user space", "user!"]
        
        for username in invalid_usernames:
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "username": username,
                    "password": "testpass123"
                }
            )
            assert response.status_code == 422, f"'{username}' should be invalid"
    
    
    def test_register_invalid_password_too_short(self, client):
        """너무 짧은 비밀번호로 회원가입 실패"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "validuser",
                "password": "short"  # 8자 미만
            }
        )
        
        assert response.status_code == 422
    
    
    def test_register_invalid_password_too_long(self, client):
        """너무 긴 비밀번호로 회원가입 실패"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "validuser",
                "password": "a" * 101  # 100자 초과
            }
        )
        
        assert response.status_code == 422
    
    
    def test_register_missing_username(self, client):
        """사용자명 누락 시 회원가입 실패"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "password": "testpass123"
            }
        )
        
        assert response.status_code == 422
    
    
    def test_register_missing_password(self, client):
        """비밀번호 누락 시 회원가입 실패"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "validuser"
            }
        )
        
        assert response.status_code == 422
    
    
    def test_login_success(self, client, test_user):
        """로그인 성공 테스트"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "testpass123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "username" in data
        assert data["username"] == "testuser"
        # 토큰이 유효한 형식인지 확인
        assert len(data["access_token"]) > 20
    
    
    def test_login_wrong_password(self, client, test_user):
        """잘못된 비밀번호로 로그인 실패 테스트"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
        error_detail = response.json()["detail"].lower()
        assert "incorrect" in error_detail or "비밀번호" in error_detail or "invalid" in error_detail
    
    
    def test_login_nonexistent_user(self, client):
        """존재하지 않는 사용자로 로그인 실패 테스트"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "anypassword"
            }
        )
        
        assert response.status_code == 401
        error_detail = response.json()["detail"].lower()
        assert "not found" in error_detail or "incorrect" in error_detail or "존재" in error_detail
    
    
    def test_login_inactive_user(self, client, test_inactive_user):
        """비활성화된 사용자 로그인 실패 테스트"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "inactiveuser",
                "password": "testpass123"
            }
        )
        
        # 비활성 사용자는 로그인 불가
        assert response.status_code in [401, 403]
    
    
    def test_login_missing_username(self, client):
        """사용자명 누락 시 로그인 실패"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "password": "testpass123"
            }
        )
        
        assert response.status_code == 422
    
    
    def test_login_missing_password(self, client):
        """비밀번호 누락 시 로그인 실패"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser"
            }
        )
        
        assert response.status_code == 422
    
    
    def test_login_empty_credentials(self, client):
        """빈 자격증명으로 로그인 실패"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "",
                "password": ""
            }
        )
        
        assert response.status_code in [401, 422]
    
    
    def test_register_and_login_flow(self, client):
        """회원가입 후 바로 로그인하는 플로우 테스트"""
        # 1. 회원가입
        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "flowuser",
                "password": "flowpass123"
            }
        )
        assert register_response.status_code == 200
        
        # 2. 로그인
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "flowuser",
                "password": "flowpass123"
            }
        )
        assert login_response.status_code == 200
        assert "access_token" in login_response.json()


class TestProtectedRoutes:
    """인증이 필요한 라우트 테스트"""
    
    def test_access_protected_route_without_token(self, client):
        """토큰 없이 보호된 라우트 접근 시 실패"""
        protected_endpoints = [
            "/api/v1/account/",
            "/api/v1/positions/",
            "/api/v1/orders/"
        ]
        
        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401, f"{endpoint} should require authentication"
    
    
    def test_access_protected_route_with_invalid_token(self, client):
        """유효하지 않은 토큰으로 접근 시 실패"""
        headers = {"Authorization": "Bearer invalid_token_12345"}
        
        protected_endpoints = [
            "/api/v1/account/",
            "/api/v1/positions/",
            "/api/v1/orders/"
        ]
        
        for endpoint in protected_endpoints:
            response = client.get(endpoint, headers=headers)
            assert response.status_code == 401, f"{endpoint} should reject invalid token"
    
    
    def test_access_protected_route_with_malformed_token(self, client):
        """잘못된 형식의 토큰으로 접근 시 실패"""
        malformed_headers = [
            {"Authorization": "invalid_token"},  # Bearer 누락
            {"Authorization": "Bearer"},  # 토큰 누락
            {"Authorization": ""},  # 빈 헤더
        ]
        
        for headers in malformed_headers:
            response = client.get("/api/v1/account/", headers=headers)
            assert response.status_code == 401
    
    
    def test_access_protected_route_with_valid_token(self, client, auth_headers, test_account):
        """유효한 토큰으로 접근 성공"""
        response = client.get("/api/v1/account/", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "balance" in data
        assert "total_profit" in data
    
    
    def test_token_reuse(self, client, auth_headers, test_account):
        """동일한 토큰으로 여러 요청 가능한지 확인"""
        # 첫 번째 요청
        response1 = client.get("/api/v1/account/", headers=auth_headers)
        assert response1.status_code == 200
        
        # 두 번째 요청 (같은 토큰)
        response2 = client.get("/api/v1/account/", headers=auth_headers)
        assert response2.status_code == 200
        
        # 세 번째 요청 (같은 토큰)
        response3 = client.get("/api/v1/positions/", headers=auth_headers)
        assert response3.status_code == 200
    
    
    def test_different_users_cannot_access_others_data(self, client, test_user, test_account):
        """다른 사용자의 데이터에 접근할 수 없는지 확인"""
        # 첫 번째 사용자 로그인
        response1 = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "testpass123"
            }
        )
        token1 = response1.json()["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}
        
        # 두 번째 사용자 생성 및 로그인
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser2",
                "password": "testpass456"
            }
        )
        response2 = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser2",
                "password": "testpass456"
            }
        )
        token2 = response2.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        # 각 사용자는 자신의 데이터만 볼 수 있어야 함
        account1 = client.get("/api/v1/account/", headers=headers1)
        account2 = client.get("/api/v1/account/", headers=headers2)
        
        assert account1.status_code == 200
        assert account2.status_code == 200
        
        # 두 계정의 데이터가 다른지 확인 (ID가 다름)
        # 실제로는 user_id가 다르므로 다른 계정을 조회
        assert account1.json() != account2.json() or account1.json()["user_id"] != account2.json()["user_id"]