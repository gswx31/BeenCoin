# app/tasks/scheduler.py
"""
Background task scheduler
"""
import asyncio
import logging
from sqlmodel import Session
from app.core.database import engine
from app.services.order_service import order_service
from app.services.stop_loss_take_profit_service import (
    check_stop_loss_take_profit_orders,
    check_futures_stop_loss_take_profit
)
from app.routers.alerts import check_price_alerts
from app.services.futures_service import futures_service

logger = logging.getLogger(__name__)


async def check_pending_orders(session: Session):
    """Check and execute pending limit orders"""
    try:
        await order_service.check_pending_orders(session)
    except Exception as e:
        logger.error(f"Error checking pending orders: {e}")


async def update_positions_pnl(session: Session):
    """Update positions PnL with current prices"""
    try:
        from app.models.database import Position, PositionStatus
        from app.services.binance_service import get_current_price
        from sqlmodel import select
        from decimal import Decimal
        
        positions = session.exec(
            select(Position).where(Position.position_status == PositionStatus.OPEN)
        ).all()
        
        for position in positions:
            try:
                current_price = await get_current_price(position.symbol)
                position.current_price = Decimal(str(current_price))
                position.unrealized_pnl = (position.current_price - position.average_price) * position.quantity
            except Exception as e:
                logger.error(f"Error updating position {position.id}: {e}")
        
        session.commit()
        
    except Exception as e:
        logger.error(f"Error updating positions PnL: {e}")


async def check_liquidations(session: Session):
    """Check for futures position liquidations"""
    try:
        from app.models.futures import FuturesPosition, FuturesPositionStatus, FuturesPositionSide
        from app.services.binance_service import get_current_price
        from sqlmodel import select
        from decimal import Decimal
        
        positions = session.exec(
            select(FuturesPosition).where(FuturesPosition.status == FuturesPositionStatus.OPEN)
        ).all()
        
        for position in positions:
            try:
                current_price = await get_current_price(position.symbol)
                current_price = Decimal(str(current_price))
                
                # Simple liquidation check (can be more sophisticated)
                should_liquidate = False
                
                if position.side == FuturesPositionSide.LONG:
                    # Long liquidation: price drops below (entry - margin/leverage)
                    liquidation_price = position.entry_price * Decimal("0.9")  # Simplified
                    if current_price <= liquidation_price:
                        should_liquidate = True
                else:
                    # Short liquidation: price rises above (entry + margin/leverage)
                    liquidation_price = position.entry_price * Decimal("1.1")  # Simplified
                    if current_price >= liquidation_price:
                        should_liquidate = True
                
                if should_liquidate:
                    position.status = FuturesPositionStatus.LIQUIDATED
                    position.mark_price = current_price
                    position.realized_pnl = -position.margin  # Lost entire margin
                    logger.warning(f"Position liquidated: {position.id}")
                    
            except Exception as e:
                logger.error(f"Error checking liquidation for position {position.id}: {e}")
        
        session.commit()
        
    except Exception as e:
        logger.error(f"Error checking liquidations: {e}")


async def run_background_tasks():
    """
    Main background task runner
    
    Runs every 5 seconds:
    - Check pending orders
    - Check stop loss/take profit
    - Check price alerts
    - Update positions PnL
    - Check liquidations
    """
    logger.info("🚀 Background tasks started")
    
    while True:
        try:
            with Session(engine) as session:
                # Run all background tasks
                tasks = [
                    check_pending_orders(session),
                    check_stop_loss_take_profit_orders(session),
                    check_futures_stop_loss_take_profit(session),
                    check_price_alerts(session),
                    update_positions_pnl(session),
                    check_liquidations(session)
                ]
                
                # Run tasks concurrently
                await asyncio.gather(*tasks, return_exceptions=True)
            
            # Wait before next iteration
            await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"Background task error: {e}")
            await asyncio.sleep(5)


def start_background_tasks():
    """Start background tasks (called from main app)"""
    asyncio.create_task(run_background_tasks())
    logger.info("✅ Background scheduler registered")