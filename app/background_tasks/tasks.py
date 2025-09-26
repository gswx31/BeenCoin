from app.background_tasks.celery_app import celery_app
from app.services.order_service import update_position
from app.core.database import engine
from sqlmodel import Session, select
from app.models.database import User, Position
from app.services.binance_service import get_current_price
import asyncio

@celery_app.task
def update_all_positions():
    with Session(engine) as session:
        users = session.exec(select(User)).all()
        for user in users:
            positions = session.exec(select(Position).where(Position.account_id == user.accounts[0].id if user.accounts else None)).all()
            for pos in positions:
                if pos.quantity > 0:
                    current_price = asyncio.run(get_current_price(pos.symbol))
                    pos.current_value = pos.quantity * current_price
                    pos.unrealized_profit = pos.quantity * (current_price - pos.average_price)
                    session.add(pos)
        session.commit()
