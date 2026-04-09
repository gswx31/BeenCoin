from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session
from app.schemas.account import AccountOut
from app.schemas.transaction import TransactionOut
from app.services.order_service import get_account_summary, get_transaction_history, toggle_bnb_fee
from app.core.database import get_session
from app.routers.orders import get_current_user
from app.core.config import settings
from typing import List

router = APIRouter(prefix="/account", tags=["account"])


@router.get("", response_model=AccountOut)
def get_account(current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    return get_account_summary(session, current_user.id)


@router.get("/transactions", response_model=List[TransactionOut])
def get_transactions(current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    txs = get_transaction_history(session, current_user.id)
    return [
        TransactionOut(
            id=t.id, symbol=t.symbol, side=t.side,
            quantity=t.quantity, price=t.price,
            fee=t.fee, fee_asset=t.fee_asset,
            is_maker=t.is_maker, realized_pnl=t.realized_pnl,
            timestamp=str(t.timestamp),
        )
        for t in txs
    ]


class BnbFeeToggle(BaseModel):
    use_bnb: bool


@router.post("/bnb-fee")
def set_bnb_fee(
    body: BnbFeeToggle,
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return toggle_bnb_fee(session, current_user.id, body.use_bnb)


@router.get("/symbol-rules")
def get_symbol_rules():
    """Return Binance-style symbol trading rules."""
    return settings.SYMBOL_RULES
