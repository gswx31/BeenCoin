# tests/conftest.py
"""
pytest 설정 파일 - 모든 테스트에서 사용할 공통 fixture 정의
"""
import pytest
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from decimal import Decimal
from datetime import datetime

# 애플리케이션 모듈 import
from app.main import app
from app.models.database import User, TradingAccount, Position, Order
from app.core.database import get_session
from app.utils.security import get_password_hash, create_access_token


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
    yield engine
    # 테스트 후 정리
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def session(test_engine):
    """
    테스트용 데이터베이스 세션
    각 테스트 함수마다 독립적인 세션 제공
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    
    yield session
    
    # 테스트 후 롤백 및 정리
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(test_engine):
    """
    FastAPI TestClient - API 엔드포인트 테스트용
    """
    def get_test_session():
        connection = test_engine.connect()
        transaction = connection.begin()
        session = Session(bind=connection)
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()
            connection.close()
    
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
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_inactive_user(session):
    """
    비활성화된 테스트 사용자 생성
    """
    user = User(
        username="inactiveuser",
        hashed_password=get_password_hash("testpass123"),
        is_active=False,
        created_at=datetime.utcnow()
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
        total_profit=Decimal("0"),
        created_at=datetime.utcnow()
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


@pytest.fixture(scope="function")
def test_account_low_balance(session, test_user):
    """
    잔액이 부족한 테스트 계정 생성
    """
    account = TradingAccount(
        user_id=test_user.id,
        balance=Decimal("1000"),  # 낮은 잔액
        total_profit=Decimal("0"),
        created_at=datetime.utcnow()
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
    assert response.status_code == 200, f"로그인 실패: {response.json()}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def auth_token(test_user):
    """
    직접 토큰 생성 (로그인 API 호출 없이)
    """
    token = create_access_token(data={"sub": test_user.username})
    return token


@pytest.fixture(scope="function")
def test_position(session, test_account):
    """
    테스트용 포지션 생성 (BTC 0.1개 보유, 평균가 50000)
    """
    position = Position(
        account_id=test_account.id,
        symbol="BTCUSDT",
        quantity=Decimal("0.1"),
        average_price=Decimal("50000"),
        current_value=Decimal("5000"),
        unrealized_profit=Decimal("0"),
        created_at=datetime.utcnow()
    )
    session.add(position)
    session.commit()
    session.refresh(position)
    return position


@pytest.fixture(scope="function")
def test_multiple_positions(session, test_account):
    """
    여러 포지션 생성 (다양한 코인)
    """
    positions = [
        Position(
            account_id=test_account.id,
            symbol="BTCUSDT",
            quantity=Decimal("0.1"),
            average_price=Decimal("50000"),
            current_value=Decimal("5000"),
            unrealized_profit=Decimal("0"),
            created_at=datetime.utcnow()
        ),
        Position(
            account_id=test_account.id,
            symbol="ETHUSDT",
            quantity=Decimal("1.5"),
            average_price=Decimal("3000"),
            current_value=Decimal("4500"),
            unrealized_profit=Decimal("0"),
            created_at=datetime.utcnow()
        ),
        Position(
            account_id=test_account.id,
            symbol="BNBUSDT",
            quantity=Decimal("10"),
            average_price=Decimal("400"),
            current_value=Decimal("4000"),
            unrealized_profit=Decimal("0"),
            created_at=datetime.utcnow()
        )
    ]
    for pos in positions:
        session.add(pos)
    session.commit()
    for pos in positions:
        session.refresh(pos)
    return positions


@pytest.fixture(scope="function")
def test_filled_order(session, test_account):
    """
    체결된 주문 생성
    """
    order = Order(
        account_id=test_account.id,
        symbol="BTCUSDT",
        side="BUY",
        order_type="MARKET",
        quantity=Decimal("0.1"),
        price=Decimal("50000"),
        status="FILLED",
        fee=Decimal("5"),
        created_at=datetime.utcnow()
    )
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


@pytest.fixture(scope="function")
def test_pending_order(session, test_account):
    """
    대기 중인 주문 생성
    """
    order = Order(
        account_id=test_account.id,
        symbol="BTCUSDT",
        side="BUY",
        order_type="LIMIT",
        quantity=Decimal("0.1"),
        price=Decimal("48000"),
        status="PENDING",
        fee=Decimal("0"),
        created_at=datetime.utcnow()
    )
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


@pytest.fixture(scope="function")
def test_multiple_orders(session, test_account):
    """
    여러 주문 생성 (다양한 상태와 타입)
    """
    orders = [
        Order(
            account_id=test_account.id,
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity=Decimal("0.1"),
            price=Decimal("50000"),
            status="FILLED",
            fee=Decimal("5"),
            created_at=datetime.utcnow()
        ),
        Order(
            account_id=test_account.id,
            symbol="ETHUSDT",
            side="BUY",
            order_type="LIMIT",
            quantity=Decimal("1.0"),
            price=Decimal("2900"),
            status="PENDING",
            fee=Decimal("0"),
            created_at=datetime.utcnow()
        ),
        Order(
            account_id=test_account.id,
            symbol="BTCUSDT",
            side="SELL",
            order_type="MARKET",
            quantity=Decimal("0.05"),
            price=Decimal("51000"),
            status="FILLED",
            fee=Decimal("2.5"),
            created_at=datetime.utcnow()
        )
    ]
    for order in orders:
        session.add(order)
    session.commit()
    for order in orders:
        session.refresh(order)
    return orders


@pytest.fixture(autouse=True)
def reset_db(session):
    """
    각 테스트 후 데이터베이스 초기화 (자동 실행)
    """
    yield
    # 테스트 후 모든 데이터 삭제
    session.query(Order).delete()
    session.query(Position).delete()
    session.query(TradingAccount).delete()
    session.query(User).delete()
    session.commit()


# 테스트용 상수
TEST_USER_DATA = {
    "username": "testuser",
    "password": "testpass123"
}

TEST_ACCOUNT_INITIAL_BALANCE = Decimal("1000000")
TEST_BTC_PRICE = Decimal("50000")
TEST_ETH_PRICE = Decimal("3000")
TEST_TRADING_FEE_RATE = Decimal("0.001")  # 0.1%