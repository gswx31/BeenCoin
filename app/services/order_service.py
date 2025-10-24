# app/services/order_service.py
"""
주문 서비스 - 안정화 버전
"""
from sqlmodel import Session, select
from app.models.database import Order, TradingAccount, Position, User
from app.schemas.order import OrderCreate
from app.services.binance_service import get_current_price, execute_market_order
from decimal import Decimal, InvalidOperation
from fastapi import HTTPException
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# 거래 수수료율 (0.1%)
FEE_RATE = Decimal("0.001")


class OrderServiceError(HTTPException):
    """주문 서비스 에러 기본 클래스"""
    pass


async def create_order(
    session: Session,
    user_id: int,
    order_data: OrderCreate
) -> Order:
    """
    주문 생성 및 처리
    
    Args:
        session: DB 세션
        user_id: 사용자 ID
        order_data: 주문 데이터
    
    Returns:
        Order: 생성된 주문
    
    Raises:
        HTTPException: 주문 실패 시
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
        raise HTTPException(
            status_code=400,
            detail=f"잘못된 입력값: {str(e)}"
        )
    
    # ================================
    # 2. 사용자 및 계정 조회
    # ================================
    try:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=404,
                detail="사용자를 찾을 수 없습니다"
            )
        
        account = session.exec(
            select(TradingAccount).where(TradingAccount.user_id == user_id)
        ).first()
        
        if not account:
            # 계정이 없으면 생성
            account = TradingAccount(
                user_id=user_id,
                balance=Decimal("1000000"),  # 초기 잔액 100만원
                total_profit=Decimal("0")
            )
            session.add(account)
            session.commit()
            session.refresh(account)
            logger.info(f"✅ 새 거래 계정 생성: Account ID={account.id}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 계정 조회 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail="계정 조회 중 오류 발생"
        )
    
    # ================================
    # 3. 시장가 조회
    # ================================
    try:
        if order_data.order_type == "MARKET":
            # ✅ 시장가 주문 - 현재가 조회
            current_price = await get_current_price(order_data.symbol)
            execution_price = current_price
            logger.info(f"💱 시장가 조회 성공: {order_data.symbol} = ${execution_price}")
        
        elif order_data.order_type == "LIMIT":
            # 지정가 주문
            if not price:
                raise HTTPException(
                    status_code=400,
                    detail="지정가 주문은 가격이 필요합니다"
                )
            execution_price = price
            logger.info(f"📌 지정가 설정: ${execution_price}")
        
        else:
            raise HTTPException(
                status_code=400,
                detail="지원하지 않는 주문 타입입니다"
            )
    
    except HTTPException as e:
        # ✅ 시장가 조회 실패를 사용자에게 명확히 전달
        logger.error(f"❌ 시장가 조회 실패: {e.detail}")
        raise HTTPException(
            status_code=503,
            detail=f"시장가격 조회 실패: {e.detail}"
        )
    except Exception as e:
        logger.error(f"❌ 예상치 못한 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"가격 조회 중 오류 발생: {str(e)}"
        )
    
    # ================================
    # 4. 잔액/포지션 확인
    # ================================
    try:
        if order_data.side == "BUY":
            # 매수 - 잔액 확인
            total_cost = quantity * execution_price
            fee = total_cost * FEE_RATE
            required_balance = total_cost + fee
            
            if account.balance < required_balance:
                logger.warning(
                    f"⚠️ 잔액 부족: "
                    f"보유 ${float(account.balance):.2f} / "
                    f"필요 ${float(required_balance):.2f}"
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"잔액이 부족합니다. "
                           f"보유: ${float(account.balance):.2f}, "
                           f"필요: ${float(required_balance):.2f}"
                )
        
        elif order_data.side == "SELL":
            # 매도 - 포지션 확인
            position = session.exec(
                select(Position).where(
                    Position.account_id == account.id,
                    Position.symbol == order_data.symbol
                )
            ).first()
            
            if not position or position.quantity < quantity:
                available = position.quantity if position else Decimal("0")
                logger.warning(
                    f"⚠️ 보유 수량 부족: "
                    f"보유 {float(available):.8f} / "
                    f"필요 {float(quantity):.8f}"
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"보유 수량이 부족합니다. "
                           f"보유: {float(available):.8f}, "
                           f"필요: {float(quantity):.8f}"
                )
        
        else:
            raise HTTPException(
                status_code=400,
                detail="지원하지 않는 주문 방향입니다 (BUY 또는 SELL)"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 잔액/포지션 확인 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail="잔액 확인 중 오류 발생"
        )
    
    # ================================
    # 5. 주문 생성
    # ================================
    try:
        # 수수료 계산
        order_value = quantity * execution_price
        fee = order_value * FEE_RATE
        
        # 주문 객체 생성
        new_order = Order(
            account_id=account.id,
            symbol=order_data.symbol,
            side=order_data.side,
            order_type=order_data.order_type,
            quantity=quantity,
            price=execution_price if order_data.order_type == "MARKET" else price,
            status="PENDING",
            fee=fee if order_data.order_type == "MARKET" else Decimal("0"),
            created_at=datetime.utcnow()
        )
        
        session.add(new_order)
        session.commit()
        session.refresh(new_order)
        
        logger.info(f"✅ 주문 생성 완료: Order ID={new_order.id}")
    
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 주문 생성 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail="주문 생성 중 오류 발생"
        )
    
    # ================================
    # 6. 주문 체결 (시장가인 경우)
    # ================================
    if order_data.order_type == "MARKET":
        try:
            # 체결 처리
            _fill_order(session, new_order, account, execution_price, quantity, fee)
            
            logger.info(
                f"✅ 시장가 주문 체결 완료: "
                f"Order ID={new_order.id}, Price=${execution_price}"
            )
        
        except Exception as e:
            session.rollback()
            logger.error(f"❌ 주문 체결 실패: {e}")
            
            # 주문 상태를 REJECTED로 변경
            new_order.status = "REJECTED"
            session.add(new_order)
            session.commit()
            
            raise HTTPException(
                status_code=500,
                detail=f"주문 체결 실패: {str(e)}"
            )
    
    return new_order


def _fill_order(
    session: Session,
    order: Order,
    account: TradingAccount,
    price: Decimal,
    quantity: Decimal,
    fee: Decimal
):
    """
    주문 체결 처리 (내부 함수)
    
    Args:
        session: DB 세션
        order: 주문 객체
        account: 계정 객체
        price: 체결 가격
        quantity: 체결 수량
        fee: 수수료
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
                current_value=Decimal("0"),
                unrealized_profit=Decimal("0")
            )
            session.add(position)
        
        # ================================
        # 매수 처리
        # ================================
        if order.side == "BUY":
            # 잔액 차감
            total_cost = quantity * price + fee
            account.balance -= total_cost
            
            # 포지션 업데이트
            if position.quantity > 0:
                # 기존 포지션이 있는 경우 - 평균가 계산
                total_cost_old = position.quantity * position.average_price
                total_cost_new = quantity * price
                new_total_quantity = position.quantity + quantity
                
                position.average_price = (total_cost_old + total_cost_new) / new_total_quantity
                position.quantity = new_total_quantity
            else:
                # 신규 포지션
                position.quantity = quantity
                position.average_price = price
            
            position.current_value = position.quantity * price
            position.unrealized_profit = position.quantity * (price - position.average_price)
            
            logger.info(
                f"💰 매수 체결: Qty={quantity}, "
                f"Avg Price=${position.average_price}, "
                f"Balance=${account.balance}"
            )
        
        # ================================
        # 매도 처리
        # ================================
        elif order.side == "SELL":
            # 수익 계산
            profit = quantity * (price - position.average_price)
            
            # 잔액 증가 (매도 금액 - 수수료)
            sell_amount = quantity * price
            account.balance += (sell_amount - fee)
            account.total_profit += profit
            
            # 포지션 업데이트
            position.quantity -= quantity
            
            if position.quantity > 0:
                position.current_value = position.quantity * price
                position.unrealized_profit = position.quantity * (price - position.average_price)
            else:
                # 포지션 전체 청산
                position.quantity = Decimal("0")
                position.current_value = Decimal("0")
                position.unrealized_profit = Decimal("0")
                position.average_price = Decimal("0")
            
            logger.info(
                f"💸 매도 체결: Qty={quantity}, "
                f"Profit=${profit}, "
                f"Balance=${account.balance}"
            )
        
        # 주문 상태 업데이트
        order.status = "FILLED"
        order.filled_at = datetime.utcnow()
        
        # DB 커밋
        session.add_all([order, account, position])
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
    user_id: int,
    symbol: str = None,
    status: str = None,
    limit: int = 100
) -> list[Order]:
    """
    사용자 주문 목록 조회
    
    Args:
        session: DB 세션
        user_id: 사용자 ID
        symbol: 필터링할 심볼 (선택)
        status: 필터링할 상태 (선택)
        limit: 최대 조회 개수
    
    Returns:
        list[Order]: 주문 목록
    """
    
    try:
        # 계정 조회
        account = session.exec(
            select(TradingAccount).where(TradingAccount.user_id == user_id)
        ).first()
        
        if not account:
            return []
        
        # 쿼리 생성
        query = select(Order).where(Order.account_id == account.id)
        
        if symbol:
            query = query.where(Order.symbol == symbol)
        
        if status:
            query = query.where(Order.status == status)
        
        query = query.order_by(Order.created_at.desc()).limit(limit)
        
        orders = session.exec(query).all()
        
        logger.debug(f"📋 주문 목록 조회: User={user_id}, Count={len(orders)}")
        return list(orders)
    
    except Exception as e:
        logger.error(f"❌ 주문 목록 조회 실패: {e}")
        return []


