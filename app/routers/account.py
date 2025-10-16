from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.schemas.account import AccountOut
from app.schemas.transaction import TransactionOut
from app.services.order_service import get_account_summary, get_transaction_history
from app.core.database import get_session
from app.routers.orders import get_current_user
from typing import List
from app.models.database import SpotAccount, SpotPosition

router = APIRouter(prefix="/account", tags=["account"])

@router.get("/", response_model=AccountOut)
def get_account(current_user = Depends(get_current_user), session: Session = Depends(get_session)):
    summary = get_account_summary(session, current_user.id)
    return AccountOut(**summary)

@router.get("/transactions", response_model=List[TransactionOut])
def get_transactions(current_user = Depends(get_current_user), session: Session = Depends(get_session)):
    transactions = get_transaction_history(session, current_user.id)
    return [TransactionOut(**t.dict(), timestamp=str(t.timestamp)) for t in transactions]
