# app/services/order_service.py
"""
Order service for handling trading operations
"""
from sqlmodel import Session, select
from typing import List, Optional
from decimal import Decimal
from datetime import datetime
import logging

from app.models.database import (
    Order, OrderType, OrderSide, OrderStatus,
    TradingAccount, Position, Transaction, PositionStatus
)
from app.schemas.order import OrderCreate
from app.core.config import settings
from app.services.binance_service import get_current_price
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

class OrderService:
    """Order management service"""
    
    @staticmethod
    async def create_order(
        session: Session, 
        user_id: int, 
        order_data: OrderCreate
    ) -> Order:
        """
        Create a new order
        
        Args:
            session: Database session
            user_id: User ID
            order_data: Order creation data
        
        Returns:
            Order: Created order
        
        Raises:
            HTTPException: If validation fails
        """
        # Validate symbol
        if order_data.symbol not in settings.SUPPORTED_SYMBOLS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported symbol: {order_data.symbol}"
            )
        
        # Get trading account
        account = session.exec(
            select(TradingAccount).where(TradingAccount.user_id == user_id)
        ).first()
        
        if not account:
            # Create account if not exists
            account = TradingAccount(user_id=user_id)
            session.add(account)
            session.commit()
        
        # Validate balance for buy orders (except STOP_LOSS and TAKE_PROFIT)
        if order_data.order_side == OrderSide.BUY and order_data.order_type not in [OrderType.STOP_LOSS, OrderType.TAKE_PROFIT]:
            required_balance = await OrderService._calculate_required_balance(
                order_data, session
            )
            
            if account.balance < required_balance:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient balance. Required: {required_balance}, Available: {account.balance}"
                )
        
        # Validate quantity for sell orders (including STOP_LOSS)
        if order_data.order_side == OrderSide.SELL or order_data.order_type in [OrderType.STOP_LOSS, OrderType.TAKE_PROFIT]:
            position = session.exec(
                select(Position).where(
                    Position.user_id == user_id,
                    Position.symbol == order_data.symbol,
                    Position.position_status == PositionStatus.OPEN
                )
            ).first()
            
            if not position or position.quantity < order_data.quantity:
                available = position.quantity if position else 0
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient quantity. Required: {order_data.quantity}, Available: {available}"
                )
        
        # Create order
        order = Order(
            user_id=user_id,
            symbol=order_data.symbol,
            order_type=order_data.order_type,
            order_side=order_data.order_side,
            quantity=order_data.quantity,
            price=order_data.price,
            stop_price=order_data.stop_price,
            order_status=OrderStatus.PENDING
        )
        
        session.add(order)
        
        # Execute market order immediately
        if order_data.order_type == OrderType.MARKET:
            await OrderService._execute_market_order(session, order)
        
        session.commit()
        session.refresh(order)
        
        return order
    
    @staticmethod
    async def _calculate_required_balance(
        order_data: OrderCreate,
        session: Session
    ) -> Decimal:
        """Calculate required balance for an order"""
        if order_data.order_type == OrderType.MARKET:
            # Get current market price
            current_price = await get_current_price(order_data.symbol)
            required = Decimal(str(current_price)) * order_data.quantity
        elif order_data.order_type == OrderType.LIMIT:
            # Use limit price
            if order_data.price is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Price is required for LIMIT orders"
                )
            required = order_data.price * order_data.quantity
        else:
            # For STOP_LOSS and TAKE_PROFIT, calculate based on stop price
            required = Decimal("0")  # These don't lock balance immediately
        
        # Add trading fee
        if required > 0:
            required += required * Decimal(str(settings.DEFAULT_TRADING_FEE))
        
        return required
    
    @staticmethod
    async def _execute_market_order(session: Session, order: Order):
        """Execute a market order immediately"""
        try:
            # Get current market price
            current_price = await get_current_price(order.symbol)
            
            # Calculate fee
            fee = order.quantity * Decimal(str(current_price)) * Decimal(str(settings.DEFAULT_TRADING_FEE))
            
            # Update order
            order.executed_quantity = order.quantity
            order.executed_price = Decimal(str(current_price))
            order.fee = fee
            order.order_status = OrderStatus.FILLED
            order.updated_at = datetime.utcnow()
            
            # Update account balance and positions
            account = session.exec(
                select(TradingAccount).where(TradingAccount.user_id == order.user_id)
            ).first()
            
            if order.order_side == OrderSide.BUY:
                # Deduct balance
                total_cost = (order.executed_price * order.quantity) + fee
                account.balance -= total_cost
                account.locked_balance -= total_cost
                
                # Update or create position
                position = session.exec(
                    select(Position).where(
                        Position.user_id == order.user_id,
                        Position.symbol == order.symbol,
                        Position.position_status == PositionStatus.OPEN
                    )
                ).first()
                
                if position:
                    # Update existing position
                    total_quantity = position.quantity + order.quantity
                    total_value = (position.quantity * position.average_price) + (order.quantity * order.executed_price)
                    position.average_price = total_value / total_quantity
                    position.quantity = total_quantity
                else:
                    # Create new position
                    position = Position(
                        user_id=order.user_id,
                        symbol=order.symbol,
                        quantity=order.quantity,
                        average_price=order.executed_price,
                        current_price=order.executed_price
                    )
                    session.add(position)
            
            else:  # SELL
                # Add balance
                total_revenue = (order.executed_price * order.quantity) - fee
                account.balance += total_revenue
                
                # Update position
                position = session.exec(
                    select(Position).where(
                        Position.user_id == order.user_id,
                        Position.symbol == order.symbol,
                        Position.position_status == PositionStatus.OPEN
                    )
                ).first()
                
                if position:
                    # Calculate realized PnL
                    realized_pnl = (order.executed_price - position.average_price) * order.quantity
                    position.realized_pnl += realized_pnl
                    position.quantity -= order.quantity
                    
                    # Close position if quantity is 0
                    if position.quantity <= 0:
                        position.position_status = PositionStatus.CLOSED
                    
                    # Update account profit
                    account.total_profit += realized_pnl
            
            # Update total volume
            account.total_volume += order.quantity * order.executed_price
            
            # Create transaction record
            transaction = Transaction(
                user_id=order.user_id,
                order_id=order.id,
                transaction_type=f"TRADE_{order.order_side.value}",
                amount=order.quantity * order.executed_price,
                balance_after=account.balance,
                description=f"{order.order_side.value} {order.quantity} {order.symbol} @ {order.executed_price}"
            )
            session.add(transaction)
            
        except Exception as e:
            logger.error(f"Failed to execute market order: {e}")
            order.order_status = OrderStatus.REJECTED
            raise

    @staticmethod
    async def cancel_order(
        session: Session,
        user_id: int,
        order_id: int
    ) -> Order:
        """
        Cancel an order
        
        Args:
            session: Database session
            user_id: User ID
            order_id: Order ID
        
        Returns:
            Order: Cancelled order
        
        Raises:
            HTTPException: If order not found or cannot be cancelled
        """
        order = session.exec(
            select(Order).where(
                Order.id == order_id,
                Order.user_id == user_id
            )
        ).first()
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        if order.order_status != OrderStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel order with status: {order.order_status.value}"
            )
        
        order.order_status = OrderStatus.CANCELLED
        order.updated_at = datetime.utcnow()
        
        session.commit()
        session.refresh(order)
        
        return order

    @staticmethod
    async def get_user_orders(
        session: Session,
        user_id: int,
        symbol: Optional[str] = None,
        status: Optional[OrderStatus] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Order]:
        """
        Get user orders with optional filtering
        
        Args:
            session: Database session
            user_id: User ID
            symbol: Optional symbol filter
            status: Optional status filter
            limit: Maximum number of results
            offset: Results offset
        
        Returns:
            List[Order]: List of orders
        """
        query = select(Order).where(Order.user_id == user_id)
        
        if symbol:
            query = query.where(Order.symbol == symbol)
        
        if status:
            query = query.where(Order.order_status == status)
        
        query = query.order_by(Order.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        orders = session.exec(query).all()
        return orders

    @staticmethod
    async def check_pending_orders(session: Session):
        """
        Check and execute pending limit orders
        This should be called periodically by a background task
        """
        pending_orders = session.exec(
            select(Order).where(
                Order.order_status == OrderStatus.PENDING,
                Order.order_type == OrderType.LIMIT
            )
        ).all()
        
        for order in pending_orders:
            try:
                current_price = await get_current_price(order.symbol)
                
                should_execute = False
                
                if order.order_side == OrderSide.BUY:
                    # Execute buy order if current price <= limit price
                    should_execute = current_price <= float(order.price)
                else:
                    # Execute sell order if current price >= limit price
                    should_execute = current_price >= float(order.price)
                
                if should_execute:
                    await OrderService._execute_market_order(session, order)
                    session.commit()
                    logger.info(f"Executed limit order {order.id} for user {order.user_id}")
            
            except Exception as e:
                logger.error(f"Failed to check order {order.id}: {e}")
                continue

# Create singleton instance
order_service = OrderService()