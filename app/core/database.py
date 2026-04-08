from sqlmodel import create_engine, Session
from app.core.config import settings

# aiosqlite 드라이버 제거 → 동기 SQLite 사용
DATABASE_URL = settings.DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

def get_session():
    with Session(engine) as session:
        yield session
