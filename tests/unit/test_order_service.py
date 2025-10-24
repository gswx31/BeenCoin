import pytest
from decimal import Decimal
from app.services.order_service import update_position
from app.models.database import TradingAccount, Position
from sqlmodel import Session, create_engine
from sqlalchemy.pool import StaticPool

@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    from app.models.database import SQLModel
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_update_position_buy(session: Session):
    account = TradingAccount(id=1, user_id=1, balance=Decimal('1000000'))
    session.add(account)
    session.commit()
    update_position(session, 1, "BTCUSDT", "BUY", Decimal('1'), Decimal('50000'), Decimal('50'))
    position = session.exec(Position.select().where(Position.symbol == "BTCUSDT")).first()
    assert position.quantity == Decimal('1')
    assert account.balance == Decimal('999950')
