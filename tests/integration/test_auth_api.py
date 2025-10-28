# tests/integration/test_auth_api.py
"""
인증 API 통합 테스트 - 수정 버전
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
        # ✅ 개선: 더 유연한 에러 메시지 확인
        assert any(keyword in error_detail for keyword in ["이미 존재", "already exists", "duplicate", "taken"])
    
    
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
                    "password": "validpass123"
                }
            )
            # 422 (Validation Error) 또는 400 (Bad Request) 예상
            assert response.status_code in [400, 422], f"username={username} should fail"
    
    
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
        # ✅ 개선: 더 유연한 에러 메시지 확인
        assert any(keyword in error_detail for keyword in ["incorrect", "비밀번호", "invalid", "wrong"])
    
    
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
        # ✅ 개선: 다양한 에러 메시지 패턴 수용
        assert any(keyword in error_detail for keyword in ["not found", "incorrect", "존재", "invalid"])
    
    
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
        # ✅ 개선: 에러 메시지 검증 추가
        if response.status_code != 401:
            error_detail = response.json()["detail"].lower()
            assert any(keyword in error_detail for keyword in ["inactive", "비활성", "disabled"])
    
    
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
    
    
    def test_protected_route_without_token(self, client):
        """인증 토큰 없이 보호된 라우트 접근 시도"""
        response = client.get("/api/v1/account/")
        assert response.status_code == 401
    
    
    def test_protected_route_with_invalid_token(self, client):
        """잘못된 토큰으로 보호된 라우트 접근 시도"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/account/", headers=headers)
        assert response.status_code == 401
    
    
    def test_protected_route_with_valid_token(self, client, auth_headers):
        """유효한 토큰으로 보호된 라우트 접근 성공"""
        response = client.get("/api/v1/account/", headers=auth_headers)
        # 성공 또는 리소스 없음 (계정 미생성)
        assert response.status_code in [200, 404]
    
    
    def test_token_expiration_format(self, client, test_user):
        """토큰이 올바른 JWT 형식인지 확인"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "testpass123"
            }
        )
        
        assert response.status_code == 200
        token = response.json()["access_token"]
        
        # JWT는 3개의 부분으로 나뉘어짐 (헤더.페이로드.서명)
        parts = token.split(".")
        assert len(parts) == 3
        
        # 각 부분이 base64 인코딩된 문자열인지 확인
        for part in parts:
            assert len(part) > 0
            assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in part)