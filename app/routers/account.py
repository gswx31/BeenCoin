# app/routers/account.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.database import get_session
from app.utils.security import get_current_user
from app.models.database import User, SpotAccount, SpotPosition, Transaction
from app.services.binance_service import get_current_price
from typing import List
import logging
from decimal import Decimal
import asyncio

router = APIRouter(prefix="/account", tags=["account"])
logger = logging.getLogger(__name__)


@router.get("/")
async def get_account(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    계정 요약 정보 + 보유 포지션
    ✅ positions 데이터 포함!
    """
    try:
        # 계정 조회
        account = session.exec(
            select(SpotAccount).where(SpotAccount.user_id == current_user.id)
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다")
        
        # 포지션 조회 (수량 > 0인 것만)
        positions = session.exec(
            select(SpotPosition)
            .where(SpotPosition.account_id == account.id)
            .where(SpotPosition.quantity > 0)
        ).all()
        
        # 포지션 데이터 포맷팅 + 실시간 가격 업데이트
        positions_data = []
        positions_value = Decimal('0')
        unrealized_profit_total = Decimal('0')
        
        for pos in positions:
            try:
                # 실시간 가격 조회
                current_price = await get_current_price(pos.symbol)
                
                # 포지션 값 계산
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
                # 에러 시 캐시된 가격 사용
                positions_data.append({
                    "symbol": pos.symbol,
                    "quantity": float(pos.quantity),
                    "average_price": float(pos.average_price),
                    "current_price": float(pos.current_price),
                    "invested_value": float(pos.quantity * pos.average_price),
                    "current_value": float(pos.current_value),
                    "unrealized_profit": float(pos.unrealized_profit),
                    "profit_rate": 0
                })
        
        # 총 자산 계산
        total_value = float(account.usdt_balance + positions_value)
        
        # 초기 자본 (100만원)
        initial_balance = 1000000.0
        
        # 수익률 계산
        total_profit = float(account.total_profit + unrealized_profit_total)
        profit_rate = (total_profit / initial_balance) * 100 if initial_balance > 0 else 0
        
        return {
            "balance": float(account.usdt_balance),
            "total_value": total_value,
            "total_profit": total_profit,
            "profit_rate": round(profit_rate, 2),
            "positions": positions_data,  # ✅ 이게 중요!
            "positions_value": float(positions_value),
            "unrealized_profit": float(unrealized_profit_total),
            "realized_profit": float(account.total_profit)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 계정 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="계정 조회 실패")


@router.get("/positions")
async def get_positions(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    보유 포지션 목록만 조회
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
            try:
                current_price = await get_current_price(pos.symbol)
                result.append({
                    "symbol": pos.symbol,
                    "quantity": float(pos.quantity),
                    "average_price": float(pos.average_price),
                    "current_price": float(current_price),
                    "current_value": float(pos.quantity * current_price),
                    "unrealized_profit": float(pos.quantity * (current_price - pos.average_price))
                })
            except Exception as e:
                logger.error(f"❌ {pos.symbol} 가격 조회 실패: {e}")
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
    """
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
    현재 잔액만 빠르게 조회
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