# app/services/portfolio_service.py
"""
Portfolio management service
"""
from sqlmodel import Session, select, func
from sqlalchemy.orm import selectinload
from typing import Dict, List, Optional
from decimal import Decimal
from app.models.database import TradingAccount, Position, PositionStatus, Transaction, Order
from app.services.binance_service import get_current_price
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PortfolioService:
    """Portfolio management service"""
    
    @staticmethod
    async def get_portfolio_summary(session: Session, user_id: int) -> Dict:
        """
        Get comprehensive portfolio summary
        
        Args:
            session: Database session
            user_id: User ID
        
        Returns:
            Dict: Portfolio summary
        """
        # Get account with positions in single query (avoid N+1)
        account = session.exec(
            select(TradingAccount)
            .where(TradingAccount.user_id == user_id)
            .options(selectinload(TradingAccount.user))
        ).first()
        
        if not account:
            return {
                "total_value": 0,
                "balance": 0,
                "locked_balance": 0,
                "positions_value": 0,
                "total_profit": 0,
                "profit_rate": 0,
                "positions": []
            }
        
        # Get all open positions
        positions = session.exec(
            select(Position)
            .where(
                Position.user_id == user_id,
                Position.position_status == PositionStatus.OPEN
            )
        ).all()
        
        # Calculate positions value with current prices
        positions_value = Decimal("0")
        position_details = []
        
        for position in positions:
            try:
                # Get current price
                current_price = await get_current_price(position.symbol)
                current_price = Decimal(str(current_price))
                
                # Update position current price
                position.current_price = current_price
                position.unrealized_pnl = (current_price - position.average_price) * position.quantity
                
                position_value = position.quantity * current_price
                positions_value += position_value
                
                position_details.append({
                    "symbol": position.symbol,
                    "quantity": float(position.quantity),
                    "average_price": float(position.average_price),
                    "current_price": float(current_price),
                    "current_value": float(position_value),
                    "unrealized_pnl": float(position.unrealized_pnl),
                    "unrealized_pnl_percentage": float(
                        (position.unrealized_pnl / (position.average_price * position.quantity) * 100)
                        if position.average_price > 0 else 0
                    ),
                    "realized_pnl": float(position.realized_pnl)
                })
                
            except Exception as e:
                logger.error(f"Error fetching price for {position.symbol}: {e}")
                # Use average price if current price unavailable
                position_value = position.quantity * position.average_price
                positions_value += position_value
        
        session.commit()  # Save updated prices
        
        # Calculate total value and profit rate
        total_value = account.balance + positions_value
        profit_rate = (account.total_profit / total_value * 100) if total_value > 0 else 0
        
        return {
            "total_value": float(total_value),
            "balance": float(account.balance),
            "locked_balance": float(account.locked_balance),
            "positions_value": float(positions_value),
            "total_profit": float(account.total_profit),
            "profit_rate": float(profit_rate),
            "total_volume": float(account.total_volume),
            "positions": position_details
        }
    
    @staticmethod
    async def get_portfolio_performance(
        session: Session,
        user_id: int,
        period_days: int = 30
    ) -> Dict:
        """
        Get portfolio performance metrics
        
        Args:
            session: Database session
            user_id: User ID
            period_days: Period in days
        
        Returns:
            Dict: Performance metrics
        """
        start_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Get transactions in period
        transactions = session.exec(
            select(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.created_at >= start_date
            )
            .order_by(Transaction.created_at)
        ).all()
        
        # Get completed orders in period
        orders = session.exec(
            select(Order)
            .where(
                Order.user_id == user_id,
                Order.created_at >= start_date,
                Order.order_status == "FILLED"
            )
        ).all()
        
        # Calculate metrics
        total_trades = len(orders)
        winning_trades = 0
        losing_trades = 0
        total_profit = Decimal("0")
        total_loss = Decimal("0")
        total_volume = Decimal("0")
        
        for order in orders:
            if order.order_side == "SELL":
                # Find corresponding buy order
                position = session.exec(
                    select(Position)
                    .where(
                        Position.user_id == user_id,
                        Position.symbol == order.symbol
                    )
                ).first()
                
                if position:
                    pnl = (order.executed_price - position.average_price) * order.quantity
                    
                    if pnl > 0:
                        winning_trades += 1
                        total_profit += pnl
                    else:
                        losing_trades += 1
                        total_loss += abs(pnl)
            
            total_volume += order.quantity * (order.executed_price or order.price or 0)
        
        # Win rate
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Average profit/loss
        avg_profit = (total_profit / winning_trades) if winning_trades > 0 else 0
        avg_loss = (total_loss / losing_trades) if losing_trades > 0 else 0
        
        # Profit factor
        profit_factor = (total_profit / total_loss) if total_loss > 0 else float(total_profit)
        
        # Daily statistics
        daily_trades = total_trades / period_days if period_days > 0 else 0
        daily_volume = total_volume / period_days if period_days > 0 else 0
        
        return {
            "period_days": period_days,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": float(win_rate),
            "total_profit": float(total_profit),
            "total_loss": float(total_loss),
            "net_profit": float(total_profit - total_loss),
            "average_profit": float(avg_profit),
            "average_loss": float(avg_loss),
            "profit_factor": float(profit_factor),
            "total_volume": float(total_volume),
            "daily_trades": float(daily_trades),
            "daily_volume": float(daily_volume),
            "transactions": len(transactions)
        }
    
    @staticmethod
    async def get_asset_allocation(session: Session, user_id: int) -> List[Dict]:
        """
        Get asset allocation breakdown
        
        Args:
            session: Database session
            user_id: User ID
        
        Returns:
            List[Dict]: Asset allocation
        """
        # Get account
        account = session.exec(
            select(TradingAccount).where(TradingAccount.user_id == user_id)
        ).first()
        
        if not account:
            return []
        
        # Get positions
        positions = session.exec(
            select(Position)
            .where(
                Position.user_id == user_id,
                Position.position_status == PositionStatus.OPEN
            )
        ).all()
        
        # Calculate allocation
        allocation = []
        total_value = account.balance
        
        # Add USDT allocation
        allocation.append({
            "asset": "USDT",
            "quantity": float(account.balance),
            "value": float(account.balance),
            "percentage": 0  # Will calculate after
        })
        
        # Add position allocations
        for position in positions:
            try:
                current_price = await get_current_price(position.symbol)
                position_value = position.quantity * Decimal(str(current_price))
                total_value += position_value
                
                # Extract base asset from symbol (e.g., BTC from BTCUSDT)
                base_asset = position.symbol.replace("USDT", "")
                
                allocation.append({
                    "asset": base_asset,
                    "symbol": position.symbol,
                    "quantity": float(position.quantity),
                    "value": float(position_value),
                    "price": current_price,
                    "percentage": 0
                })
                
            except Exception as e:
                logger.error(f"Error calculating allocation for {position.symbol}: {e}")
        
        # Calculate percentages
        for item in allocation:
            item["percentage"] = (item["value"] / float(total_value) * 100) if total_value > 0 else 0
        
        # Sort by value descending
        allocation.sort(key=lambda x: x["value"], reverse=True)
        
        return allocation


# Singleton instance
portfolio_service = PortfolioService()