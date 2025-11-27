# app/services/auto_stop_loss_take_profit.py
"""
주문 체결 시 자동 손절/익절 설정
- 지정가 매수 체결 → 자동으로 손절/익절 주문 생성
- OCO 주문: 손절 OR 익절 중 하나 체결 시 나머지 취소
"""
from datetime import datetime
from decimal import Decimal
import logging

from sqlmodel import Session, select

from app.models.database import Order, OrderSide, OrderStatus, OrderType, Position

logger = logging.getLogger(__name__)


async def auto_create_stop_loss_take_profit(
    session: Session,
    filled_order: Order,
    stop_loss_percent: Decimal = None,
    take_profit_percent: Decimal = None,
    stop_loss_price: Decimal = None,
    take_profit_price: Decimal = None,
):
    """
    체결된 매수 주문에 대해 자동으로 손절/익절 주문 생성

    Args:
        session: DB 세션
        filled_order: 체결된 주문
        stop_loss_percent: 손절 비율 (예: -3% → Decimal("3"))
        take_profit_percent: 익절 비율 (예: +5% → Decimal("5"))
        stop_loss_price: 손절 가격 (직접 지정)
        take_profit_price: 익절 가격 (직접 지정)

    Example:
        # 매수 체결 후 자동으로 -3% 손절, +5% 익절 설정
        await auto_create_stop_loss_take_profit(
            session,
            filled_order,
            stop_loss_percent=Decimal("3"),
            take_profit_percent=Decimal("5")
        )
    """

    # 매수 주문만 처리
    if filled_order.side != OrderSide.BUY:
        return

    # 이미 체결된 주문만 처리
    if filled_order.order_status != OrderStatus.FILLED:
        return

    try:
        # 평균 체결가
        avg_price = filled_order.average_price
        if not avg_price:
            logger.warning(f"⚠️ 평균 체결가 없음: Order #{filled_order.id}")
            return

        quantity = filled_order.filled_quantity

        # 손절가 계산
        if stop_loss_price:
            sl_price = stop_loss_price
        elif stop_loss_percent:
            sl_price = avg_price * (Decimal("1") - stop_loss_percent / Decimal("100"))
        else:
            sl_price = None

        # 익절가 계산
        if take_profit_price:
            tp_price = take_profit_price
        elif take_profit_percent:
            tp_price = avg_price * (Decimal("1") + take_profit_percent / Decimal("100"))
        else:
            tp_price = None

        created_orders = []

        # 손절 주문 생성
        if sl_price:
            stop_loss_order = Order(
                account_id=filled_order.account_id,
                user_id=filled_order.user_id,
                symbol=filled_order.symbol,
                side=OrderSide.SELL,
                order_type=OrderType.STOP_LOSS,
                order_status=OrderStatus.PENDING,
                quantity=quantity,
                stop_price=sl_price,
                filled_quantity=Decimal("0"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(stop_loss_order)
            created_orders.append(("STOP_LOSS", sl_price))

            logger.info(
                f"🔴 자동 손절 설정: {filled_order.symbol} "
                f"{quantity} @ ${sl_price:.2f} "
                f"({stop_loss_percent}% 하락)"
            )

        # 익절 주문 생성
        if tp_price:
            take_profit_order = Order(
                account_id=filled_order.account_id,
                user_id=filled_order.user_id,
                symbol=filled_order.symbol,
                side=OrderSide.SELL,
                order_type=OrderType.TAKE_PROFIT,
                order_status=OrderStatus.PENDING,
                quantity=quantity,
                stop_price=tp_price,
                filled_quantity=Decimal("0"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(take_profit_order)
            created_orders.append(("TAKE_PROFIT", tp_price))

            logger.info(
                f"🟢 자동 익절 설정: {filled_order.symbol} "
                f"{quantity} @ ${tp_price:.2f} "
                f"({take_profit_percent}% 상승)"
            )

        session.commit()

        if created_orders:
            logger.info(
                f"✅ 자동 손절/익절 설정 완료: {filled_order.symbol} " f"매수가 ${avg_price:.2f}"
            )

    except Exception as e:
        session.rollback()
        logger.error(f"❌ 자동 손절/익절 설정 실패: {e}")


async def cancel_opposite_order(session: Session, filled_order: Order):
    """
    OCO (One-Cancels-the-Other) 로직

    손절 OR 익절 중 하나가 체결되면 나머지 자동 취소

    Args:
        session: DB 세션
        filled_order: 방금 체결된 손절/익절 주문

    Example:
        손절 체결 → 익절 주문 자동 취소
        익절 체결 → 손절 주문 자동 취소
    """

    # 손절/익절 주문만 처리
    if filled_order.order_type not in [OrderType.STOP_LOSS, OrderType.TAKE_PROFIT]:
        return

    # 체결된 주문만 처리
    if filled_order.order_status != OrderStatus.FILLED:
        return

    try:
        # 반대 주문 타입 결정
        if filled_order.order_type == OrderType.STOP_LOSS:
            opposite_type = OrderType.TAKE_PROFIT
            opposite_name = "익절"
        else:
            opposite_type = OrderType.STOP_LOSS
            opposite_name = "손절"

        # 같은 심볼, 같은 수량의 반대 주문 찾기
        opposite_orders = session.exec(
            select(Order).where(
                Order.user_id == filled_order.user_id,
                Order.symbol == filled_order.symbol,
                Order.order_type == opposite_type,
                Order.order_status == OrderStatus.PENDING,
                Order.quantity == filled_order.quantity,
            )
        ).all()

        if not opposite_orders:
            logger.debug(f"반대 주문 없음: {opposite_name}")
            return

        # 모든 반대 주문 취소
        cancelled_count = 0
        for opposite_order in opposite_orders:
            opposite_order.order_status = OrderStatus.CANCELLED
            opposite_order.updated_at = datetime.utcnow()
            session.add(opposite_order)
            cancelled_count += 1

            logger.info(
                f"🚫 OCO 자동 취소: {opposite_name} 주문 #{opposite_order.id} "
                f"({filled_order.order_type.value} 체결로 인해)"
            )

        session.commit()

        if cancelled_count > 0:
            logger.info(
                f"✅ OCO 완료: {filled_order.order_type.value} 체결 → "
                f"{opposite_name} {cancelled_count}개 주문 취소"
            )

    except Exception as e:
        session.rollback()
        logger.error(f"❌ OCO 처리 실패: {e}")


async def check_and_create_missing_stop_loss_take_profit(session: Session, user_id: str):
    """
    기존 포지션 중 손절/익절이 없는 것들을 찾아서 자동 설정

    Args:
        session: DB 세션
        user_id: 사용자 ID

    Usage:
        # 사용자의 모든 포지션에 대해 손절/익절 확인 및 생성
        await check_and_create_missing_stop_loss_take_profit(session, user_id)
    """

    try:
        # 사용자의 포지션 조회
        from app.models.database import TradingAccount

        account = session.exec(
            select(TradingAccount).where(TradingAccount.user_id == user_id)
        ).first()

        if not account:
            return

        # 보유 중인 포지션
        positions = session.exec(
            select(Position).where(Position.account_id == account.id, Position.quantity > 0)
        ).all()

        for position in positions:
            # 해당 심볼의 대기 중인 손절/익절 주문 확인
            existing_orders = session.exec(
                select(Order).where(
                    Order.user_id == user_id,
                    Order.symbol == position.symbol,
                    Order.order_status == OrderStatus.PENDING,
                    Order.order_type.in_([OrderType.STOP_LOSS, OrderType.TAKE_PROFIT]),
                )
            ).all()

            has_stop_loss = any(o.order_type == OrderType.STOP_LOSS for o in existing_orders)
            has_take_profit = any(o.order_type == OrderType.TAKE_PROFIT for o in existing_orders)

            # 손절/익절이 없으면 자동 생성
            if not has_stop_loss or not has_take_profit:
                logger.warning(
                    f"⚠️ {position.symbol} 포지션에 "
                    f"{'손절' if not has_stop_loss else ''}"
                    f"{'/' if not has_stop_loss and not has_take_profit else ''}"
                    f"{'익절' if not has_take_profit else ''} 없음"
                )

                # 기본 손절/익절 비율 (설정 가능)
                DEFAULT_STOP_LOSS_PERCENT = Decimal("3")  # -3%
                DEFAULT_TAKE_PROFIT_PERCENT = Decimal("6")  # +6% (2:1 비율)

                # 가상의 체결 주문 생성 (평균 매수가 기반)
                virtual_order = Order(
                    id=f"virtual-{position.id}",
                    account_id=account.id,
                    user_id=user_id,
                    symbol=position.symbol,
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    order_status=OrderStatus.FILLED,
                    quantity=position.quantity,
                    average_price=position.average_price,
                    filled_quantity=position.quantity,
                )

                await auto_create_stop_loss_take_profit(
                    session,
                    virtual_order,
                    stop_loss_percent=DEFAULT_STOP_LOSS_PERCENT if not has_stop_loss else None,
                    take_profit_percent=(
                        DEFAULT_TAKE_PROFIT_PERCENT if not has_take_profit else None
                    ),
                )

    except Exception as e:
        logger.error(f"❌ 누락된 손절/익절 생성 실패: {e}")


async def get_related_orders(session: Session, order: Order) -> dict:
    """
    특정 주문과 연관된 주문들 조회

    Args:
        session: DB 세션
        order: 조회할 주문

    Returns:
        dict: {
            "original_buy": Order,  # 원래 매수 주문
            "stop_loss": Order,     # 손절 주문
            "take_profit": Order    # 익절 주문
        }
    """

    try:
        result = {"original_buy": None, "stop_loss": None, "take_profit": None}

        # 같은 심볼의 주문들 조회
        related_orders = session.exec(
            select(Order).where(
                Order.user_id == order.user_id,
                Order.symbol == order.symbol,
                Order.quantity == order.quantity,
            )
        ).all()

        for related_order in related_orders:
            if (
                related_order.side == OrderSide.BUY
                and related_order.order_status == OrderStatus.FILLED
            ):
                result["original_buy"] = related_order
            elif related_order.order_type == OrderType.STOP_LOSS:
                result["stop_loss"] = related_order
            elif related_order.order_type == OrderType.TAKE_PROFIT:
                result["take_profit"] = related_order

        return result

    except Exception as e:
        logger.error(f"❌ 연관 주문 조회 실패: {e}")
        return {"original_buy": None, "stop_loss": None, "take_profit": None}
