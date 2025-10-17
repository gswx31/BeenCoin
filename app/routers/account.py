# app/routers/account.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.models.database import User, SpotAccount, SpotPosition, Order, OrderStatus, OrderSide
from app.schemas.account import AccountSummary, PositionOut
from app.core.database import get_session
from app.utils.security import get_current_user
from app.core.config import settings
from decimal import Decimal
from typing import List

router = APIRouter(prefix="/account", tags=["account"])

# app/routers/account.py
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.core.database import get_session
from app.utils.security import get_current_user
from app.models.database import User, SpotAccount, SpotPosition, Transaction
from typing import List
import logging

router = APIRouter(prefix="/account", tags=["account"])
logger = logging.getLogger(__name__)


@router.get("/")
def get_account_summary(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """계정 요약 정보"""
    try:
        account = session.exec(
            select(SpotAccount).where(SpotAccount.user_id == current_user.id)
        ).first()
        
        if not account:
            return {
                "balance": 0,
                "total_profit": 0
            }
        
        return {
            "balance": float(account.usdt_balance),
            "total_profit": float(account.total_profit)
        }
        
    except Exception as e:
        logger.error(f"❌ 계정 조회 실패: {e}")
        return {"balance": 0, "total_profit": 0}


@router.get("/positions")
def get_positions(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    ✅ 보유 포지션 목록 (매도 퍼센트 기능용)
    """
    try:
        account = session.exec(
            select(SpotAccount).where(SpotAccount.user_id == current_user.id)
        ).first()
        
        if not account:
            return []
        
        positions = session.exec(
            select(SpotPosition)
            .where(SpotPosition.account_id == account.id)
            .where(SpotPosition.quantity > 0)
        ).all()
        
        result = []
        for pos in positions:
            result.append({
                "symbol": pos.symbol,
                "quantity": float(pos.quantity),
                "average_price": float(pos.average_price),
                "current_price": float(pos.current_price),
                "current_value": float(pos.current_value),
                "unrealized_profit": float(pos.unrealized_profit)
            })
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 포지션 조회 실패: {e}")
        return []


@router.get("/transactions")
def get_transactions(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """거래 내역 조회"""
    try:
        transactions = session.exec(
            select(Transaction)
            .where(Transaction.user_id == current_user.id)
            .order_by(Transaction.timestamp.desc())
            .limit(limit)
        ).all()
        
        result = []
        for tx in transactions:
            result.append({
                "id": tx.id,
                "symbol": tx.symbol,
                "side": tx.side,
                "quantity": float(tx.quantity),
                "price": float(tx.price),
                "fee": float(tx.fee),
                "timestamp": tx.timestamp.isoformat()
            })
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 거래 내역 조회 실패: {e}")
        return []

@router.get("/positions/{symbol}")
def get_position_by_symbol(
    symbol: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    특정 심볼의 포지션 상세 조회 (주문 가능 수량 포함)
    """
    account = session.exec(
        select(SpotAccount).where(SpotAccount.user_id == current_user.id)
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다")
    
    position = session.exec(
        select(SpotPosition).where(
            SpotPosition.account_id == account.id,
            SpotPosition.symbol == symbol
        )
    ).first()
    
    if not position or position.quantity == 0:
        return {
            "symbol": symbol,
            "quantity": 0.0,
            "locked_quantity": 0.0,
            "available_quantity": 0.0,
            "average_price": 0.0,
            "message": "보유하고 있지 않은 코인입니다"
        }
    
    # 미체결 매도 주문 수량
    pending_sell_orders = session.exec(
        select(Order).where(
            Order.user_id == current_user.id,
            Order.symbol == symbol,
            Order.side == OrderSide.SELL,
            Order.status == OrderStatus.PENDING
        )
    ).all()
    
    locked_quantity = sum(
        (order.quantity - order.filled_quantity) 
        for order in pending_sell_orders
    )
    
    available_quantity = position.quantity - locked_quantity
    
    return PositionOut(
        id=position.id,
        symbol=position.symbol,
        quantity=float(position.quantity),
        locked_quantity=float(locked_quantity),
        available_quantity=float(available_quantity),
        average_price=float(position.average_price),
        current_price=float(position.current_price),
        current_value=float(position.current_value),
        unrealized_profit=float(position.unrealized_profit),
        profit_rate=(
            float((position.current_price - position.average_price) / position.average_price * 100)
            if position.average_price > 0 else 0.0
        )
    )