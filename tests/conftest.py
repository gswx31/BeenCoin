# tests/conftest.py
"""
pytest 설정 파일 - 모든 테스트에서 사용할 공통 fixture 정의
"""
import pytest
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from decimal import Decimal

# 애플리케이션 모듈 import
from app.main import app
from app.models.database import User, TradingAccount, Position, Order
from app.core.database import get_session
from app.utils.security import get_password_hash


@pytest.fixture(scope="function")
def test_engine():
    """
    테스트용 인메모리 데이터베이스 엔진 생성
    각 테스트 함수마다 새로운 DB 생성
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # 멀티스레드 환경에서 안전
        echo=False  # SQL 로그 비활성화 (필요시 True로 변경)
    )
    # 모든 테이블 생성
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="function")
def session(test_engine):
    """
    테스트용 데이터베이스 세션
    각 테스트 함수마다 독립적인 세션 제공
    """
    with Session(test_engine) as session:
        yield session
        # 테스트 후 자동으로 롤백 (선택사항)
        session.rollback()


@pytest.fixture(scope="function")
def client(test_engine):
    """
    FastAPI TestClient - API 엔드포인트 테스트용
    """
    def get_test_session():
        with Session(test_engine) as session:
            yield session
    
    # 실제 DB 의존성을 테스트 DB로 오버라이드
    app.dependency_overrides[get_session] = get_test_session
    
    with TestClient(app) as test_client:
        yield test_client
    
    # 테스트 후 오버라이드 제거
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(session):
    """
    테스트용 사용자 생성
    """
    user = User(
        username="testuser",
        hashed_password=get_password_hash("testpass123"),
        is_active=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_account(session, test_user):
    """
    테스트용 거래 계정 생성 (초기 잔액 100만원)
    """
    account = TradingAccount(
        user_id=test_user.id,
        balance=Decimal("1000000"),
        total_profit=Decimal("0")
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


@pytest.fixture(scope="function")
def auth_headers(client, test_user):
    """
    인증 헤더 생성 - 로그인 후 토큰 반환
    """
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "testpass123"
        }
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def test_position(session, test_account):
    """
    테스트용 포지션 생성 (BTC 0.1개 보유)
    """
    position = Position(
        account_id=test_account.id,
        symbol="BTCUSDT",
        quantity=Decimal("0.1"),
        average_price=Decimal("50000"),
        current_value=Decimal("5000"),
        unrealized_profit=Decimal("0")
    )
    session.add(position)
    session.commit()
    session.refresh(position)
    return position