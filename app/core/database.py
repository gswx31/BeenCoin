# app/core/database.py - 개선 버전
from sqlmodel import create_engine, Session
from app.core.config import settings

# SQLite URL 정규화 (aiosqlite -> sqlite)
db_url = settings.DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite:///")

print(f"📊 Database URL: {db_url}")

# 동기 엔진 생성
engine = create_engine(
    db_url,
    echo=False,  # 프로덕션에서는 False
    connect_args={"check_same_thread": False}  # SQLite 전용
)

def get_session():
    """의존성 주입용 세션 생성기"""
    with Session(engine) as session:
        try:
            yield session
        except Exception as e:
            print(f"❌ Database error: {e}")
            session.rollback()
            raise
        finally:
            session.close()


# app/models/database.py 수정
from sqlmodel import SQLModel
from app.core.database import engine

def create_db_and_tables():
    """데이터베이스 및 테이블 생성"""
    print("📝 Creating database tables...")
    SQLModel.metadata.create_all(engine)
    print("✅ Database tables created successfully!")