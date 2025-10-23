import pytest
from sqlmodel import Session, create_engine, SQLModel

@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:", echo=True)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
