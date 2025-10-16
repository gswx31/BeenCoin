import pytest
from decimal import Decimal
from app.services.order_service import update_position
from app.models.database import SpotAccount, SpotPosition
from sqlmodel import Session, create_engine
from sqlalchemy.pool import StaticPool

@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    from app.models.database import SQLModel
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

