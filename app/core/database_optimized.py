# ============================================
# app/core/database_optimized.py
# ============================================
"""
데이터베이스 성능 최적화
"""
from sqlalchemy.pool import QueuePool
from sqlmodel import create_engine

from app.core.config import settings

# Connection Pool 최적화
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,  # SQL 로깅 비활성화 (프로덕션)
    poolclass=QueuePool,
    pool_size=20,  # 기본 연결 수
    max_overflow=10,  # 추가 가능한 연결 수
    pool_timeout=30,  # 연결 대기 시간 (초)
    pool_recycle=3600,  # 연결 재활용 시간 (1시간)
    pool_pre_ping=True,  # 연결 상태 확인
    connect_args={
        "check_same_thread": False,  # SQLite용
        "timeout": 30,  # SQLite용
    }
    if "sqlite" in settings.DATABASE_URL
    else {},
)