async def cancel_order(session: Session, user_id: int, order_id: int) -> Order:
    """
    주문 취소
    
    Args:
        session: DB 세션
        user_id: 사용자 ID
        order_id: 주문 ID
    
    Returns:
        Order: 취소된 주문
    
    Raises:
        HTTPException: 취소 실패 시
    """
    
    try:
        # 주문 조회
        order = session.get(Order, order_id)
        
        if not order:
            raise HTTPException(
                status_code=404,
                detail="주문을 찾을 수 없습니다"
            )
        
        # 권한 확인
        account = session.get(TradingAccount, order.account_id)
        if not account or account.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="주문을 취소할 권한이 없습니다"
            )
        
        # 상태 확인
        if order.status != "PENDING":
            raise HTTPException(
                status_code=400,
                detail=f"취소할 수 없는 주문 상태입니다: {order.status}"
            )
        
        # 취소 처리
        order.status = "CANCELLED"
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
        raise HTTPException(
            status_code=500,
            detail="주문 취소 중 오류 발생"
        )


def calculate_fee(quantity: Decimal, price: Decimal) -> Decimal:
    """
    거래 수수료 계산
    
    Args:
        quantity: 수량
        price: 가격
    
    Returns:
        Decimal: 수수료
    """
    return quantity * price * FEE_RATE