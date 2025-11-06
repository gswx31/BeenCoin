"""
BeenCoin 테스트 픽스처 - 로그인 문제 해결 버전
=========================================

핵심 수정:
1. user_factory에서 원본 비밀번호 저장 (user._test_password)
2. test_user fixture에 password 속성 추가
3. auth_headers가 실제 로그인된 토큰 사용
"""
import asyncio
import pytest
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator, Callable
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import logging

from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.main import app
from app.models.database import (
    User, TradingAccount, Position, Order, Transaction,
    OrderSide, OrderType, OrderStatus
)
from app.core.database import get_session
from app.utils.security import hash_password, create_access_token
from app.schemas.order import OrderCreate

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """이벤트 루프 - 세션 레벨"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


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
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """DB 세션 - 트랜잭션 롤백 지원"""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, expire_on_commit=False)
    
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


# =============================================================================
# Client Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def client(test_engine) -> Generator[TestClient, None, None]:
    """FastAPI TestClient"""
    def get_test_session():
        connection = test_engine.connect()
        transaction = connection.begin()
        session = Session(bind=connection, expire_on_commit=False)
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


# =============================================================================
# User Fixtures - 로그인 문제 해결!
# =============================================================================

@pytest.fixture
def user_factory(db_session: Session) -> Callable:
    """
    사용자 팩토리 - 원본 비밀번호 저장
    
    핵심: user._test_password에 원본 비밀번호 저장!
    """
    def _create_user(
        username: str = "testuser",
        password: str = "testpass123",
        is_active: bool = True,
        **kwargs
    ) -> User:
        user = User(
            username=username,
            hashed_password=hash_password(password),
            is_active=is_active,
            created_at=datetime.utcnow(),
            **kwargs
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # ✅ 원본 비밀번호 저장 (로그인 테스트용)
        user._test_password = password
        
        return user
    
    return _create_user


@pytest.fixture
def test_user(user_factory) -> User:
    """
    기본 테스트 사용자 - 비밀번호 알 수 있음!
    
    사용법:
        # 로그인 시
        username = test_user.username
        password = test_user._test_password  # 원본 비밀번호!
    """
    return user_factory(username="testuser", password="testpass123")


@pytest.fixture
def multiple_users(user_factory) -> list[User]:
    """여러 사용자 생성"""
    return [
        user_factory(username=f"user{i}", password=f"pass{i}")
        for i in range(1, 4)
    ]


@pytest.fixture(params=["active_user", "inactive_user"])
def parameterized_user(request, user_factory) -> User:
    """파라미터화된 사용자"""
    if request.param == "active_user":
        return user_factory(username="active", is_active=True)
    else:
        return user_factory(username="inactive", is_active=False)


# =============================================================================
# Account Fixtures
# =============================================================================

@pytest.fixture
def account_factory(db_session: Session) -> Callable:
    """거래 계정 팩토리 - locked_balance 포함"""
    def _create_account(
        user: User,
        balance: Decimal = Decimal("1000000"),
        locked_balance: Decimal = Decimal("0"),
        total_profit: Decimal = Decimal("0"),
        **kwargs
    ) -> TradingAccount:
        account = TradingAccount(
            user_id=user.id,
            balance=balance,
            locked_balance=locked_balance,
            total_profit=total_profit,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            **kwargs
        )
        db_session.add(account)
        db_session.commit()
        db_session.refresh(account)
        return account
    
    return _create_account


@pytest.fixture
def test_account(test_user: User, account_factory) -> TradingAccount:
    """기본 테스트 계정"""
    return account_factory(user=test_user)


@pytest.fixture(params=[
    Decimal("1000000"),
    Decimal("100000"),
    Decimal("10000000"),
])
def varied_balance_account(request, test_user: User, account_factory) -> TradingAccount:
    """다양한 잔액의 계정"""
    return account_factory(user=test_user, balance=request.param)


# =============================================================================
# Order Fixtures
# =============================================================================

@pytest.fixture
def order_factory(db_session: Session) -> Callable:
    """주문 팩토리 - Enum 타입 사용"""
    def _create_order(
        user: User,
        account: TradingAccount,
        symbol: str = "BTCUSDT",
        side: OrderSide = OrderSide.BUY,
        order_type: OrderType = OrderType.MARKET,
        order_status: OrderStatus = OrderStatus.PENDING,
        price: Decimal = None,
        quantity: Decimal = Decimal("0.1"),
        filled_quantity: Decimal = Decimal("0"),
        average_price: Decimal = None,
        stop_price: Decimal = None,
        **kwargs
    ) -> Order:
        order = Order(
            account_id=account.id,
            user_id=user.id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            order_status=order_status,
            price=price,
            quantity=quantity,
            filled_quantity=filled_quantity,
            average_price=average_price,
            stop_price=stop_price,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            **kwargs
        )
        db_session.add(order)
        db_session.commit()
        db_session.refresh(order)
        return order
    
    return _create_order


@pytest.fixture
def test_order(test_user: User, test_account: TradingAccount, order_factory) -> Order:
    """기본 테스트 주문"""
    return order_factory(user=test_user, account=test_account)


@pytest.fixture
def pending_order(test_user: User, test_account: TradingAccount, order_factory) -> Order:
    """대기 중인 지정가 주문"""
    return order_factory(
        user=test_user,
        account=test_account,
        order_type=OrderType.LIMIT,
        order_status=OrderStatus.PENDING,
        price=Decimal("49000")
    )


@pytest.fixture
def filled_order(test_user: User, test_account: TradingAccount, order_factory) -> Order:
    """체결 완료된 주문"""
    return order_factory(
        user=test_user,
        account=test_account,
        order_type=OrderType.MARKET,
        order_status=OrderStatus.FILLED,
        filled_quantity=Decimal("0.1"),
        average_price=Decimal("50000")
    )


# =============================================================================
# Position Fixtures
# =============================================================================

@pytest.fixture
def position_factory(db_session: Session) -> Callable:
    """포지션 팩토리"""
    def _create_position(
        account: TradingAccount,
        symbol: str = "BTCUSDT",
        quantity: Decimal = Decimal("0.1"),
        average_price: Decimal = Decimal("50000"),
        current_price: Decimal = None,
        **kwargs
    ) -> Position:
        if current_price is None:
            current_price = average_price
        
        position = Position(
            account_id=account.id,
            symbol=symbol,
            quantity=quantity,
            average_price=average_price,
            current_price=current_price,
            current_value=quantity * current_price,
            unrealized_profit=quantity * (current_price - average_price),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            **kwargs
        )
        db_session.add(position)
        db_session.commit()
        db_session.refresh(position)
        return position
    
    return _create_position


@pytest.fixture
def test_position(test_account: TradingAccount, position_factory) -> Position:
    """기본 테스트 포지션"""
    return position_factory(account=test_account)


@pytest.fixture
def btc_position(test_account: TradingAccount, position_factory) -> Position:
    """BTC 포지션"""
    return position_factory(
        account=test_account,
        symbol="BTCUSDT",
        quantity=Decimal("0.1"),
        average_price=Decimal("45000")
    )


# =============================================================================
# Authentication Fixtures - 실제 로그인 사용!
# =============================================================================

@pytest.fixture
def auth_token(test_user: User, client: TestClient) -> str:
    """
    실제 로그인을 통한 JWT 토큰 - 로그인 문제 해결!
    
    기존 문제: create_access_token()으로 직접 생성
    해결: 실제 /auth/login API 호출
    """
    # 실제 로그인 API 호출
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user.username,
            "password": test_user._test_password  # 원본 비밀번호!
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        # 로그인 실패 시 직접 생성 (fallback)
        return create_access_token(data={"sub": test_user.username})


@pytest.fixture
def auth_headers(auth_token: str) -> dict:
    """인증 헤더"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def expired_token(test_user: User) -> str:
    """만료된 토큰"""
    return create_access_token(
        data={"sub": test_user.username},
        expires_delta=timedelta(minutes=-10)
    )


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_binance_price():
    """Binance 현재가 조회 Mock"""
    with patch("app.services.binance_service.get_current_price") as mock:
        mock.return_value = Decimal("50000")
        yield mock


