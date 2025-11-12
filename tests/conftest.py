# conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool
from typing import Generator


# tests/conftest.py
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 이제 app 모듈 임포트
from app.main import app
from app.models.database import (
    User, TradingAccount, Position, Order, Transaction,
    OrderSide, OrderType, OrderStatus
)
from app.core.database import get_session
from app.utils.security import hash_password, create_access_token
from app.schemas.order import OrderCreate

from datetime import datetime


# =============================================================================
# 1. 세션 스코프: DB 한 번만 생성 (빠름)
# =============================================================================
@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


# =============================================================================
# 2. 함수 스코프: 각 테스트는 독립된 트랜잭션 + rollback (격리)
# =============================================================================
@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, expire_on_commit=False)

    yield session

    session.close()
    transaction.rollback()   # 중요: rollback으로 격리 보장
    connection.close()


# =============================================================================
# 3. 클라이언트: 앱에 테스트 세션 주입
# =============================================================================
@pytest.fixture(scope="function")
def client(db_session):
    def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# =============================================================================
# 4. 사용자 팩토리: 당신의 스키마 그대로 사용
# =============================================================================
@pytest.fixture
def user_factory(db_session):
    def _create_user(
        username: str = "testuser",
        password: str = "testpass123",
        email: str = "test@example.com",
        is_active: bool = True,
        is_admin: bool = False
    ) -> User:
        user = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            is_active=is_active,
            is_admin=is_admin,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # 로그인용 원본 비밀번호 저장
        user._test_password = password
        return user

    return _create_user


# =============================================================================
# 5. 테스트용 사용자
# =============================================================================
@pytest.fixture
def test_user(user_factory):
    return user_factory()


# =============================================================================
# 6. 인증 토큰 (실제 로그인)
# =============================================================================
@pytest.fixture
def auth_token(client, test_user):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user.username,
            "password": test_user._test_password
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]