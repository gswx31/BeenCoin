# tests/test_basic.py
import pytest
from fastapi.testclient import TestClient

class TestBasicAPI:
    """기본 API 테스트"""
    
    def test_root_endpoint(self, client: TestClient):
        """루트 엔드포인트 테스트"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
    
    def test_health_check(self, client: TestClient):
        """헬스 체크 테스트"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_api_docs(self, client: TestClient):
        """API 문서 테스트"""
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_register_endpoint_exists(self, client: TestClient):
        """회원가입 엔드포인트 존재 확인"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com", 
                "password": "testpass123"
            }
        )
        # 200(성공)이나 400(중복) 또는 422(검증 실패)는 엔드포인트가 존재함을 의미
        assert response.status_code != 404