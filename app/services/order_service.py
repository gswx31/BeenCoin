# app/services/order_service.py
from sqlmodel import Session, select
from app.models.database import (
    Order, SpotAccount, SpotPosition, Transaction,
    OrderSide, OrderStatus, TradingType
)
from app.services.binance_service import get_current_price, execute_market_order, get_recent_trades
from decimal import Decimal, InvalidOperation
from app.schemas.order import OrderCreate
from fastapi import HTTPException, status
from app.core.config import settings
from typing import List, Optional
from datetime import datetime
import logging
import asyncio

logger = logging.getLogger(__name__)
FEE_RATE = Decimal('0.001')

async def create_order(session: Session, user_id: int, order_data: OrderCreate) -> Order:
    """주문 생성 및 처리"""
    
    # 입력 검증
    try:
        quantity = Decimal(str(order_data.quantity))
        if quantity <= 0:
            raise ValueError("수량은 0보다 커야 합니다")
        
        price = None
        if order_data.price:
            price = Decimal(str(order_data.price))
            if price <= 0:
                raise ValueError("가격은 0보다 커야 합니다")
    except (ValueError, InvalidOperation) as e:
        raise HTTPException(status_code=400, detail=f"잘못된 입력: {str(e)}")
    
    # 심볼 검증
    if order_data.symbol not in settings.SUPPORTED_SYMBOLS:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 심볼: {order_data.symbol}")
    
    # 주문 생성
    try:
        order = Order(
            user_id=user_id,
            trading_type=TradingType.SPOT,
            symbol=order_data.symbol,
            side=order_data.side,
            order_type=order_data.order_type,
            quantity=quantity,
            price=price,
            status=OrderStatus.PENDING,
            filled_quantity=Decimal('0')
        )
        session.add(order)
        session.commit()
        session.refresh(order)
        
        logger.info(f"📝 주문 생성: ID={order.id}, {order.side} {order.quantity} {order.symbol}")
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 주문 생성 실패: {e}")
        raise HTTPException(status_code=500, detail="주문 생성 실패")
    
    # 시장가 주문 즉시 체결
    if order.order_type == 'MARKET':
        try:
            current_price = await execute_market_order(order.symbol, order.side, quantity)
            _fill_order(session, order, current_price, quantity)
            session.refresh(order)
            logger.info(f"✅ 시장가 체결: ID={order.id}, Price=${current_price}")
            
        except HTTPException:
            order.status = OrderStatus.REJECTED
            session.add(order)
            session.commit()
            session.refresh(order)
            raise
            
        except Exception as e:
            order.status = OrderStatus.REJECTED
            session.add(order)
            session.commit()
            session.refresh(order)
            logger.error(f"❌ 시장가 체결 실패: {e}")
            raise HTTPException(status_code=500, detail=f"주문 체결 실패: {str(e)}")
    
    # 지정가 주문 모니터링
    elif order.order_type == 'LIMIT':
        if not price:
            raise HTTPException(status_code=400, detail="지정가 주문은 가격이 필요합니다")
        
        asyncio.create_task(
            _monitor_limit_order_with_trades(order.id, order.symbol, order.side, quantity, price, user_id)
        )
        logger.info(f"⏳ 지정가 모니터링 시작: ID={order.id}, Target=${price}")
    
    return order


