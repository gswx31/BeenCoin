# app/routers/account.py
from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.schemas.account import AccountOut
from app.schemas.transaction import TransactionOut
from app.services.order_service import get_account_summary, get_transaction_history
from app.core.database import get_session
from app.utils.security import get_current_user
from app.models.database import User
from typing import List
import logging

router = APIRouter(prefix="/account", tags=["account"])
logger = logging.getLogger(__name__)

@router.get("/", response_model=AccountOut)
def get_account(
    current_user: User = Depends(get_current_user), 
    session: Session = Depends(get_session)
):
    """계정 정보 조회"""
    try:
        summary = get_account_summary(session, current_user.id)
        return AccountOut(**summary)
    except Exception as e:
        logger.error(f"❌ 계정 조회 실패: {e}")
        raise


@router.get("/transactions", response_model=List[TransactionOut])
def get_transactions(
    current_user: User = Depends(get_current_user), 
    session: Session = Depends(get_session)
):
    """거래 내역 조회"""
    try:
        transactions = get_transaction_history(session, current_user.id)
        
        return [
            TransactionOut(
                id=t.id,
                symbol=t.symbol,
                side=t.side.value if hasattr(t.side, 'value') else t.side,
                quantity=float(t.quantity),
                price=float(t.price),
                fee=float(t.fee),
                timestamp=str(t.timestamp)
            ) 
            for t in transactions
        ]
    except Exception as e:
        logger.error(f"❌ 거래 내역 조회 실패: {e}")
        raise