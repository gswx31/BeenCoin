# ============================================================================
# 파일: tests/conftest.py
# ============================================================================
# pytest 전역 설정 및 fixtures
# ============================================================================

import os
import sys
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from decimal import Decimal
import random
import string

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# 환경 설정
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """테스트 환경 설정"""
    # CI 환경 및 Mock Binance 설정
    os.environ["CI"] = "true"
    os.environ["MOCK_BINANCE"] = "true"
    os.environ["DATABASE_URL"] = "sqlite:///./test.db"
    os.environ["SECRET_KEY"] = "test-secret-key-for-testing-purposes-only-very-long"
    os.environ["DEBUG"] = "true"
    os.environ["ENVIRONMENT"] = "test"
    
    yield
    
    # 테스트 후 정리
    if os.path.exists("test.db"):
        os.remove("test.db")


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def mock_session():
    """Mock 데이터베이스 세션"""
    session = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    session.refresh = MagicMock()
    session.add = MagicMock()
    session.add_all = MagicMock()
    session.flush = MagicMock()
    return session


@pytest.fixture
def db_session():
    """실제 테스트 데이터베이스 세션"""
    from app.core.database import engine, get_session
    from sqlmodel import Session, SQLModel
    
    # 테이블 생성
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        yield session
        session.rollback()


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
def test_user_data():
    """테스트 사용자 데이터"""
    suffix = ''.join(random.choices(string.ascii_lowercase, k=8))
    return {
        "username": f"testuser_{suffix}",
        "email": f"test_{suffix}@example.com",
        "password": "TestPassword123!"
    }


@pytest.fixture
def mock_user():
    """Mock 사용자 객체"""
    from uuid import uuid4
    
    user = MagicMock()
    user.id = str(uuid4())
    user.username = "testuser"
    user.email = "test@example.com"
    user.hashed_password = "hashed_password"
    user.is_active = True
    user.created_at = None
    return user


@pytest.fixture
def auth_token(test_user_data):
    """인증 토큰 생성"""
    from app.utils.security import create_access_token
    
    return create_access_token(data={"sub": test_user_data["username"]})


# ============================================================================
# Futures Fixtures
# ============================================================================

@pytest.fixture
def mock_futures_account():
    """Mock 선물 계정"""
    from uuid import uuid4
    
    account = MagicMock()
    account.id = str(uuid4())
    account.user_id = str(uuid4())
    account.balance = Decimal("100000")
    account.margin_used = Decimal("0")
    account.unrealized_pnl = Decimal("0")
    account.total_profit = Decimal("0")
    account.total_balance = Decimal("100000")
    account.available_balance = Decimal("100000")
    account.margin_ratio = Decimal("0")
    return account


@pytest.fixture
def mock_futures_position():
    """Mock 선물 포지션"""
    from uuid import uuid4
    from app.models.futures import FuturesPositionSide, FuturesPositionStatus
    from datetime import datetime
    
    position = MagicMock()
    position.id = str(uuid4())
    position.account_id = str(uuid4())
    position.symbol = "BTCUSDT"
    position.side = FuturesPositionSide.LONG
    position.status = FuturesPositionStatus.OPEN
    position.quantity = Decimal("0.1")
    position.entry_price = Decimal("50000")
    position.mark_price = Decimal("51000")
    position.liquidation_price = Decimal("45000")
    position.margin = Decimal("500")
    position.leverage = 10
    position.unrealized_pnl = Decimal("100")
    position.realized_pnl = Decimal("0")
    position.roe_percent = Decimal("20")
    position.position_value = Decimal("5100")
    position.fee = Decimal("0.5")
    position.opened_at = datetime.utcnow()
    position.closed_at = None
    return position


# ============================================================================
# Binance Service Mocks
# ============================================================================

@pytest.fixture
def mock_binance_price():
    """Binance 가격 조회 Mock"""
    with patch('app.services.binance_service.get_current_price',
               new_callable=AsyncMock) as mock:
        mock.return_value = Decimal("50000")
        yield mock


@pytest.fixture
def mock_binance_trades():
    """Binance 체결 내역 Mock"""
    with patch('app.services.binance_service.get_recent_trades',
               new_callable=AsyncMock) as mock:
        mock.return_value = [
            {
                "id": 1,
                "price": Decimal("50000"),
                "qty": Decimal("0.01"),
                "time": 1234567890000,
                "isBuyerMaker": False
            }
        ]
        yield mock


@pytest.fixture
def mock_binance_order_book():
    """Binance 호가창 Mock"""
    with patch('app.services.binance_service.get_order_book',
               new_callable=AsyncMock) as mock:
        mock.return_value = {
            "bids": [[Decimal("49900"), Decimal("1.0")]],
            "asks": [[Decimal("50100"), Decimal("1.0")]]
        }
        yield mock


@pytest.fixture
def mock_market_order():
    """시장가 주문 Mock"""
    with patch('app.services.binance_service.execute_market_order_with_real_trades',
               new_callable=AsyncMock) as mock:
        mock.return_value = {
            "average_price": Decimal("50000"),
            "total_quantity": Decimal("0.1"),
            "fills": [
                {
                    "price": "50000",
                    "quantity": "0.1",
                    "timestamp": "2024-01-01T00:00:00"
                }
            ]
        }
        yield mock


# ============================================================================
# HTTP Client Fixtures
# ============================================================================

@pytest.fixture
def client():
    """FastAPI 테스트 클라이언트"""
    from fastapi.testclient import TestClient
    from app.main import app
    
    with TestClient(app) as c:
        yield c


@pytest.fixture
def async_client():
    """비동기 테스트 클라이언트"""
    import httpx
    from app.main import app
    
    return httpx.AsyncClient(app=app, base_url="http://test")


# ============================================================================
# Helper Functions
# ============================================================================

def generate_random_string(length: int = 8) -> str:
    """랜덤 문자열 생성"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def generate_valid_password() -> str:
    """유효한 비밀번호 생성"""
    return f"Test{generate_random_string(4)}123!"


# ============================================================================
# Markers
# ============================================================================

def pytest_configure(config):
    """pytest 마커 설정"""
    config.addinivalue_line("markers", "unit: 단위 테스트")
    config.addinivalue_line("markers", "integration: 통합 테스트")
    config.addinivalue_line("markers", "slow: 느린 테스트")
    config.addinivalue_line("markers", "api: API 테스트")
    config.addinivalue_line("markers", "db: 데이터베이스 테스트")


# ============================================================================
# Async Support
# ============================================================================

@pytest.fixture
def event_loop():
    """이벤트 루프 생성"""
    import asyncio
    
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()