"""

주요 개선사항:
1. Factory Fixtures - 동적 객체 생성
2. Parameterized Fixtures - 다양한 시나리오 테스트
3. Async Support - 비동기 테스트 완전 지원
4. Dependency Injection - 깔끔한 의존성 관리
5. Scope 최적화 - 성능 향상
"""
import asyncio
import pytest
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator, Callable
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
import logging

from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.main import app
from app.models.database import User, TradingAccount, Position, Order, Transaction
from app.core.database import get_session
from app.utils.security import hash_password, create_access_token

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Database Fixtures - 데이터베이스 관련
# =============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """이벤트 루프 - 세션 레벨"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def test_engine():
    """
    테스트용 인메모리 DB 엔진
    - 각 테스트마다 깨끗한 DB
    - StaticPool로 멀티스레드 안전
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False  # 디버그시 True로 변경
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """
    DB 세션 - 트랜잭션 롤백 지원
    각 테스트 후 자동 롤백으로 격리 보장
    """
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
# Client Fixtures - API 클라이언트
# =============================================================================

@pytest.fixture(scope="function")
def client(test_engine) -> Generator[TestClient, None, None]:
    """
    FastAPI TestClient
    - 의존성 오버라이드
    - 자동 세션 관리
    """
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
# User Fixtures - 사용자 관련
# =============================================================================

@pytest.fixture
def user_factory(db_session: Session) -> Callable:
    """
    사용자 팩토리 - 동적 생성
    
    Usage:
        user1 = user_factory(username="user1")
        user2 = user_factory(username="user2", is_active=False)
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
            **kwargs
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    
    return _create_user


@pytest.fixture
def test_user(user_factory) -> User:
    """기본 테스트 사용자"""
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
    """
    파라미터화된 사용자 fixture
    - active/inactive 사용자 모두 테스트
    """
    if request.param == "active_user":
        return user_factory(username="active", is_active=True)
    else:
        return user_factory(username="inactive", is_active=False)


# =============================================================================
# Account Fixtures - 거래 계정
# =============================================================================

@pytest.fixture
def account_factory(db_session: Session) -> Callable:
    """
    거래 계정 팩토리
    
    Usage:
        account = account_factory(user=user, balance=1000000)
    """
    def _create_account(
        user: User,
        balance: Decimal = Decimal("1000000"),
        total_profit: Decimal = Decimal("0"),
        **kwargs
    ) -> TradingAccount:
        account = TradingAccount(
            user_id=user.id,
            balance=balance,
            total_profit=total_profit,
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
    Decimal("1000000"),    # 기본
    Decimal("100000"),     # 낮은 잔액
    Decimal("10000000"),   # 높은 잔액
])
def varied_balance_account(request, test_user: User, account_factory) -> TradingAccount:
    """다양한 잔액의 계정"""
    return account_factory(user=test_user, balance=request.param)


# =============================================================================
# Order Fixtures - 주문 관련
# =============================================================================

@pytest.fixture
def order_factory(db_session: Session) -> Callable:
    """
    주문 팩토리
    
    Usage:
        order = order_factory(user=user, symbol="BTCUSDT", side="BUY")
    """
    def _create_order(
        user: User,
        symbol: str = "BTCUSDT",
        side: str = "BUY",
        order_type: str = "MARKET",
        price: Decimal = Decimal("50000"),
        quantity: Decimal = Decimal("0.1"),
        order_status: str = "PENDING",
        **kwargs
    ) -> Order:
        order = Order(
            user_id=user.id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            price=price,
            quantity=quantity,
            filled_quantity=Decimal("0"),
            order_status=order_status,
            **kwargs
        )
        db_session.add(order)
        db_session.commit()
        db_session.refresh(order)
        return order
    
    return _create_order


@pytest.fixture
def test_order(test_user: User, order_factory) -> Order:
    """기본 테스트 주문"""
    return order_factory(user=test_user)


# =============================================================================
# Position Fixtures - 포지션
# =============================================================================

@pytest.fixture
def position_factory(db_session: Session) -> Callable:
    """포지션 팩토리"""
    def _create_position(
        account: TradingAccount,
        symbol: str = "BTCUSDT",
        quantity: Decimal = Decimal("1.0"),
        average_price: Decimal = Decimal("50000"),
        **kwargs
    ) -> Position:
        position = Position(
            account_id=account.id,
            symbol=symbol,
            quantity=quantity,
            average_price=average_price,
            current_value=quantity * average_price,
            unrealized_profit=Decimal("0"),
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


# =============================================================================
# Authentication Fixtures - 인증
# =============================================================================

@pytest.fixture
def auth_token(test_user: User) -> str:
    """JWT 토큰 생성"""
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
# Mock Fixtures - 외부 서비스 Mocking
# =============================================================================

@pytest.fixture
def mock_binance_service():
    """
    Binance Service Mock
    - 실제 API 호출 없이 테스트
    """
    with pytest.MonkeyPatch.context() as m:
        mock = MagicMock()
        mock.get_current_price.return_value = Decimal("50000")
        mock.get_coin_info.return_value = {
            "symbol": "BTCUSDT",
            "price": "50000.00",
            "change_24h": "2.5"
        }
        m.setattr("app.services.binance_service", mock)
        yield mock


@pytest.fixture
def mock_async_binance():
    """비동기 Binance Mock"""
    mock = AsyncMock()
    mock.get_current_price = AsyncMock(return_value=Decimal("50000"))
    mock.get_historical_data = AsyncMock(return_value=[])
    return mock


# =============================================================================
# Test Data Fixtures - 테스트 데이터
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
def sample_order_data() -> dict:
    """샘플 주문 데이터"""
    return {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "order_type": "MARKET",
        "quantity": "0.1"
    }


# =============================================================================
# Performance Fixtures - 성능 테스트
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
    # 필요시 글로벌 상태 초기화


@pytest.fixture
def caplog_info(caplog):
    """로그 레벨을 INFO로 설정"""
    caplog.set_level(logging.INFO)
    return caplog


def pytest_configure(config):
    """pytest 설정 초기화"""
    # 로그 디렉토리 생성
    log_dir = Path("tests/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 70)
    logger.info("BeenCoin 테스트 스위트 시작")
    logger.info("=" * 70)


def pytest_collection_modifyitems(config, items):
    """
    테스트 아이템 수정
    - 마커 자동 추가
    - 실행 순서 최적화
    """
    for item in items:
        # API 테스트 마커 자동 추가
        if "api" in item.nodeid:
            item.add_marker(pytest.mark.api)
        
        # 단위 테스트 마커
        if "unit" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        
        # 통합 테스트 마커
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)


def pytest_sessionfinish(session, exitstatus):
    """테스트 세션 종료"""
    logger.info("=" * 70)
    logger.info("테스트 완료")
    logger.info(f"종료 상태: {exitstatus}")
    logger.info("=" * 70)