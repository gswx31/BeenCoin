# tests/test_auth.py
"""
Authentication tests
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models.database import User

def test_register_user(client: TestClient, session: Session):
    """Test user registration"""
    response = client.post(
        "/auth/register",
        json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "NewPass123!"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "new@example.com"
    assert "id" in data

def test_register_duplicate_username(client: TestClient, test_user: User):
    """Test registration with duplicate username"""
    response = client.post(
        "/auth/register",
        json={
            "username": test_user.username,
            "email": "another@example.com",
            "password": "AnotherPass123!"
        }
    )
    
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()

def test_register_invalid_password(client: TestClient):
    """Test registration with invalid password"""
    response = client.post(
        "/auth/register",
        json={
            "username": "testuser2",
            "email": "test2@example.com",
            "password": "weak"
        }
    )
    
    assert response.status_code == 422  # Validation error

def test_login_success(client: TestClient, test_user: User):
    """Test successful login"""
    response = client.post(
        "/auth/login",
        json={
            "username": test_user.username,
            "password": "Test123!Pass"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == test_user.username

def test_login_invalid_credentials(client: TestClient, test_user: User):
    """Test login with invalid credentials"""
    response = client.post(
        "/auth/login",
        json={
            "username": test_user.username,
            "password": "WrongPassword"
        }
    )
    
    assert response.status_code == 401
    assert "Invalid username or password" in response.json()["detail"]

def test_login_nonexistent_user(client: TestClient):
    """Test login with non-existent user"""
    response = client.post(
        "/auth/login",
        json={
            "username": "nonexistent",
            "password": "SomePassword123!"
        }
    )
    
    assert response.status_code == 401
    assert "Invalid username or password" in response.json()["detail"]

def test_logout(client: TestClient):
    """Test logout endpoint"""
    response = client.post("/auth/logout")
    
    assert response.status_code == 200
    assert "logged out" in response.json()["message"].lower()