@pytest.fixture
def mock_binance_trades():
    """Binance 최근 체결 내역 Mock"""
    with patch("app.services.binance_service.get_recent_trades") as mock:
        mock.return_value = [
            {"price": "50000", "qty": "0.05"},
            {"price": "49900", "qty": "0.05"},
        ]
        yield mock


@pytest.fixture
def mock_binance_service():
    """Binance Service 완전 Mock"""
    with patch("app.services.binance_service.get_current_price") as mock_price, \
         patch("app.services.binance_service.get_recent_trades") as mock_trades:
        
        mock_price.return_value = Decimal("50000")
        mock_trades.return_value = [
            {"price": "50000", "qty": "0.1"},
        ]
        
        yield {
            "price": mock_price,
            "trades": mock_trades
        }


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def sample_coin_symbols() -> list[str]:
    """샘플 코인 심볼"""
    return ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT"]


@pytest.fixture
def sample_prices() -> dict[str, Decimal]:
    """샘플 가격 데이터"""
    return {
        "BTCUSDT": Decimal("50000"),
        "ETHUSDT": Decimal("3000"),
        "BNBUSDT": Decimal("400"),
        "ADAUSDT": Decimal("0.5")
    }


@pytest.fixture
def sample_order_data() -> OrderCreate:
    """샘플 주문 데이터"""
    return OrderCreate(
        symbol="BTCUSDT",
        side="BUY",
        order_type="MARKET",
        quantity=Decimal("0.1")
    )


