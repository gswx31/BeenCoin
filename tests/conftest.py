# tests/conftest.py
"""
pytest 설정 파일 - 원래 구조 (TradingAccount)
"""
import pytest
import sys
from pathlib import Path
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from decimal import Decimal
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.main import app
from app.models.database import User, TradingAccount, Position, Order
from app.core.database import get_session
from app.utils.security import hash_password, create_access_token


# =====================================================
# 데이터베이스 관련 Fixtures
# =====================================================

@pytest.fixture(scope="function")
def test_engine():
    """테스트용 인메모리 DB 엔진"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def session(test_engine):
    """테스트용 DB 세션"""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(test_engine):
    """FastAPI TestClient"""
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
    
    app.dependency_overrides[get_session] = get_test_session
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


# =====================================================
# 사용자 관련 Fixtures
# =====================================================

@pytest.fixture(scope="function")
def test_user(session):
    """테스트용 사용자"""
    user = User(
        username="testuser",
        hashed_password=hash_password("testpass123"),
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_inactive_user(session):
    """비활성화된 사용자"""
    user = User(
        username="inactiveuser",
        hashed_password=hash_password("testpass123"),
        is_active=False,
        created_at=datetime.utcnow()
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


# =====================================================
# 계정 관련 Fixtures
# =====================================================

@pytest.fixture(scope="function")
def test_account(session, test_user):
    """테스트용 거래 계정 (잔액 100만원)"""
    account = TradingAccount(
        user_id=test_user.id,
        balance=Decimal("1000000"),
        total_profit=Decimal("0"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


@pytest.fixture(scope="function")
def test_account_low_balance(session, test_user):
    """잔액 부족 계정"""
    account = TradingAccount(
        user_id=test_user.id,
        balance=Decimal("1000"),
        total_profit=Decimal("0"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


# =====================================================
# 인증 관련 Fixtures
# =====================================================

@pytest.fixture(scope="function")
def auth_headers(client, test_user, test_account):
    """인증 헤더"""
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
    """직접 토큰 생성"""
    token = create_access_token(data={"sub": test_user.username})
    return token


# =====================================================
# 포지션 관련 Fixtures
# =====================================================

@pytest.fixture(scope="function")
def test_position(session, test_account):
    """테스트용 포지션 (BTC 0.1개, 평균가 50000)"""
    position = Position(
        account_id=test_account.id,
        symbol="BTCUSDT",
        quantity=Decimal("0.1"),
        average_price=Decimal("50000"),
        current_price=Decimal("50000"),
        current_value=Decimal("5000"),
        unrealized_profit=Decimal("0"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    session.add(position)
    session.commit()
    session.refresh(position)
    return position


@pytest.fixture(scope="function")
def test_multiple_positions(session, test_account):
    """여러 포지션"""
    positions_data = [
        {
            "symbol": "BTCUSDT",
            "quantity": Decimal("0.1"),
            "average_price": Decimal("50000"),
            "current_price": Decimal("50000"),
            "current_value": Decimal("5000")
        },
        {
            "symbol": "ETHUSDT",
            "quantity": Decimal("1.5"),
            "average_price": Decimal("3000"),
            "current_price": Decimal("3000"),
            "current_value": Decimal("4500")
        },
        {
            "symbol": "BNBUSDT",
            "quantity": Decimal("10"),
            "average_price": Decimal("400"),
            "current_price": Decimal("400"),
            "current_value": Decimal("4000")
        }
    ]
    
    positions = []
    for data in positions_data:
        position = Position(
            account_id=test_account.id,
            unrealized_profit=Decimal("0"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            **data
        )
        session.add(position)
        positions.append(position)
    
    session.commit()
    for pos in positions:
        session.refresh(pos)
    
    return positions


# =====================================================
# 주문 관련 Fixtures
# =====================================================

@pytest.fixture(scope="function")
def test_filled_order(session, test_user, test_account):
    """체결된 주문"""
    order = Order(
        account_id=test_account.id,
        user_id=test_user.id,
        symbol="BTCUSDT",
        side="BUY",
        order_type="MARKET",
        quantity=Decimal("0.1"),
        price=Decimal("50000"),
        order_status="FILLED",
        filled_quantity=Decimal("0.1"),
        average_price=Decimal("50000"),
        fee=Decimal("5"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


@pytest.fixture(scope="function")
def test_pending_order(session, test_user, test_account):
    """대기 중인 주문"""
    order = Order(
        account_id=test_account.id,
        user_id=test_user.id,
        symbol="BTCUSDT",
        side="BUY",
        order_type="LIMIT",
        quantity=Decimal("0.1"),
        price=Decimal("48000"),
        order_status="PENDING",
        filled_quantity=Decimal("0"),
        fee=Decimal("0"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


@pytest.fixture(scope="function")
def test_multiple_orders(session, test_user, test_account):
    """여러 주문"""
    orders_data = [
        {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": Decimal("0.1"),
            "price": Decimal("50000"),
            "order_status": "FILLED",
            "filled_quantity": Decimal("0.1"),
            "average_price": Decimal("50000"),
            "fee": Decimal("5")
        },
        {
            "symbol": "ETHUSDT",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": Decimal("1.0"),
            "price": Decimal("2900"),
            "order_status": "PENDING",
            "filled_quantity": Decimal("0"),
            "fee": Decimal("0")
        },
        {
            "symbol": "BTCUSDT",
            "side": "SELL",
            "order_type": "MARKET",
            "quantity": Decimal("0.05"),
            "price": Decimal("51000"),
            "order_status": "FILLED",
            "filled_quantity": Decimal("0.05"),
            "average_price": Decimal("51000"),
            "fee": Decimal("2.5")
        }
    ]
    
    orders = []
    for data in orders_data:
        order = Order(
            account_id=test_account.id,
            user_id=test_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            **data
        )
        session.add(order)
        orders.append(order)
    
    session.commit()
    for order in orders:
        session.refresh(order)
    
    return orders


# =====================================================
# 테스트용 상수
# =====================================================

TEST_USER_DATA = {
    "username": "testuser",
    "password": "testpass123"
}

TEST_INITIAL_BALANCE = Decimal("1000000")
TEST_BTC_PRICE = Decimal("50000")
TEST_ETH_PRICE = Decimal("3000")
TEST_FEE_RATE = Decimal("0.001")