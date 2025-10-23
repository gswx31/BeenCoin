import pytest
from sqlmodel import SQLModel, create_engine, Session
from app.models import database as db

@pytest.fixture(scope="function")
def session():
    # 인메모리 SQLite 사용 (테스트 후 자동 삭제됨)
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
