# app/routers/futures.py
"""
선물 거래 API 라우터
"""
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from typing import List
from decimal import Decimal

from app.core.database import get_session
from app.utils.security import get_current_user
from app.models.database import User
from app.models.futures import (
    FuturesAccount, FuturesPosition, FuturesTransaction,
    FuturesPositionSide, FuturesOrderType, FuturesPositionStatus
)
from app.services import futures_service
from pydantic import BaseModel, Field
import logging

router = APIRouter(prefix="/futures", tags=["futures"])
logger = logging.getLogger(__name__)


# =====================================================
# Schemas
# =====================================================

class FuturesPositionOpen(BaseModel):
    """선물 포지션 개설 요청"""
    symbol: str = Field(..., description="거래 심볼 (예: BTCUSDT)")
    side: str = Field(..., description="LONG or SHORT")
    quantity: Decimal = Field(..., gt=0, description="계약 수량")
    leverage: int = Field(..., ge=1, le=125, description="레버리지 (1~125x)")
    order_type: str = Field(default="MARKET", description="MARKET or LIMIT")
    price: Decimal | None = Field(None, description="지정가 (LIMIT만)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "BTCUSDT",
                "side": "LONG",
                "quantity": "0.1",
                "leverage": 10,
                "order_type": "MARKET"
            }
        }


class FuturesAccountOut(BaseModel):
    """선물 계정 응답"""
    id: str  # ✅ UUID
    user_id: str
    balance: float  # ✅ float로 변환하여 표시
    margin_used: float
    total_profit: float
    unrealized_pnl: float
    total_balance: float
    available_balance: float
    margin_ratio: float
    
    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v)  # Decimal을 float로 변환
        }


class FuturesPositionOut(BaseModel):
    """선물 포지션 응답"""
    id: str  # ✅ UUID
    symbol: str
    side: str
    status: str
    leverage: int
    quantity: float
    entry_price: float
    mark_price: float
    margin: float
    unrealized_pnl: float
    realized_pnl: float
    liquidation_price: float
    position_value: float
    roe_percent: float
    opened_at: str
    closed_at: str | None
    
    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v)
        }


# =====================================================
# API Endpoints
# =====================================================

