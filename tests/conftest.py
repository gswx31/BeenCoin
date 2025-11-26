# ============================================================================
# 파일: tests/conftest.py
# ============================================================================
# BeenCoin 테스트 Fixture - 로그 저장 기능 추가
# ============================================================================

"""
핵심 기능:
1. 공유 DB 엔진 (client와 db_session이 동일한 DB 사용)
2. 테스트 로그 파일 저장
3. 유효한 사용자명 생성 (영문+숫자만)
"""

import pytest
import sys
import os
import logging
import random
import string
from pathlib import Path
from typing import Generator, Callable
from datetime import datetime, timedelta

from sqlmodel import SQLModel, create_engine, Session, select
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.main import app
from app.models.database import User
from app.core.database import get_session
from app.utils.security import hash_password, create_access_token


# =============================================================================
# 로그 설정
# =============================================================================

def setup_logging():
    """테스트 로그 설정"""
    # 로그 디렉토리 생성
    log_dir = Path("tests/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 타임스탬프가 포함된 로그 파일명
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"test_{timestamp}.log"
    
    # 로그 포맷
    log_format = "%(asctime)s [%(levelname)8s] %(name)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # 파일 핸들러
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return log_file


# 로그 파일 경로 저장
LOG_FILE = setup_logging()
logger = logging.getLogger("tests.conftest")


# =============================================================================
# 헬퍼 함수
# =============================================================================

def generate_valid_username(prefix: str = "user") -> str:
    """
    유효한 사용자명 생성
    - 영문자 + 숫자만 허용 (특수문자 불가!)
    - 3~20자
    """
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{prefix}{suffix}"


# =============================================================================
# 데이터베이스 Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def shared_engine():
    """
    테스트용 인메모리 SQLite 엔진
    - 모든 fixture가 이 엔진을 공유
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    # 모든 모델 임포트 (테이블 생성 전 필수)
    from app.models.database import (
        User, TradingAccount, Order, Position,
        Transaction, PriceAlert
    )
    from app.models.futures import (
        FuturesAccount, FuturesPosition,
        FuturesOrder, FuturesTransaction
    )
    
    # 테이블 생성
    SQLModel.metadata.create_all(engine)
    logger.info("✅ 테스트 DB 초기화 완료")
    
    yield engine
    
    # 정리
    SQLModel.metadata.drop_all(engine)
    engine.dispose()
    logger.info("🗑️ 테스트 DB 정리 완료")


@pytest.fixture(scope="function")
def db_session(shared_engine) -> Generator[Session, None, None]:
    """DB 세션 - shared_engine 사용"""
    with Session(shared_engine) as session:
        yield session


@pytest.fixture(scope="function")
def client(shared_engine) -> Generator[TestClient, None, None]:
    """
    FastAPI TestClient - shared_engine 사용
    """
    def get_test_session():
        with Session(shared_engine) as session:
            yield session
    
    # 의존성 오버라이드
    app.dependency_overrides[get_session] = get_test_session
    
    with TestClient(app) as test_client:
        yield test_client
    
    # 정리
    app.dependency_overrides.clear()


# =============================================================================
# 사용자 Fixtures
# =============================================================================

@pytest.fixture
def user_factory(shared_engine) -> Callable:
    """
    사용자 생성 팩토리
    
    ⚠️ 주의: username은 영문+숫자만 허용 (언더스코어 불가!)
    """
    created_users = []
    
    def _create_user(
        username: str = None,
        password: str = "testpass123",
        is_active: bool = True,
        **kwargs
    ) -> User:
        # 유효한 username 생성
        if username is None:
            username = generate_valid_username("testuser")
        
        with Session(shared_engine) as session:
            # 기존 사용자 확인
            existing = session.exec(
                select(User).where(User.username == username)
            ).first()
            
            if existing:
                existing._test_password = password
                return existing
            
            # 새 사용자 생성
            user = User(
                username=username,
                hashed_password=hash_password(password),
                is_active=is_active,
                created_at=datetime.utcnow(),
                **kwargs
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            
            # 테스트용 원본 비밀번호 저장
            user._test_password = password
            created_users.append(user.id)
            
            logger.info(f"✅ 테스트 사용자 생성: {username} (ID: {user.id})")
            return user
    
    yield _create_user


@pytest.fixture
def test_user(user_factory) -> User:
    """기본 테스트 사용자 (유효한 username)"""
    return user_factory(username="testuser", password="testpass123")


# =============================================================================
# 인증 Fixtures
# =============================================================================

@pytest.fixture
def auth_token(test_user: User, client: TestClient) -> str:
    """JWT 토큰 생성 - 실제 로그인 API 호출"""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user.username,
            "password": test_user._test_password
        }
    )
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        logger.info(f"✅ 로그인 성공: {test_user.username}")
        return token
    else:
        # 폴백: 직접 토큰 생성
        logger.warning(f"⚠️ 로그인 실패 ({response.status_code}): {response.text}")
        logger.warning("   → 토큰 직접 생성으로 폴백")
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


@pytest.fixture
def expired_headers(expired_token: str) -> dict:
    """만료된 토큰 헤더"""
    return {"Authorization": f"Bearer {expired_token}"}


# =============================================================================
# 추가 헬퍼 Fixtures
# =============================================================================

@pytest.fixture
def random_username() -> str:
    """랜덤 사용자명 생성"""
    return generate_valid_username()


@pytest.fixture
def create_and_login(client: TestClient, user_factory):
    """사용자 생성 및 로그인 헬퍼"""
    def _create_and_login(username: str = None, password: str = "testpass123"):
        username = username or generate_valid_username()
        
        # 사용자 생성
        user_factory(username=username, password=password)
        
        # 로그인
        response = client.post(
            "/api/v1/auth/login",
            data={"username": username, "password": password}
        )
        
        if response.status_code != 200:
            raise Exception(f"로그인 실패: {response.status_code} - {response.text}")
        
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    return _create_and_login


# =============================================================================
# Pytest 설정
# =============================================================================

def pytest_configure(config):
    """pytest 설정"""
    config.addinivalue_line("markers", "unit: 단위 테스트")
    config.addinivalue_line("markers", "integration: 통합 테스트")
    config.addinivalue_line("markers", "api: API 테스트")
    config.addinivalue_line("markers", "e2e: End-to-End 테스트")
    config.addinivalue_line("markers", "slow: 느린 테스트")
    
    logger.info("=" * 70)
    logger.info("🧪 BeenCoin 테스트 시작")
    logger.info(f"📝 로그 파일: {LOG_FILE}")
    logger.info("=" * 70)


def pytest_sessionfinish(session, exitstatus):
    """테스트 세션 종료"""
    status_map = {0: "PASSED ✅", 1: "FAILED ❌", 2: "INTERRUPTED ⚠️"}
    status = status_map.get(exitstatus, f"UNKNOWN ({exitstatus})")
    
    logger.info("=" * 70)
    logger.info(f"🏁 테스트 완료: {status}")
    logger.info(f"📝 로그 파일: {LOG_FILE}")
    logger.info("=" * 70)


def pytest_runtest_logreport(report):
    """각 테스트 결과 로깅"""
    if report.when == "call":
        if report.passed:
            logger.debug(f"✅ PASSED: {report.nodeid}")
        elif report.failed:
            logger.error(f"❌ FAILED: {report.nodeid}")
            if report.longrepr:
                logger.error(f"   Error: {report.longrepr}")
        elif report.skipped:
            logger.info(f"⏭️ SKIPPED: {report.nodeid}")