def _fill_order(session: Session, order: Order, price: Decimal, quantity: Decimal):
    """주문 체결 처리 (원자적 트랜잭션)"""
    
    try:
        fee = price * quantity * FEE_RATE
        
        # 계정 조회
        account = session.exec(
            select(SpotAccount).where(SpotAccount.user_id == order.user_id)
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다")
        
        # 포지션 조회/생성
        position = session.exec(
            select(SpotPosition).where(
                SpotPosition.account_id == account.id,
                SpotPosition.symbol == order.symbol
            )
        ).first()
        
        if not position:
            position = SpotPosition(
                account_id=account.id,
                symbol=order.symbol,
                quantity=Decimal('0'),
                average_price=Decimal('0'),
                current_price=price,
                current_value=Decimal('0'),
                unrealized_profit=Decimal('0')
            )
            session.add(position)
            session.flush()
        
        # 매수 처리
        if order.side == OrderSide.BUY:
            total_cost = price * quantity + fee
            
            if account.usdt_balance < total_cost:
                raise HTTPException(
                    status_code=400,
                    detail=f"잔액 부족: ${float(account.usdt_balance):.2f} (필요: ${float(total_cost):.2f})"
                )
            
            # 평균단가 계산
            new_qty = position.quantity + quantity
            total_value = (position.average_price * position.quantity) + (price * quantity)
            position.average_price = total_value / new_qty if new_qty > 0 else price
            position.quantity = new_qty
            account.usdt_balance -= total_cost
            
            logger.info(f"💰 매수 체결: {quantity} {order.symbol} @ ${price} (Fee: ${fee})")
        
        # 매도 처리
        elif order.side == OrderSide.SELL:
            if position.quantity < quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"수량 부족: {float(position.quantity)} (필요: {float(quantity)})"
                )
            
            position.quantity -= quantity
            proceeds = price * quantity
            profit = (price - position.average_price) * quantity - fee
            
            account.usdt_balance += (proceeds - fee)
            account.total_profit += profit
            
            logger.info(f"💸 매도 체결: {quantity} {order.symbol} @ ${price} (Profit: ${profit})")
        
        # 주문 업데이트
        order.filled_quantity = quantity
        order.average_price = price
        order.status = OrderStatus.FILLED
        order.updated_at = datetime.utcnow()
        
        # 거래 내역 기록
        transaction = Transaction(
            user_id=order.user_id,
            order_id=order.id,
            trading_type=TradingType.SPOT,
            symbol=order.symbol,
            side=order.side,
            quantity=quantity,
            price=price,
            fee=fee,
            timestamp=datetime.utcnow()
        )
        session.add(transaction)
        
        # 포지션 평가
        position.current_price = price
        position.current_value = position.quantity * price
        position.unrealized_profit = position.quantity * (price - position.average_price)
        position.updated_at = datetime.utcnow()
        
        # 커밋
        session.add(order)
        session.add(account)
        session.add(position)
        session.commit()
        
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 체결 처리 실패: {e}")
        raise HTTPException(status_code=500, detail="주문 체결 처리 실패")


async def _monitor_limit_order_with_trades(
    order_id: int,
    symbol: str,
    side: str,
    quantity: Decimal,
    target_price: Decimal,
    user_id: int
):
    """지정가 주문 모니터링 (바이낸스 실제 체결 내역 기반)"""
    from app.core.database import engine
    
    max_duration = 24 * 3600  # 24시간
    check_interval = 1  # 1초마다 체크
    elapsed_time = 0
    last_trade_id = None
    
    logger.info(f"⏳ 지정가 모니터링 시작: {side} {quantity} {symbol} @ ${target_price}")
    
    try:
        while elapsed_time < max_duration:
            try:
                # 바이낸스 최근 체결 내역 조회
                trades = await get_recent_trades(symbol, limit=50)
                
                if trades:
                    # 중복 체크
                    if last_trade_id:
                        trades = [t for t in trades if t['id'] > last_trade_id]
                    
                    if trades:
                        last_trade_id = max(t['id'] for t in trades)
                    
                    # 체결 조건 확인
                    for trade in trades:
                        trade_price = Decimal(str(trade['price']))
                        
                        should_fill = False
                        fill_price = trade_price
                        
                        # 매수: 실제 거래가 목표가 이하
                        if side == OrderSide.BUY and trade_price <= target_price:
                            should_fill = True
                            logger.info(f"💰 매수 조건 충족: 목표=${target_price} >= 실제=${trade_price}")
                        
                        # 매도: 실제 거래가 목표가 이상
                        elif side == OrderSide.SELL and trade_price >= target_price:
                            should_fill = True
                            logger.info(f"💸 매도 조건 충족: 목표=${target_price} <= 실제=${trade_price}")
                        
                        if should_fill:
                            with Session(engine) as new_session:
                                order = new_session.get(Order, order_id)
                                if order and order.status == OrderStatus.PENDING:
                                    _fill_order(new_session, order, fill_price, quantity)
                                    logger.info(f"✅ 지정가 체결 완료: ID={order_id} @ ${fill_price}")
                            return
                
                await asyncio.sleep(check_interval)
                elapsed_time += check_interval
                
                # 10분마다 상태 로그
                if elapsed_time % 600 == 0:
                    logger.info(f"⏰ 지정가 대기중: ID={order_id} ({elapsed_time//60}분 경과)")
                
            except Exception as e:
                logger.error(f"❌ 모니터링 체크 오류: {e}")
                await asyncio.sleep(5)
                elapsed_time += 5
        
        # 24시간 경과 - 주문 만료
        with Session(engine) as new_session:
            order = new_session.get(Order, order_id)
            if order and order.status == OrderStatus.PENDING:
                order.status = OrderStatus.EXPIRED
                order.updated_at = datetime.utcnow()
                new_session.add(order)
                new_session.commit()
                logger.warning(f"⏰ 주문 만료: ID={order_id} (24시간 경과)")
                
    except Exception as e:
        logger.error(f"❌ 모니터링 중단: {e}")


