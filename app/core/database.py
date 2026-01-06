# app/core/database.py
"""
데이터베이스 연결 및 초기화 - 선물 테이블 포함
"""
import logging

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

logger = logging.getLogger(__name__)

# 데이터베이스 엔진
engine = create_engine(settings.DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

def create_db_and_tables():
    """
    데이터베이스 및 테이블 생성
    - 현물 거래 테이블
    - 선물 거래 테이블
    """

    # ✅ 모든 모델 임포트 (테이블 생성 전에 필수!)

    logger.info("📊 데이터베이스 초기화 중...")

    # 모든 테이블 생성
    SQLModel.metadata.create_all(engine)

    logger.info("✅ 데이터베이스 초기화 완료!")
    logger.info("  - 현물 거래 테이블 생성 완료")
    logger.info("  - 선물 거래 테이블 생성 완료")

def get_session():
    """데이터베이스 세션 의존성"""
    with Session(engine) as session:
        yield session
