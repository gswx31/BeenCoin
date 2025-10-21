from sqlmodel import create_engine, Session, SQLModel
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# 성능 최적화: 커넥션 풀 설정
connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=settings.DB_POOL_PRE_PING,
    connect_args=connect_args
)

def get_session():
    """데이터베이스 세션 제공 (의존성 주입용)"""
    with Session(engine) as session:
        yield session

def create_db_and_tables():
    """데이터베이스 초기화 - 테이블 생성"""
    try:
        SQLModel.metadata.create_all(engine)
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Database creation failed: {e}")
        raise

def drop_all_tables():
    """모든 테이블 삭제 (디버깅용)"""
    try:
        SQLModel.metadata.drop_all(engine)
        logger.info("✅ All tables dropped")
    except Exception as e:
        logger.error(f"❌ Table drop failed: {e}")