@router.get("/account", response_model=FuturesAccountOut)
async def get_futures_account(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    선물 계정 조회
    
    - balance: 사용 가능한 증거금
    - margin_used: 포지션에 사용 중인 증거금
    - total_balance: 총 자산
    - unrealized_pnl: 미실현 손익
    - margin_ratio: 증거금 비율 (%)
    """
    
    from sqlmodel import select
    
    account = session.exec(
        select(FuturesAccount).where(FuturesAccount.user_id == current_user.id)
    ).first()
    
    if not account:
        # 선물 계정 생성
        account = FuturesAccount(
            user_id=current_user.id,
            balance=Decimal("1000000"),
            margin_used=Decimal("0"),
            total_profit=Decimal("0"),
            unrealized_pnl=Decimal("0")
        )
        session.add(account)
        session.commit()
        session.refresh(account)
    
    return FuturesAccountOut(
        id=account.id,
        user_id=account.user_id,
        balance=float(account.balance),
        margin_used=float(account.margin_used),
        total_profit=float(account.total_profit),
        unrealized_pnl=float(account.unrealized_pnl),
        total_balance=float(account.total_balance),
        available_balance=float(account.available_balance),
        margin_ratio=float(account.margin_ratio)
    )


@router.post("/positions/open", response_model=FuturesPositionOut)
async def open_position(
    data: FuturesPositionOpen,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    선물 포지션 개설
    
    ### 예시:
    - BTC 10x 롱 포지션
    - 수량: 0.1 BTC
    - 현재가: 50,000 USDT
    - 필요 증거금: 500 USDT (50,000 * 0.1 / 10)
    - 청산가: ~45,000 USDT (증거금의 90% 손실 시)
    
    ### 레버리지:
    - 1x ~ 125x
    - 높을수록 수익도 크지만 위험도 큼
    
    ### 롱 vs 숏:
    - 롱(LONG): 가격 상승 베팅
    - 숏(SHORT): 가격 하락 베팅
    """
    
    logger.info(
        f"📥 선물 포지션 개설 요청: User={current_user.username}, "
        f"{data.side} {data.symbol} {data.quantity} @ {data.leverage}x"
    )
    
    position = await futures_service.open_futures_position(
        session=session,
        user_id=current_user.id,
        symbol=data.symbol,
        side=FuturesPositionSide(data.side),
        quantity=data.quantity,
        leverage=data.leverage,
        order_type=FuturesOrderType(data.order_type),
        price=data.price
    )
    
    return FuturesPositionOut(
        id=position.id,
        symbol=position.symbol,
        side=position.side.value,
        status=position.status.value,
        leverage=position.leverage,
        quantity=float(position.quantity),
        entry_price=float(position.entry_price),
        mark_price=float(position.mark_price),
        margin=float(position.margin),
        unrealized_pnl=float(position.unrealized_pnl),
        realized_pnl=float(position.realized_pnl),
        liquidation_price=float(position.liquidation_price),
        position_value=float(position.position_value),
        roe_percent=float(position.roe_percent),
        opened_at=position.opened_at.isoformat(),
        closed_at=position.closed_at.isoformat() if position.closed_at else None
    )


@router.post("/positions/{position_id}/close")
async def close_position(
    position_id: str,  # ✅ UUID
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    선물 포지션 청산
    
    - 현재가로 포지션 청산
    - 실현 손익 계산
    - 증거금 반환
    """
    
    result = await futures_service.close_futures_position(
        session=session,
        user_id=current_user.id,
        position_id=position_id
    )
    
    return result


@router.get("/positions", response_model=List[FuturesPositionOut])
async def get_positions(
    status: str = Query("OPEN", description="OPEN, CLOSED, LIQUIDATED"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    선물 포지션 목록 조회
    
    - status: OPEN (열림), CLOSED (청산됨), LIQUIDATED (강제청산됨)
    """
    
    positions = futures_service.get_futures_positions(
        session=session,
        user_id=current_user.id,
        status=FuturesPositionStatus(status)
    )
    
    result = []
    for pos in positions:
        result.append(FuturesPositionOut(
            id=pos.id,
            symbol=pos.symbol,
            side=pos.side.value,
            status=pos.status.value,
            leverage=pos.leverage,
            quantity=float(pos.quantity),
            entry_price=float(pos.entry_price),
            mark_price=float(pos.mark_price),
            margin=float(pos.margin),
            unrealized_pnl=float(pos.unrealized_pnl),
            realized_pnl=float(pos.realized_pnl),
            liquidation_price=float(pos.liquidation_price),
            position_value=float(pos.position_value),
            roe_percent=float(pos.roe_percent),
            opened_at=pos.opened_at.isoformat(),
            closed_at=pos.closed_at.isoformat() if pos.closed_at else None
        ))
    
    return result


@router.get("/transactions", response_model=List[dict])
async def get_transactions(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    선물 거래 내역 조회
    """
    
    from sqlmodel import select
    
    transactions = session.exec(
        select(FuturesTransaction)
        .where(FuturesTransaction.user_id == current_user.id)
        .order_by(FuturesTransaction.timestamp.desc())
        .limit(limit)
    ).all()
    
    return [
        {
            "id": tx.id,
            "symbol": tx.symbol,
            "side": tx.side.value,
            "action": tx.action,
            "quantity": float(tx.quantity),
            "price": float(tx.price),
            "leverage": tx.leverage,
            "pnl": float(tx.pnl),
            "fee": float(tx.fee),
            "timestamp": tx.timestamp.isoformat()
        }
        for tx in transactions
    ]


@router.get("/stats")
async def get_futures_stats(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    선물 거래 통계
    
    - 총 거래 횟수
    - 승률
    - 평균 ROE
    - 최대 수익/손실
    """
    
    from sqlmodel import select
    
    # 청산된 포지션만 조회 (실현 손익)
    closed_positions = session.exec(
        select(FuturesPosition)
        .join(FuturesAccount)
        .where(
            FuturesAccount.user_id == current_user.id,
            FuturesPosition.status.in_([
                FuturesPositionStatus.CLOSED,
                FuturesPositionStatus.LIQUIDATED
            ])
        )
    ).all()
    
    if not closed_positions:
        return {
            "total_trades": 0,
            "win_trades": 0,
            "lose_trades": 0,
            "win_rate": 0,
            "total_pnl": 0,
            "avg_roe": 0,
            "max_profit": 0,
            "max_loss": 0
        }
    
    total_trades = len(closed_positions)
    win_trades = len([p for p in closed_positions if p.realized_pnl > 0])
    lose_trades = len([p for p in closed_positions if p.realized_pnl < 0])
    win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
    
    total_pnl = sum(float(p.realized_pnl) for p in closed_positions)
    avg_roe = sum(float(p.roe_percent) for p in closed_positions) / total_trades if total_trades > 0 else 0
    max_profit = max((float(p.realized_pnl) for p in closed_positions), default=0)
    max_loss = min((float(p.realized_pnl) for p in closed_positions), default=0)
    
    return {
        "total_trades": total_trades,
        "win_trades": win_trades,
        "lose_trades": lose_trades,
        "win_rate": round(win_rate, 2),
        "total_pnl": round(total_pnl, 2),
        "avg_roe": round(avg_roe, 2),
        "max_profit": round(max_profit, 2),
        "max_loss": round(max_loss, 2)
    }