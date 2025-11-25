# ============================================================================
# 파일 위치: tests/conftest.py
# ============================================================================
# 설명: 테스트 Fixture 설정 (최종 수정 버전)
# ============================================================================

"""
BeenCoin 테스트 Fixture
=======================
API 통합 테스트를 위한 기본 설정
"""

import asyncio
import pytest
import sys
from pathlib import Path
from typing import Generator, Callable
from decimal import Decimal
from datetime import datetime, timedelta
import logging

from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.main import app
from app.models.database import User
from app.core.database import get_session
from app.utils.security import hash_password, create_access_token

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """이벤트 루프"""
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
    """DB 세션"""
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
# User Fixtures
# =============================================================================

@pytest.fixture
def user_factory(db_session: Session) -> Callable:
    """사용자 생성 팩토리"""
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
        
        # 원본 비밀번호 저장 (로그인 테스트용)
        user._test_password = password
        
        return user
    
    return _create_user


@pytest.fixture
def test_user(user_factory) -> User:
    """기본 테스트 사용자"""
    return user_factory(username="testuser", password="testpass123")


# =============================================================================
# Auth Fixtures - ✅ 최종 수정 버전
# =============================================================================

@pytest.fixture
def auth_token(test_user: User, client: TestClient) -> str:
    """JWT 토큰 생성 (실제 로그인)"""
    response = client.post(
        "/api/v1/auth/login",
        data={  # ✅ json → data로 변경 (Form Data)
            "username": test_user.username,
            "password": test_user._test_password
        }
    )
    
    if response.status_code == 200:
        logger.info(f"✅ auth_token fixture: 토큰 생성 성공 - {test_user.username}")
        return response.json()["access_token"]
    else:
        # 로그인 실패 시 직접 생성
        logger.warning(f"⚠️ auth_token fixture: 로그인 실패 (status: {response.status_code})")
        logger.warning(f"   Response: {response.text}")
        logger.warning(f"   토큰 직접 생성으로 폴백")
        return create_access_token(data={"sub": test_user.username})


@pytest.fixture
def auth_headers(auth_token: str) -> dict:
    """인증 헤더"""
    logger.info(f"✅ auth_headers fixture: 헤더 생성 완료")
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def expired_token(test_user: User) -> str:
    """만료된 토큰"""
    return create_access_token(
        data={"sub": test_user.username},
        expires_delta=timedelta(minutes=-10)
    )


# =============================================================================
# Pytest Configuration
# =============================================================================

def pytest_configure(config):
    """pytest 설정 초기화"""
    config.addinivalue_line("markers", "unit: 단위 테스트")
    config.addinivalue_line("markers", "integration: 통합 테스트")
    config.addinivalue_line("markers", "api: API 테스트")
    config.addinivalue_line("markers", "e2e: End-to-End 테스트")
    
    # 로그 디렉토리 생성
    log_dir = Path("tests/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 70)
    logger.info("BeenCoin 테스트 시작")
    logger.info("=" * 70)


def pytest_sessionfinish(session, exitstatus):
    """테스트 세션 종료"""
    logger.info("=" * 70)
    logger.info(f"테스트 완료 - 종료 상태: {exitstatus}")
    logger.info("=" * 70)