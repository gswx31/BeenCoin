# app/routers/account.py
"""
Account management routes
"""
from fastapi import APIRouter, Depends
from app.schemas.account import AccountOut
from app.schemas.transaction import TransactionOut
from app.services.order_service import get_account_summary, get_transaction_history
from app.core.database import get_session
from app.models.database import User, TradingAccount, Position, Transaction
from app.utils.security import get_current_user
from typing import List
from decimal import Decimal
from pydantic import BaseModel, field_serializer

router = APIRouter(tags=["Account"])

class AccountSummary(BaseModel):
    """Account summary response"""
    balance: Decimal
    locked_balance: Decimal
    total_profit: Decimal
    total_volume: Decimal
    positions_value: Decimal
    total_value: Decimal
    
    @field_serializer('balance', 'locked_balance', 'total_profit', 'total_volume', 'positions_value', 'total_value')
    def serialize_decimal(self, value: Decimal) -> str:
        """Serialize Decimal fields"""
        if value is None:
            return None
        # Format to 8 decimal places and remove trailing zeros
        formatted = f"{value:.8f}".rstrip('0').rstrip('.')
        # If the value is a whole number, keep one decimal place
        if '.' not in formatted:
            formatted = f"{value:.1f}"
        return formatted

@router.get("/summary", response_model=AccountSummary)
async def get_account_summary(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get account summary"""
    
    # Get trading account
    account = session.exec(
        select(TradingAccount).where(TradingAccount.user_id == current_user.id)
    ).first()
    
    if not account:
        account = TradingAccount(user_id=current_user.id)
        session.add(account)
        session.commit()
        session.refresh(account)
    
    # Calculate positions value
    positions = session.exec(
        select(Position).where(
            Position.user_id == current_user.id,
            Position.position_status == "OPEN"
        )
    ).all()
    
    positions_value = sum(
        pos.quantity * (pos.current_price or pos.average_price) 
        for pos in positions
    )
    
    total_value = account.balance + positions_value
    
    return AccountSummary(
        balance=account.balance,
        locked_balance=account.locked_balance,
        total_profit=account.total_profit,
        total_volume=account.total_volume,
        positions_value=positions_value,
        total_value=total_value
    )

@router.get("/positions")
async def get_positions(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get all user positions"""
    
    positions = session.exec(
        select(Position).where(Position.user_id == current_user.id)
    ).all()
    
    return positions

@router.get("/transactions")
async def get_transactions(
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get transaction history"""
    
    transactions = session.exec(
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    
    return transactions

@router.get("/portfolio")
async def get_portfolio(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get portfolio overview"""
    
    # Get open positions
    positions = session.exec(
        select(Position).where(
            Position.user_id == current_user.id,
            Position.position_status == "OPEN"
        )
    ).all()
    
    # Calculate portfolio metrics
    portfolio = []
    for position in positions:
        current_value = position.quantity * (position.current_price or position.average_price)
        cost_basis = position.quantity * position.average_price
        pnl = current_value - cost_basis
        pnl_percentage = (pnl / cost_basis * 100) if cost_basis > 0 else 0
        
        portfolio.append({
            "symbol": position.symbol,
            "quantity": position.quantity,
            "average_price": position.average_price,
            "current_price": position.current_price,
            "current_value": current_value,
            "cost_basis": cost_basis,
            "unrealized_pnl": pnl,
            "unrealized_pnl_percentage": pnl_percentage,
            "realized_pnl": position.realized_pnl
        })
    
    return portfolio

@router.get("/portfolio/performance")
async def get_portfolio_performance(
    period_days: int = 30,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get portfolio performance metrics"""
    
    from app.services.portfolio_service import portfolio_service
    
    performance = await portfolio_service.get_portfolio_performance(
        session=session,
        user_id=current_user.id,
        period_days=period_days
    )
    
    return performance

@router.get("/portfolio/allocation")
async def get_portfolio_allocation(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get asset allocation breakdown"""
    
    from app.services.portfolio_service import portfolio_service
    
    allocation = await portfolio_service.get_asset_allocation(
        session=session,
        user_id=current_user.id
    )
    
    return allocation

@router.get("/portfolio/summary")
async def get_portfolio_summary_detailed(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get detailed portfolio summary"""
    
    from app.services.portfolio_service import portfolio_service
    
    summary = await portfolio_service.get_portfolio_summary(
        session=session,
        user_id=current_user.id
    )
    
    return summary