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


@router.get("/", response_model=AccountSummary)
def get_account_summary(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    계정 요약 정보 조회
    - 잔액, 총 손익, 포지션 목록 (주문 가능 수량 포함)
    """
    # 현물 계정 조회
    account = session.exec(
        select(SpotAccount).where(SpotAccount.user_id == current_user.id)
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다")
    
    # 모든 포지션 조회
    positions = session.exec(
        select(SpotPosition).where(SpotPosition.account_id == account.id)
    ).all()
    
    # 각 포지션에 대한 주문 가능 수량 계산
    position_list = []
    for pos in positions:
        if pos.quantity > 0:  # 보유 수량이 있는 경우만
            # 해당 심볼의 PENDING 매도 주문 수량 합계
            pending_sell_orders = session.exec(
                select(Order).where(
                    Order.user_id == current_user.id,
                    Order.symbol == pos.symbol,
                    Order.side == OrderSide.SELL,
                    Order.status == OrderStatus.PENDING
                )
            ).all()
            
            # 미체결 매도 주문 수량 합계
            locked_quantity = sum(
                (order.quantity - order.filled_quantity) 
                for order in pending_sell_orders
            )
            
            # 주문 가능 수량 = 보유 수량 - 미체결 매도 주문 수량
            available_quantity = pos.quantity - locked_quantity
            
            position_list.append(PositionOut(
                id=pos.id,
                symbol=pos.symbol,
                quantity=float(pos.quantity),
                locked_quantity=float(locked_quantity),
                available_quantity=float(available_quantity),
                average_price=float(pos.average_price),
                current_price=float(pos.current_price),
                current_value=float(pos.current_value),
                unrealized_profit=float(pos.unrealized_profit),
                profit_rate=(
                    float((pos.current_price - pos.average_price) / pos.average_price * 100)
                    if pos.average_price > 0 else 0.0
                )
            ))
    
    # 총 자산 = 현금 잔액 + 모든 포지션의 현재 가치
    total_asset_value = sum(pos.current_value for pos in positions)
    total_value = account.usdt_balance + total_asset_value
    
    # 초기 자본금
    initial_balance = Decimal(str(settings.INITIAL_BALANCE))
    
    # 수익률 계산
    profit_rate = (
        float((total_value - initial_balance) / initial_balance * 100)
        if initial_balance > 0 else 0.0
    )
    
    return AccountSummary(
        balance=float(account.usdt_balance),
        total_profit=float(account.total_profit),
        total_value=float(total_value),
        profit_rate=profit_rate,
        positions=position_list
    )


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