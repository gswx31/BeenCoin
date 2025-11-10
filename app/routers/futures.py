# app/routers/futures.py
"""
Futures trading routes
"""
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from typing import List, Optional
from decimal import Decimal
from app.core.database import get_session
from app.models.database import User
from app.models.futures import (
    FuturesPosition, FuturesAccount, FuturesPositionSide,
    FuturesPositionStatus
)
from app.services.futures_service import futures_service
from app.utils.security import get_current_user
from pydantic import BaseModel, Field

router = APIRouter(prefix="/futures", tags=["Futures Trading"])

# Request schemas
class OpenPositionRequest(BaseModel):
    """Open position request schema"""
    symbol: str
    side: FuturesPositionSide
    quantity: Decimal = Field(..., gt=0)
    leverage: int = Field(default=1, ge=1, le=125)
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None

class ClosePositionRequest(BaseModel):
    """Close position request schema"""
    position_id: int

# Routes
@router.get("/account")
async def get_futures_account(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get futures account information"""
    
    account = session.exec(
        select(FuturesAccount).where(FuturesAccount.user_id == current_user.id)
    ).first()
    
    if not account:
        # Create account if not exists
        account = FuturesAccount(user_id=current_user.id)
        session.add(account)
        session.commit()
        session.refresh(account)
    
    return account

@router.get("/positions")
async def get_positions(
    status: Optional[FuturesPositionStatus] = Query(None),
    symbol: Optional[str] = Query(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get user's futures positions"""
    
    query = select(FuturesPosition).where(
        FuturesPosition.user_id == current_user.id
    )
    
    if status:
        query = query.where(FuturesPosition.status == status)
    
    if symbol:
        query = query.where(FuturesPosition.symbol == symbol)
    
    positions = session.exec(query).all()
    
    # Update mark prices for open positions
    for position in positions:
        if position.status == FuturesPositionStatus.OPEN:
            await futures_service.update_position_mark_price(session, position.id)
    
    return positions

@router.post("/open-position")
async def open_position(
    request: OpenPositionRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Open a new futures position"""
    
    position = await futures_service.open_position(
        session=session,
        user_id=current_user.id,
        symbol=request.symbol,
        side=request.side,
        quantity=request.quantity,
        leverage=request.leverage
    )
    
    # Set stop loss and take profit if provided
    if request.stop_loss:
        position.stop_loss = request.stop_loss
    if request.take_profit:
        position.take_profit = request.take_profit
    
    session.commit()
    session.refresh(position)
    
    return position

@router.post("/close-position")
async def close_position(
    request: ClosePositionRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Close a futures position"""
    
    position = await futures_service.close_position(
        session=session,
        user_id=current_user.id,
        position_id=request.position_id
    )
    
    return position

@router.get("/positions/{position_id}")
async def get_position(
    position_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get a specific position"""
    
    position = session.exec(
        select(FuturesPosition).where(
            FuturesPosition.id == position_id,
            FuturesPosition.user_id == current_user.id
        )
    ).first()
    
    if not position:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found"
        )
    
    # Update mark price if open
    if position.status == FuturesPositionStatus.OPEN:
        await futures_service.update_position_mark_price(session, position.id)
    
    return position