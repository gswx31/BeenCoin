from app.background_tasks.celery_app import celery_app
from app.core.database import engine
from sqlmodel import Session, select
from app.models.database import TradingAccount, Position
from app.services.binance_service import get_current_price
import asyncio

@celery_app.task
def update_all_positions():
    with Session(engine) as session:
        accounts = session.exec(select(TradingAccount)).all()
        for account in accounts:
            positions = session.exec(
                select(Position).where(Position.account_id == account.id)
            ).all()
            for pos in positions:
                if pos.quantity > 0:
                    try:
                        current_price = asyncio.run(get_current_price(pos.symbol))
                        pos.current_value = pos.quantity * current_price
                        pos.unrealized_profit = pos.quantity * (current_price - pos.average_price)
                        session.add(pos)
                    except Exception as e:
                        print(f"Failed to update {pos.symbol}: {e}")
        session.commit()
