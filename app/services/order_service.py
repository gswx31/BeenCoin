# app/services/order_service.py
"""
주문 서비스 - 원래 구조 (TradingAccount)
"""
from sqlmodel import Session, select
from app.models.database import Order, TradingAccount, Position, User, Transaction, OrderSide, OrderType, OrderStatus
from app.schemas.order import OrderCreate
from app.services.binance_service import get_current_price
from decimal import Decimal, InvalidOperation
from fastapi import HTTPException
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# 거래 수수료율 (0.1%)
FEE_RATE = Decimal("0.001")


async def create_order(
    session: Session,
    user_id: str,  # UUID string
    order_data: OrderCreate
) -> Order:
    """
    주문 생성 및 처리
    """
    
    logger.info(
        f"📝 주문 생성 시작: User={user_id}, "
        f"Symbol={order_data.symbol}, Side={order_data.side}, "
        f"Type={order_data.order_type}, Quantity={order_data.quantity}"
    )
    
    # ================================
    # 1. 입력 검증
    # ================================
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
        logger.error(f"❌ 입력 검증 실패: {e}")
        raise HTTPException(status_code=400, detail=f"잘못된 입력값: {str(e)}")
    
    # ================================
    # 2. 사용자 및 계정 조회
    # ================================
    try:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        
        account = session.exec(
            select(TradingAccount).where(TradingAccount.user_id == user_id)
        ).first()
        
        if not account:
            # 계정이 없으면 생성
            account = TradingAccount(
                user_id=user_id,
                balance=Decimal("1000000"),  # 초기 잔액 100만원
                total_profit=Decimal("0"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(account)
            session.commit()
            session.refresh(account)
            logger.info(f"✅ 새 거래 계정 생성: Account ID={account.id}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 계정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="계정 조회 중 오류 발생")
    
    # ================================
    # 3. 시장가 조회
    # ================================
    if order_data.order_type == OrderType.MARKET or order_data.order_type == "MARKET":
        try:
            execution_price = await get_current_price(order_data.symbol)
            logger.info(f"💵 현재 시장가: {order_data.symbol} = ${execution_price}")
        except Exception as e:
            logger.error(f"❌ 시장가 조회 실패: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"시장가격 조회 실패: {str(e)}"
            )
    else:
        execution_price = price
    
    # ================================
    # 4. 잔액/포지션 확인
    # ================================
    try:
        order_value = quantity * execution_price
        fee = order_value * FEE_RATE
        
        side_value = order_data.side.value if hasattr(order_data.side, 'value') else order_data.side
        
        if side_value == "BUY":
            # 매수: 잔액 확인
            total_cost = order_value + fee
            if account.balance < total_cost:
                raise HTTPException(
                    status_code=400,
                    detail=f"잔액 부족 - 보유: ${float(account.balance):.2f}, 필요: ${float(total_cost):.2f}"
                )
            logger.info(f"✅ 잔액 충분: ${account.balance} >= ${total_cost}")
        
        elif side_value == "SELL":
            # 매도: 포지션 확인
            position = session.exec(
                select(Position).where(
                    Position.account_id == account.id,
                    Position.symbol == order_data.symbol
                )
            ).first()
            
            if not position or position.quantity < quantity:
                available = position.quantity if position else Decimal("0")
                raise HTTPException(
                    status_code=400,
                    detail=f"수량 부족 - 보유: {float(available):.8f}, 필요: {float(quantity):.8f}"
                )
            logger.info(f"✅ 수량 충분: {position.quantity} >= {quantity}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 잔액/포지션 확인 실패: {e}")
        raise HTTPException(status_code=500, detail="잔액 확인 중 오류 발생")
    
    # ================================
    # 5. 주문 객체 생성
    # ================================
    try:
        new_order = Order(
            account_id=account.id,
            user_id=user_id,
            symbol=order_data.symbol,
            side=order_data.side.value if hasattr(order_data.side, 'value') else order_data.side,
            order_type=order_data.order_type.value if hasattr(order_data.order_type, 'value') else order_data.order_type,
            quantity=quantity,
            price=execution_price if order_data.order_type == OrderType.MARKET or order_data.order_type == "MARKET" else price,
            order_status=OrderStatus.PENDING,
            filled_quantity=Decimal("0"),
            average_price=None,
            fee=Decimal("0"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        session.add(new_order)
        session.commit()
        session.refresh(new_order)
        
        logger.info(f"✅ 주문 생성 완료: Order ID={new_order.id}")
    
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 주문 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"주문 생성 실패: {str(e)}")
    
    # ================================
    # 6. 시장가 주문 즉시 체결
    # ================================
    if order_data.order_type == OrderType.MARKET or order_data.order_type == "MARKET":
        try:
            _fill_market_order(session, new_order, account, execution_price, quantity, fee)
            logger.info(f"✅ 시장가 주문 체결 완료: Order ID={new_order.id}")
        except Exception as e:
            session.rollback()
            logger.error(f"❌ 주문 체결 실패: {e}")
            
            new_order.order_status = OrderStatus.REJECTED
            session.add(new_order)
            session.commit()
            
            raise HTTPException(status_code=500, detail=f"주문 체결 실패: {str(e)}")
    
    return new_order


def _fill_market_order(
    session: Session,
    order: Order,
    account: TradingAccount,
    price: Decimal,
    quantity: Decimal,
    fee: Decimal
):
    """
    시장가 주문 체결 처리
    """
    
    try:
        # 포지션 조회 또는 생성
        position = session.exec(
            select(Position).where(
                Position.account_id == account.id,
                Position.symbol == order.symbol
            )
        ).first()
        
        if not position:
            position = Position(
                account_id=account.id,
                symbol=order.symbol,
                quantity=Decimal("0"),
                average_price=Decimal("0"),
                current_price=price,
                current_value=Decimal("0"),
                unrealized_profit=Decimal("0"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(position)
            session.flush()
        
        # 매수 처리
        if order.side == "BUY":
            # 잔액 차감
            total_cost = quantity * price + fee
            account.balance -= total_cost
            
            # 포지션 업데이트
            if position.quantity > 0:
                # 평균가 계산
                old_cost = position.quantity * position.average_price
                new_cost = quantity * price
                new_quantity = position.quantity + quantity
                
                position.average_price = (old_cost + new_cost) / new_quantity
                position.quantity = new_quantity
            else:
                position.quantity = quantity
                position.average_price = price
            
            position.current_price = price
            position.current_value = position.quantity * price
            position.unrealized_profit = position.quantity * (price - position.average_price)
            
            logger.info(f"💰 매수 체결: Qty={quantity}, Avg=${position.average_price:.2f}, Balance=${account.balance:.2f}")
        
        # 매도 처리
        elif order.side == "SELL":
            # 수익 계산
            profit = quantity * (price - position.average_price)
            
            # 잔액 증가
            sell_amount = quantity * price
            account.balance += (sell_amount - fee)
            account.total_profit += profit
            
            # 포지션 업데이트
            position.quantity -= quantity
            
            if position.quantity > 0:
                position.current_price = price
                position.current_value = position.quantity * price
                position.unrealized_profit = position.quantity * (price - position.average_price)
            else:
                # 전체 청산
                position.quantity = Decimal("0")
                position.current_value = Decimal("0")
                position.unrealized_profit = Decimal("0")
                position.current_price = Decimal("0")
            
            logger.info(f"💸 매도 체결: Qty={quantity}, Profit=${profit:.2f}, Balance=${account.balance:.2f}")
        
        # 주문 상태 업데이트
        order.order_status = OrderStatus.FILLED
        order.filled_quantity = quantity
        order.average_price = price
        order.fee = fee
        order.updated_at = datetime.utcnow()
        
        # 거래 내역 기록
        transaction = Transaction(
            user_id=account.user_id,
            order_id=order.id,
            symbol=order.symbol,
            side=OrderSide(order.side),
            quantity=quantity,
            price=price,
            fee=fee,
            timestamp=datetime.utcnow()
        )
        
        # DB 커밋
        account.updated_at = datetime.utcnow()
        position.updated_at = datetime.utcnow()
        
        session.add_all([order, account, position, transaction])
        session.commit()
        
        session.refresh(order)
        session.refresh(account)
        session.refresh(position)
    
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 체결 처리 중 오류: {e}")
        raise


def get_user_orders(
    session: Session,
    user_id: str,  # UUID string
    symbol: str = None,
    status: str = None,
    limit: int = 100
) -> list:
    """
    사용자 주문 목록 조회
    """
    
    try:
        query = select(Order).where(Order.user_id == user_id)
        
        if symbol:
            query = query.where(Order.symbol == symbol)
        
        if status:
            query = query.where(Order.order_status == status)
        
        query = query.order_by(Order.created_at.desc()).limit(limit)
        
        orders = session.exec(query).all()
        
        logger.debug(f"📋 주문 목록 조회: User={user_id}, Count={len(orders)}")
        
        return list(orders)
    
    except Exception as e:
        logger.error(f"❌ 주문 목록 조회 실패: {e}")
        return []


def cancel_order(session: Session, order_id: int, user_id: str) -> Order:  # UUID string
    """
    주문 취소
    """
    
    try:
        order = session.get(Order, order_id)
        
        if not order:
            raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")
        
        if order.user_id != user_id:
            raise HTTPException(status_code=403, detail="권한이 없습니다")
        
        if order.order_status != OrderStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail=f"취소할 수 없는 주문 상태: {order.order_status}"
            )
        
        order.order_status = OrderStatus.CANCELLED
        order.updated_at = datetime.utcnow()
        
        session.add(order)
        session.commit()
        session.refresh(order)
        
        logger.info(f"🚫 주문 취소: Order ID={order_id}")
        
        return order
    
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 주문 취소 실패: {e}")
        raise HTTPException(status_code=500, detail=f"주문 취소 실패: {str(e)}")