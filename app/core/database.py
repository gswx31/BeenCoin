# app/core/database.py
from sqlmodel import create_engine, Session
from app.core.config import settings

# SQLite URL 정규화
db_url = settings.DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite:///")

print(f"📊 Database URL: {db_url}")

# 엔진 생성 (check_same_thread=False for SQLite)
engine = create_engine(
    db_url, 
    echo=True,  # SQL 쿼리 로깅
    connect_args={"check_same_thread": False}  # SQLite용 설정
)

def get_session():
    """데이터베이스 세션 생성"""
    with Session(engine) as session:
        try:
            yield session
        except Exception as e:
            print(f"❌ Database session error: {e}")
            session.rollback()
            raise
        finally:
            session.close()