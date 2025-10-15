from sqlmodel import Session, select
from app.models.database import Order, Position, TradingAccount, TransactionHistory
from app.services.binance_service import get_current_price, monitor_limit_order, execute_market_order
from decimal import Decimal
import asyncio
from app.schemas.order import OrderCreate
from fastapi import HTTPException
from app.core.config import settings
from typing import Optional, List
from datetime import datetime

FEE_RATE = Decimal('0.001')  # 0.1% 수수료

async def create_order(session: Session, user_id: int, order_data: OrderCreate) -> Order:
    """주문 생성 및 실행"""
    if order_data.symbol not in settings.SUPPORTED_SYMBOLS:
        raise HTTPException(status_code=400, detail="Unsupported symbol")
    
    # 주문 생성
    order = Order(
        user_id=user_id, 
        symbol=order_data.symbol,
        side=order_data.side,
        order_type=order_data.order_type,
        quantity=order_data.quantity,
        price=order_data.price if order_data.order_type == 'LIMIT' else None,
        order_status='PENDING'
    )
    
    session.add(order)
    session.commit()
    session.refresh(order)
    
    try:
        if order.order_type == 'MARKET':
            # 시장가 주문 즉시 실행
            execution_price = await execute_market_order(order.symbol, order.side, order.quantity)
            await process_order_execution(session, order.id, order.quantity, execution_price)
            
        elif order.order_type == 'LIMIT':
            # 지정가 주문 비동기 모니터링
            async def limit_order_callback(order_id: int, filled_quantity: Decimal, execution_price: Decimal):
                await process_order_execution(session, order_id, filled_quantity, execution_price)
            
            asyncio.create_task(
                monitor_limit_order(
                    order.id, order.symbol, order.side, order.price, 
                    order.quantity, limit_order_callback
                )
            )
        
        return order
        
    except Exception as e:
        # 주문 실패시 상태 업데이트
        order.order_status = 'FAILED'
        session.add(order)
        session.commit()
        raise HTTPException(status_code=500, detail=f"Order creation failed: {str(e)}")

async def process_order_execution(session: Session, order_id: int, filled_quantity: Decimal, execution_price: Decimal):
    """주문 체결 처리"""
    try:
        # 주문 조회
        order = session.exec(select(Order).where(Order.id == order_id)).first()
        if not order:
            print(f"Order {order_id} not found")
            return
        
        # 수수료 계산
        fee = execution_price * filled_quantity * FEE_RATE
        
        # 주문 상태 업데이트
        order.filled_quantity = filled_quantity
        order.price = execution_price
        order.order_status = 'FILLED'
        order.updated_at = datetime.utcnow()
        
        # 포지션 및 계정 업데이트
        await update_position_and_account(session, order.user_id, order.symbol, order.side, filled_quantity, execution_price, fee)
        
        # 거래 기록
        record_transaction(session, order.user_id, order.id, order.symbol, order.side, filled_quantity, execution_price, fee)
        
        session.add(order)
        session.commit()
        
        print(f"Order {order_id} executed successfully")
        
    except Exception as e:
        print(f"Error processing order execution for {order_id}: {str(e)}")
        session.rollback()

async def update_position_and_account(session: Session, user_id: int, symbol: str, side: str, quantity: Decimal, price: Decimal, fee: Decimal):
    """포지션과 계정 업데이트"""
    account = session.exec(select(TradingAccount).where(TradingAccount.user_id == user_id)).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    position = session.exec(
        select(Position).where(Position.account_id == account.id, Position.symbol == symbol)
    ).first()
    
    total_cost = price * quantity
    net_amount = total_cost + fee if side == 'BUY' else total_cost - fee
    
    if side == 'BUY':
        # 매수 로직
        if account.balance < net_amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        
        if not position:
            position = Position(
                account_id=account.id,
                symbol=symbol,
                quantity=quantity,
                average_price=price,
                current_value=quantity * price,
                unrealized_profit=Decimal('0')
            )
            session.add(position)
        else:
            # 평균 단가 재계산
            total_quantity = position.quantity + quantity
            total_value = (position.average_price * position.quantity) + total_cost
            new_avg_price = total_value / total_quantity
            
            position.quantity = total_quantity
            position.average_price = new_avg_price
        
        account.balance -= net_amount
        
    elif side == 'SELL':
        # 매도 로직
        if not position or position.quantity < quantity:
            raise HTTPException(status_code=400, detail="Insufficient quantity to sell")
        
        # 실현 손익 계산
        realized_profit = (price - position.average_price) * quantity - fee
        
        position.quantity -= quantity
        account.balance += net_amount
        account.total_profit += realized_profit
        
        # 포지션이 0이 되면 삭제
        if position.quantity == 0:
            session.delete(position)
    
    # 포지션 현재 가치 업데이트
    if position and position.quantity > 0:
        current_price = await get_current_price(symbol)
        position.current_value = position.quantity * current_price
        position.unrealized_profit = position.quantity * (current_price - position.average_price)
        session.add(position)
    
    session.add(account)
    session.commit()

def record_transaction(session: Session, user_id: int, order_id: Optional[int], symbol: str, side: str, quantity: Decimal, price: Decimal, fee: Decimal):
    """거래 기록 생성"""
    transaction = TransactionHistory(
        user_id=user_id,
        order_id=order_id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price,
        fee=fee
    )
    session.add(transaction)
    session.commit()

def get_user_orders(session: Session, user_id: int) -> List[Order]:
    """사용자 주문 조회"""
    return session.exec(
        select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc())
    ).all()

def get_account_summary(session: Session, user_id: int) -> dict:
    """계정 요약 정보"""
    account = session.exec(select(TradingAccount).where(TradingAccount.user_id == user_id)).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    positions = session.exec(select(Position).where(Position.account_id == account.id)).all()
    
    total_position_value = sum(p.current_value for p in positions)
    total_value = account.balance + total_position_value
    initial_balance = Decimal(str(settings.INITIAL_BALANCE))
    
    profit_rate = ((total_value - initial_balance) / initial_balance * 100) if initial_balance > 0 else Decimal('0')
    
    return {
        "balance": float(account.balance),
        "total_profit": float(account.total_profit),
        "positions": [{
            "symbol": p.symbol,
            "quantity": float(p.quantity),
            "average_price": float(p.average_price),
            "current_value": float(p.current_value),
            "unrealized_profit": float(p.unrealized_profit)
        } for p in positions],
        "profit_rate": float(profit_rate),
        "total_value": float(total_value),
        "total_position_value": float(total_position_value)
    }

def get_transaction_history(session: Session, user_id: int) -> List[TransactionHistory]:
    """거래 내역 조회"""
    return session.exec(
        select(TransactionHistory)
        .where(TransactionHistory.user_id == user_id)
        .order_by(TransactionHistory.timestamp.desc())
    ).all()