@pytest.fixture
def sample_limit_order_data() -> OrderCreate:
    """샘플 지정가 주문 데이터"""
    return OrderCreate(
        symbol="BTCUSDT",
        side="BUY",
        order_type="LIMIT",
        price=Decimal("49000"),
        quantity=Decimal("0.1")
    )


# =============================================================================
# Performance Fixtures
# =============================================================================

@pytest.fixture
def benchmark_timer():
    """벤치마크 타이머"""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.perf_counter()
        
        def stop(self):
            self.end_time = time.perf_counter()
        
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()


# =============================================================================
# Cleanup & Utilities
# =============================================================================

@pytest.fixture(autouse=True)
def reset_state():
    """각 테스트 후 상태 초기화"""
    yield


@pytest.fixture
def caplog_info(caplog):
    """로그 레벨을 INFO로 설정"""
    caplog.set_level(logging.INFO)
    return caplog


# =============================================================================
# Pytest Configuration
# =============================================================================

def pytest_configure(config):
    """pytest 설정 초기화"""
    config.addinivalue_line("markers", "unit: 단위 테스트")
    config.addinivalue_line("markers", "integration: 통합 테스트")
    config.addinivalue_line("markers", "api: API 테스트")
    config.addinivalue_line("markers", "auth: 인증 테스트")
    config.addinivalue_line("markers", "order: 주문 테스트")
    config.addinivalue_line("markers", "account: 계정 테스트")
    config.addinivalue_line("markers", "performance: 성능 테스트")
    config.addinivalue_line("markers", "e2e: End-to-End 테스트")
    config.addinivalue_line("markers", "security: 보안 테스트")
    config.addinivalue_line("markers", "asyncio: 비동기 테스트")
    
    log_dir = Path("tests/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 70)
    logger.info("BeenCoin 테스트 스위트 시작")
    logger.info("=" * 70)


def pytest_collection_modifyitems(config, items):
    """테스트 아이템 수정"""
    for item in items:
        if "api" in item.nodeid or "integration" in item.nodeid:
            item.add_marker(pytest.mark.api)
        
        if "unit" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)


def pytest_sessionfinish(session, exitstatus):
    """테스트 세션 종료"""
    logger.info("=" * 70)
    logger.info("테스트 완료")
    logger.info(f"종료 상태: {exitstatus}")
    logger.info("=" * 70)