# app/routers/account.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.database import get_session
from app.utils.security import get_current_user
from app.models.database import User, SpotAccount, SpotPosition, Transaction
from app.services.order_service import get_account_summary, get_transaction_history
from typing import List
import logging

router = APIRouter(prefix="/account", tags=["account"])
logger = logging.getLogger(__name__)


@router.get("/")
def get_account(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    계정 요약 정보
    - 잔액
    - 총 수익
    """
    try:
        summary = get_account_summary(session, current_user.id)
        return summary
    except Exception as e:
        logger.error(f"❌ 계정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="계정 조회 실패")


@router.get("/positions")
def get_positions(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    보유 포지션 목록 조회 (매도 퍼센트 기능용)
    수량이 0보다 큰 포지션만 반환
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
    """
    거래 내역 조회
    최신순으로 정렬
    """
    try:
        transactions = get_transaction_history(session, current_user.id, limit)
        
        result = []
        for tx in transactions:
            result.append({
                "id": tx.id,
                "symbol": tx.symbol,
                "side": tx.side.value if hasattr(tx.side, 'value') else tx.side,
                "quantity": float(tx.quantity),
                "price": float(tx.price),
                "fee": float(tx.fee),
                "timestamp": tx.timestamp.isoformat()
            })
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 거래 내역 조회 실패: {e}")
        return []


@router.get("/balance")
def get_balance(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    현재 잔액만 조회 (빠른 조회용)
    """
    try:
        account = session.exec(
            select(SpotAccount).where(SpotAccount.user_id == current_user.id)
        ).first()
        
        if not account:
            return {"balance": 0}
        
        return {"balance": float(account.usdt_balance)}
        
    except Exception as e:
        logger.error(f"❌ 잔액 조회 실패: {e}")
        return {"balance": 0}