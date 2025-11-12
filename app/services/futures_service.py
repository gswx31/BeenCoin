# app/services/futures_service.py
"""
Futures trading service
"""
from sqlmodel import Session, select
from typing import List, Optional
from decimal import Decimal
from datetime import datetime
import logging

from app.models.futures import (
    FuturesAccount, FuturesPosition, FuturesOrder,
    FuturesOrderType, FuturesPositionSide, FuturesPositionStatus
)
from app.services.binance_service import get_current_price
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

class FuturesService:
    """Futures trading management service"""
    
    @staticmethod
    async def open_position(
        session: Session,
        user_id: int,
        symbol: str,
        side: FuturesPositionSide,
        quantity: Decimal,
        leverage: int = 1
    ) -> FuturesPosition:
        """Open a futures position"""
        
        # Get or create futures account
        account = session.exec(
            select(FuturesAccount).where(FuturesAccount.user_id == user_id)
        ).first()
        
        if not account:
            account = FuturesAccount(user_id=user_id)
            session.add(account)
            session.commit()
        
        # Get current price
        current_price = await get_current_price(symbol)
        
        # Calculate required margin
        position_value = quantity * Decimal(str(current_price))
        required_margin = position_value / leverage
        
        # Check balance
        if account.usdt_balance < required_margin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient margin. Required: {required_margin}, Available: {account.usdt_balance}"
            )
        
        # Create position
        position = FuturesPosition(
            user_id=user_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_price=Decimal(str(current_price)),
            mark_price=Decimal(str(current_price)),
            leverage=leverage,
            margin=required_margin,
            status=FuturesPositionStatus.OPEN
        )
        
        # Update account
        account.usdt_balance -= required_margin
        account.margin_balance += required_margin
        
        session.add(position)
        session.commit()
        session.refresh(position)
        
        return position
    
    @staticmethod
    async def close_position(
        session: Session,
        user_id: int,
        position_id: int
    ) -> FuturesPosition:
        """Close a futures position"""
        
        position = session.exec(
            select(FuturesPosition).where(
                FuturesPosition.id == position_id,
                FuturesPosition.user_id == user_id
            )
        ).first()
        
        if not position:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Position not found"
            )
        
        if position.status != FuturesPositionStatus.OPEN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot close position with status: {position.status.value}"
            )
        
        # Get current price
        current_price = await get_current_price(position.symbol)
        
        # Calculate PnL
        if position.side == FuturesPositionSide.LONG:
            pnl = (Decimal(str(current_price)) - position.entry_price) * position.quantity
        else:  # SHORT
            pnl = (position.entry_price - Decimal(str(current_price))) * position.quantity
        
        # Update position
        position.mark_price = Decimal(str(current_price))
        position.realized_pnl = pnl
        position.status = FuturesPositionStatus.CLOSED
        position.updated_at = datetime.utcnow()
        
        # Update account
        account = session.exec(
            select(FuturesAccount).where(FuturesAccount.user_id == user_id)
        ).first()
        
        account.usdt_balance += position.margin + pnl
        account.margin_balance -= position.margin
        account.realized_pnl += pnl
        
        session.commit()
        session.refresh(position)
        
        return position
    
    @staticmethod
    async def update_position_mark_price(
        session: Session,
        position_id: int
    ):
        """Update position mark price and unrealized PnL"""
        
        position = session.exec(
            select(FuturesPosition).where(
                FuturesPosition.id == position_id,
                FuturesPosition.status == FuturesPositionStatus.OPEN
            )
        ).first()
        
        if not position:
            return
        
        # Get current price
        current_price = await get_current_price(position.symbol)
        
        # Update mark price
        position.mark_price = Decimal(str(current_price))
        
        # Calculate unrealized PnL
        if position.side == FuturesPositionSide.LONG:
            position.unrealized_pnl = (position.mark_price - position.entry_price) * position.quantity
        else:  # SHORT
            position.unrealized_pnl = (position.entry_price - position.mark_price) * position.quantity
        
        # Calculate liquidation price (simplified)
        if position.side == FuturesPositionSide.LONG:
            position.liquidation_price = position.entry_price * Decimal("0.8")
        else:
            position.liquidation_price = position.entry_price * Decimal("1.2")
        
        position.updated_at = datetime.utcnow()
        session.commit()
    
    @staticmethod
    async def check_futures_stop_loss_take_profit(session: Session):
        """Check and execute futures stop loss and take profit orders"""
        
        open_positions = session.exec(
            select(FuturesPosition).where(
                FuturesPosition.status == FuturesPositionStatus.OPEN
            )
        ).all()
        
        for position in open_positions:
            try:
                current_price = await get_current_price(position.symbol)
                
                # Check stop loss
                if position.stop_loss:
                    if position.side == FuturesPositionSide.LONG:
                        if current_price <= float(position.stop_loss):
                            await FuturesService.close_position(
                                session, position.user_id, position.id
                            )
                            logger.info(f"Stop loss triggered for position {position.id}")
                            continue
                    else:  # SHORT
                        if current_price >= float(position.stop_loss):
                            await FuturesService.close_position(
                                session, position.user_id, position.id
                            )
                            logger.info(f"Stop loss triggered for position {position.id}")
                            continue
                
                # Check take profit
                if position.take_profit:
                    if position.side == FuturesPositionSide.LONG:
                        if current_price >= float(position.take_profit):
                            await FuturesService.close_position(
                                session, position.user_id, position.id
                            )
                            logger.info(f"Take profit triggered for position {position.id}")
                    else:  # SHORT
                        if current_price <= float(position.take_profit):
                            await FuturesService.close_position(
                                session, position.user_id, position.id
                            )
                            logger.info(f"Take profit triggered for position {position.id}")
            
            except Exception as e:
                logger.error(f"Failed to check position {position.id}: {e}")
                continue

# Create singleton instance
futures_service = FuturesService()