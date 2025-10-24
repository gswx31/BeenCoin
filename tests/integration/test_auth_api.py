# tests/integration/test_auth_api.py
"""
인증 API 통합 테스트
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
        assert "이미 존재" in response.json()["detail"] or "already exists" in response.json()["detail"].lower()
    
    
    def test_register_invalid_username(self, client):
        """유효하지 않은 사용자명으로 회원가입 실패"""
        # 너무 짧은 사용자명
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "ab",
                "password": "testpass123"
            }
        )
        assert response.status_code == 422
        
        # 특수문자 포함
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "user@name",
                "password": "testpass123"
            }
        )
        assert response.status_code == 422
    
    
    def test_register_invalid_password(self, client):
        """유효하지 않은 비밀번호로 회원가입 실패"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "validuser",
                "password": "short"  # 너무 짧음
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
        assert "incorrect" in response.json()["detail"].lower() or "비밀번호" in response.json()["detail"]
    
    
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


class TestProtectedRoutes:
    """인증이 필요한 라우트 테스트"""
    
    def test_access_protected_route_without_token(self, client):
        """토큰 없이 보호된 라우트 접근 시 실패"""
        response = client.get("/api/v1/account/")
        assert response.status_code == 401
    
    
    def test_access_protected_route_with_invalid_token(self, client):
        """유효하지 않은 토큰으로 접근 시 실패"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/account/", headers=headers)
        assert response.status_code == 401
    
    
    def test_access_protected_route_with_valid_token(self, client, auth_headers):
        """유효한 토큰으로 접근 성공"""
        response = client.get("/api/v1/account/", headers=auth_headers)
        assert response.status_code == 200