def cancel_order(session: Session, user_id: int, order_id: int) -> dict:
    """주문 취소"""
    try:
        order = session.get(Order, order_id)
        
        if not order:
            raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")
        
        if order.user_id != user_id:
            raise HTTPException(status_code=403, detail="권한이 없습니다")
        
        if order.status != OrderStatus.PENDING:
            raise HTTPException(status_code=400, detail="취소할 수 없는 주문입니다")
        
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.utcnow()
        session.add(order)
        session.commit()
        
        logger.info(f"🚫 주문 취소: ID={order_id}")
        
        return {"message": "주문이 취소되었습니다"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 주문 취소 실패: {e}")
        raise HTTPException(status_code=500, detail="주문 취소 실패")


def get_user_orders(session: Session, user_id: int, limit: int = 100) -> List[Order]:
    """사용자 주문 내역 조회"""
    try:
        return session.exec(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
        ).all()
    except Exception as e:
        logger.error(f"❌ 주문 내역 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="주문 내역 조회 실패")


def get_account_summary(session: Session, user_id: int) -> dict:
    """계정 요약 정보"""
    try:
        account = session.exec(
            select(SpotAccount).where(SpotAccount.user_id == user_id)
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다")
        
        # 보유량이 있는 포지션만
        positions = session.exec(
            select(SpotPosition)
            .where(SpotPosition.account_id == account.id)
            .where(SpotPosition.quantity > 0)
        ).all()
        
        # 포지션 현재가 업데이트
        for pos in positions:
            try:
                current_price = asyncio.run(get_current_price(pos.symbol))
                pos.current_price = current_price
                pos.current_value = pos.quantity * current_price
                pos.unrealized_profit = pos.quantity * (current_price - pos.average_price)
                pos.updated_at = datetime.utcnow()
            except Exception as e:
                logger.warning(f"⚠️ 가격 업데이트 실패: {pos.symbol} - {e}")
                pass
        
        session.commit()
        
        # 총 자산 계산
        total_value = account.usdt_balance + sum(p.current_value for p in positions)
        initial_balance = Decimal('1000000.00')
        profit_rate = ((total_value - initial_balance) / initial_balance) * 100 if initial_balance > 0 else Decimal('0')
        
        return {
            "balance": float(account.usdt_balance),
            "total_profit": float(account.total_profit),
            "positions": [
                {
                    "symbol": p.symbol,
                    "quantity": float(p.quantity),
                    "average_price": float(p.average_price),
                    "current_price": float(p.current_price),
                    "current_value": float(p.current_value),
                    "unrealized_profit": float(p.unrealized_profit)
                }
                for p in positions
            ],
            "profit_rate": float(profit_rate),
            "total_value": float(total_value)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 계정 정보 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="계정 정보 조회 실패")


def get_transaction_history(session: Session, user_id: int, limit: int = 100) -> List[Transaction]:
    """거래 내역 조회"""
    try:
        return session.exec(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.timestamp.desc())
            .limit(limit)
        ).all()
    except Exception as e:
        logger.error(f"❌ 거래 내역 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="거래 내역 조회 실패")