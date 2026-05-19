"""
공통 픽스처: 테스트용 DB, FastAPI TestClient, 인증된 사용자.
"""
import os
import pytest
import asyncio
from decimal import Decimal
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Test 환경변수 설정 (모듈 import 전에)
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-only-for-testing"
os.environ["AUTO_CREATE_TABLES"] = "false"
os.environ["RATELIMIT_ENABLED"] = "false"

# Rate limiter 비활성화 (import 전에)
from app.core.rate_limit import limiter
limiter.enabled = False

from app.main import app
from app.core import database as db_module
from app.models.database import User, TradingAccount


@pytest.fixture(scope="function")
def engine():
    """각 테스트마다 새로운 in-memory SQLite engine."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture(scope="function")
def session(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture(scope="function")
def client(engine, monkeypatch):
    """FastAPI 클라이언트 - 동일한 in-memory DB를 공유."""
    # PriceEngine을 mock (Binance 연결 차단)
    from app.services import price_engine as pe_module

    async def noop():
        pass

    monkeypatch.setattr(pe_module.price_engine, "start", noop)
    monkeypatch.setattr(pe_module.price_engine, "stop", noop)

    # 앱이 사용하는 engine을 테스트 engine으로 교체
    monkeypatch.setattr(db_module, "engine", engine)

    def override_get_session():
        with Session(engine) as s:
            yield s

    from app.core.database import get_session
    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def user_token(client):
    """등록 + 로그인한 사용자의 액세스 토큰."""
    client.post("/api/v1/auth/register", json={"username": "tester", "password": "password123"})
    res = client.post("/api/v1/auth/login", json={"username": "tester", "password": "password123"})
    return res.json()["access_token"]


@pytest.fixture
def user_tokens(client):
    """access + refresh 토큰 둘 다 반환."""
    client.post("/api/v1/auth/register", json={"username": "tester2", "password": "password123"})
    res = client.post("/api/v1/auth/login", json={"username": "tester2", "password": "password123"})
    return res.json()


@pytest.fixture
def auth_headers(user_token):
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture(autouse=True)
def mock_binance(monkeypatch):
    """모든 테스트에서 Binance API 호출을 mock."""
    async def mock_get_price(symbol):
        prices = {"BTCUSDT": Decimal("50000"), "ETHUSDT": Decimal("3000"), "BNBUSDT": Decimal("500")}
        return prices.get(symbol, Decimal("100"))

    from app.services import binance_service, order_service
    from app.services import price_engine as pe

    monkeypatch.setattr(binance_service, "get_current_price", mock_get_price)
    monkeypatch.setattr(order_service, "get_current_price", mock_get_price)

    # price_engine 캐시에도 미리 값 채워두기
    pe.price_engine._latest_prices = {
        "BTCUSDT": Decimal("50000"),
        "ETHUSDT": Decimal("3000"),
        "BNBUSDT": Decimal("500"),
    }
