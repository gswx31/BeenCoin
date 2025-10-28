# app/routers/account.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from app.core.database import get_session
from app.utils.security import get_current_user
from app.models.database import User, TradingAccount, Position, Transaction
from app.services.binance_service import get_current_price
from typing import List, Dict, Any
import logging
from decimal import Decimal

router = APIRouter(prefix="/account", tags=["account"])
logger = logging.getLogger(__name__)


@router.get("/")
async def get_account(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """계정 요약"""
    try:
        account = session.exec(
            select(TradingAccount).where(TradingAccount.user_id == current_user.id)
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다")
        
        positions = session.exec(
            select(Position)
            .where(Position.account_id == account.id)
            .where(Position.quantity > 0)
        ).all()
        
        positions_data = []
        positions_value = Decimal('0')
        unrealized_profit_total = Decimal('0')
        
        for pos in positions:
            try:
                current_price = await get_current_price(pos.symbol)
                position_value = pos.quantity * current_price
                invested_value = pos.quantity * pos.average_price
                unrealized_profit = position_value - invested_value
                profit_rate = float((unrealized_profit / invested_value) * 100) if invested_value > 0 else 0
                
                positions_data.append({
                    "symbol": pos.symbol,
                    "quantity": float(pos.quantity),
                    "average_price": float(pos.average_price),
                    "current_price": float(current_price),
                    "invested_value": float(invested_value),
                    "current_value": float(position_value),
                    "unrealized_profit": float(unrealized_profit),
                    "profit_rate": round(profit_rate, 2)
                })
                
                positions_value += position_value
                unrealized_profit_total += unrealized_profit
                
            except Exception as e:
                logger.error(f"❌ {pos.symbol} 가격 조회 실패: {e}")
        
        total_value = account.balance + positions_value
        
        result = {
            "balance": float(account.balance),
            "total_profit": float(account.total_profit),
            "positions_value": float(positions_value),
            "total_value": float(total_value),
            "unrealized_profit": float(unrealized_profit_total),
            "positions": positions_data
        }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 계정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="계정 조회 중 오류가 발생했습니다")


@router.get("/transactions")
def get_transactions(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    limit: int = 100
) -> List[Dict[str, Any]]:
    """거래 내역"""
    try:
        transactions = session.exec(
            select(Transaction)
            .where(Transaction.user_id == current_user.id)
            .order_by(Transaction.timestamp.desc())
            .limit(limit)
        ).all()
        
        result = [
            {
                "id": tx.id,
                "symbol": tx.symbol,
                "side": tx.side,
                "quantity": float(tx.quantity),
                "price": float(tx.price),
                "fee": float(tx.fee),
                "timestamp": str(tx.timestamp)
            }
            for tx in transactions
        ]
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 거래 내역 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="거래 내역 조회 중 오류가 발생했습니다")