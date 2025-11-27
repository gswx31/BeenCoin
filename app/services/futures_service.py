# app/services/futures_service.py
"""
선물 거래 서비스 - 실제 거래소 로직 구현
=========================================

주요 개선사항:
1. 시장가 주문: 실제 체결 내역 기반 분할 체결
2. 지정가 주문: 실시간 부분 체결 지원
3. 레버리지 정확히 반영
4. 청산 로직 개선
"""

import logging
from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.futures import (
    FuturesAccount,
    FuturesOrderType,
    FuturesPosition,
    FuturesPositionSide,
    FuturesPositionStatus,
    FuturesTransaction,
)
from app.services.binance_service import (
    execute_market_order_with_real_trades,
    get_current_price,
)

logger = logging.getLogger(__name__)


# =====================================================
# 1. 선물 포지션 개설
# =====================================================


async def open_futures_position(
    session: Session,
    user_id: str,
    symbol: str,
    side: FuturesPositionSide,
    quantity: Decimal,
    leverage: int,
    order_type: FuturesOrderType = FuturesOrderType.MARKET,
    price: Decimal = None,
) -> FuturesPosition:
    """
    ⭐ 선물 포지션 개설 (실제 거래소 로직 반영)

    개선사항:
    - 시장가: 실제 체결 내역 기반 분할 체결
    - 지정가: PENDING 상태로 등록, 백그라운드 작업이 부분 체결
    - 레버리지: 100x → 거래량 100배 반영

    예시:
        BTC 10x 롱 포지션
        - 수량: 0.1 BTC
        - 레버리지: 10x
        → 실제 포지션: 1 BTC (0.1 * 10)

        현재가: 50,000 USDT
        - 필요 증거금: 5,000 USDT (50,000 * 1 / 10)
        - 청산가: ~45,000 USDT

    Args:
        user_id: 사용자 ID
        symbol: 거래 심볼 (BTCUSDT)
        side: LONG or SHORT
        quantity: 계약 수량 (레버리지 적용 전)
        leverage: 레버리지 (1~125)
        order_type: MARKET or LIMIT
        price: 지정가 (LIMIT만)

    Returns:
        FuturesPosition: 개설된 포지션
    """
    try:
        # 1. 계정 조회 또는 생성
        account = session.exec(
            select(FuturesAccount).where(FuturesAccount.user_id == user_id)
        ).first()

        if not account:
            # 선물 계정 생성 (초기 자본 100만원)
            account = FuturesAccount(
                user_id=user_id,
                balance=Decimal("1000000"),
                margin_used=Decimal("0"),
                total_profit=Decimal("0"),
                unrealized_pnl=Decimal("0"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(account)
            session.flush()
            logger.info(f"✅ 선물 계정 생성: User {user_id}, 잔액 1,000,000 USDT")

        # 2. 시장가 vs 지정가
        entry_price = None
        actual_quantity = quantity * Decimal(str(leverage))  # 레버리지 적용
        fill_details = []

        if order_type == FuturesOrderType.MARKET:
            # ✅ 수정: 올바른 인자 전달
            result = await execute_market_order_with_real_trades(
                symbol=symbol,
                side="BUY" if side == FuturesPositionSide.LONG else "SELL",  # ✅ 수정
                quantity=quantity,  # ✅ 원래 수량 전달 (레버리지는 함수 내부에서 적용)
                leverage=leverage,  # ✅ 레버리지 전달
            )

            entry_price = result["average_price"]
            fill_details = result["fills"]
            actual_quantity = result["actual_position_size"]  # ✅ 함수에서 계산된 실제 수량

            logger.info(f"✅ 시장가 체결: {len(fill_details)}건, 평균가: {entry_price:.2f}")

        elif order_type == FuturesOrderType.LIMIT:
            # ✅ 지정가 주문 처리
            if price is None:
                raise HTTPException(status_code=400, detail="지정가 주문은 price가 필요합니다")

            entry_price = price
            actual_quantity = quantity * Decimal(str(leverage))

            logger.info(
                f"📝 지정가 등록: {quantity} {symbol} @ ${price:.2f} "
                f"(레버리지 {leverage}x → 실제 {actual_quantity})"
            )
        # 3. 필요 증거금 계산
        position_value = entry_price * actual_quantity
        required_margin = position_value / Decimal(str(leverage))

        # 수수료 (0.04%)
        fee_rate = Decimal("0.0004")
        fee = position_value * fee_rate

        total_required = required_margin + fee

        # 4. 잔액 확인
        if account.balance < total_required:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"증거금 부족\n"
                    f"필요: {total_required:.2f} USDT\n"
                    f"보유: {account.balance:.2f} USDT\n"
                    f"부족: {total_required - account.balance:.2f} USDT"
                ),
            )

        # 5. 청산 가격 계산 (증거금의 90% 손실 시)
        liquidation_margin = required_margin * Decimal("0.9")

        if side == FuturesPositionSide.LONG:
            # 롱: 가격 하락 시 청산
            liquidation_price = entry_price - (liquidation_margin / actual_quantity)
        else:
            # 숏: 가격 상승 시 청산
            liquidation_price = entry_price + (liquidation_margin / actual_quantity)

        # 6. 포지션 생성
        position_status = (
            FuturesPositionStatus.OPEN
            if order_type == FuturesOrderType.MARKET
            else FuturesPositionStatus.PENDING
        )

        position = FuturesPosition(
            account_id=account.id,
            symbol=symbol,
            side=side,
            status=position_status,
            leverage=leverage,
            quantity=actual_quantity,  # ⭐ 레버리지 적용된 수량
            entry_price=entry_price,
            mark_price=entry_price,
            margin=required_margin,
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            liquidation_price=liquidation_price,
            fee=fee,
            opened_at=datetime.utcnow(),
        )

        # 7. 계정 업데이트
        account.balance -= total_required
        account.margin_used += required_margin
        account.updated_at = datetime.utcnow()

        # 8. DB 저장
        session.add(position)
        session.add(account)
        session.flush()  # position.id 생성

        # 9. 거래 내역 기록
        transaction = FuturesTransaction(
            user_id=user_id,
            position_id=position.id,
            symbol=symbol,
            side=side,
            action="OPEN",
            quantity=actual_quantity,  # 실제 포지션 크기
            price=entry_price,
            leverage=leverage,
            pnl=Decimal("0"),
            fee=fee,
            timestamp=datetime.utcnow(),
        )

        session.add(transaction)
        session.commit()
        session.refresh(position)
        session.refresh(account)

        logger.info(
            f"✅ 선물 포지션 개설 완료:\n"
            f"   - ID: {position.id}\n"
            f"   - {side.value} {symbol}\n"
            f"   - 수량: {actual_quantity} (원래 {quantity} × {leverage}x)\n"
            f"   - 진입가: ${entry_price:.2f}\n"
            f"   - 증거금: {required_margin:.2f} USDT\n"
            f"   - 청산가: ${liquidation_price:.2f}\n"
            f"   - 상태: {position_status.value}"
        )

        return position

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 선물 포지션 개설 실패: {e}")
        raise HTTPException(status_code=500, detail=f"포지션 개설 실패: {str(e)}")


# =====================================================
# 2. 선물 포지션 청산
# =====================================================


async def close_futures_position(session: Session, user_id: str, position_id: str) -> dict:
    """
    선물 포지션 청산

    - 현재가로 즉시 청산
    - 실현 손익 계산
    - 증거금 + 손익 반환

    Args:
        session: DB 세션
        user_id: 사용자 ID
        position_id: 포지션 ID

    Returns:
        dict: 청산 결과
    """
    try:
        # 1. 포지션 조회
        position = session.get(FuturesPosition, position_id)

        if not position:
            raise HTTPException(status_code=404, detail="포지션을 찾을 수 없습니다")

        if position.status != FuturesPositionStatus.OPEN:
            raise HTTPException(
                status_code=400, detail=f"청산할 수 없는 포지션 (상태: {position.status.value})"
            )

        # 계정 권한 확인
        account = session.get(FuturesAccount, position.account_id)
        if account.user_id != user_id:
            raise HTTPException(status_code=403, detail="권한이 없습니다")

        # 2. 현재가 조회
        current_price = await get_current_price(position.symbol)

        # 3. 손익 계산
        if position.side == FuturesPositionSide.LONG:
            # 롱: (현재가 - 진입가) × 수량
            pnl = (current_price - position.entry_price) * position.quantity
        else:
            # 숏: (진입가 - 현재가) × 수량
            pnl = (position.entry_price - current_price) * position.quantity

        # 4. 수수료 계산
        position_value = current_price * position.quantity
        exit_fee = position_value * Decimal("0.0004")

        # 순손익 = 손익 - 진입수수료 - 청산수수료
        net_pnl = pnl - exit_fee

        # 5. 수익률 (ROE %)
        roe = (net_pnl / position.margin) * 100 if position.margin > 0 else Decimal("0")

        # 6. 포지션 업데이트
        position.status = FuturesPositionStatus.CLOSED
        position.mark_price = current_price
        position.realized_pnl = net_pnl
        position.closed_at = datetime.utcnow()

        # 7. 계정 업데이트
        # 증거금 반환 + 순손익
        account.balance += position.margin + net_pnl
        account.margin_used -= position.margin
        account.total_profit += net_pnl
        account.unrealized_pnl -= position.unrealized_pnl
        account.updated_at = datetime.utcnow()

        # 8. 거래 내역 기록
        transaction = FuturesTransaction(
            user_id=user_id,
            position_id=position.id,
            symbol=position.symbol,
            side=position.side,
            action="CLOSE",
            quantity=position.quantity,
            price=current_price,
            leverage=position.leverage,
            pnl=net_pnl,
            fee=exit_fee,
            timestamp=datetime.utcnow(),
        )

        session.add_all([position, account, transaction])
        session.commit()

        logger.info(
            f"✅ 선물 포지션 청산:\n"
            f"   - ID: {position.id}\n"
            f"   - {position.side.value} {position.symbol}\n"
            f"   - 진입가: ${position.entry_price:.2f}\n"
            f"   - 청산가: ${current_price:.2f}\n"
            f"   - 손익: {net_pnl:.2f} USDT ({roe:.2f}%)\n"
            f"   - 반환 증거금: {position.margin:.2f} USDT"
        )

        return {
            "position_id": position.id,
            "symbol": position.symbol,
            "side": position.side.value,
            "entry_price": float(position.entry_price),
            "exit_price": float(current_price),
            "quantity": float(position.quantity),
            "pnl": float(net_pnl),
            "roe_percent": float(roe),
            "margin_returned": float(position.margin),
            "total_fees": float(position.fee + exit_fee),
        }

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 선물 포지션 청산 실패: {e}")
        raise HTTPException(status_code=500, detail=f"포지션 청산 실패: {str(e)}")


# =====================================================
# 3. 강제 청산 (Liquidation)
# =====================================================


async def liquidate_position(session: Session, position: FuturesPosition):
    """
    강제 청산

    청산가에 도달하면 자동으로 포지션 청산
    - 증거금 전액 손실
    - 추가 수수료 부과
    """
    try:
        account = session.get(FuturesAccount, position.account_id)
        liquidation_price = position.liquidation_price

        # 손실액 = 증거금
        loss = position.margin

        # 강제 청산 수수료 (0.1%)
        liquidation_fee = (liquidation_price * position.quantity) * Decimal("0.001")

        # 포지션 업데이트
        position.status = FuturesPositionStatus.LIQUIDATED
        position.mark_price = liquidation_price
        position.realized_pnl = -loss
        position.closed_at = datetime.utcnow()

        # 계정 업데이트 (증거금 손실)
        account.margin_used -= position.margin
        account.total_profit -= loss
        account.unrealized_pnl -= position.unrealized_pnl
        account.updated_at = datetime.utcnow()

        # 거래 내역
        transaction = FuturesTransaction(
            user_id=account.user_id,
            position_id=position.id,
            symbol=position.symbol,
            side=position.side,
            action="LIQUIDATION",
            quantity=position.quantity,
            price=liquidation_price,
            leverage=position.leverage,
            pnl=-loss,
            fee=liquidation_fee,
            timestamp=datetime.utcnow(),
        )

        session.add_all([position, account, transaction])
        session.commit()

        logger.warning(
            f"⚠️ 강제 청산 발생:\n"
            f"   - ID: {position.id}\n"
            f"   - {position.side.value} {position.symbol}\n"
            f"   - 청산가: ${liquidation_price:.2f}\n"
            f"   - 손실: {loss:.2f} USDT (증거금 전액)"
        )

    except Exception as e:
        session.rollback()
        logger.error(f"❌ 강제 청산 실패: {e}")


# =====================================================
# 4. 백그라운드 작업 - 미실현 손익 업데이트
# =====================================================


async def update_positions_pnl(session: Session):
    """
    모든 포지션의 미실현 손익 업데이트

    5초마다 실행되는 백그라운드 작업
    """
    try:
        open_positions = session.exec(
            select(FuturesPosition).where(FuturesPosition.status == FuturesPositionStatus.OPEN)
        ).all()

        for position in open_positions:
            try:
                current_price = await get_current_price(position.symbol)

                # 미실현 손익 계산
                if position.side == FuturesPositionSide.LONG:
                    pnl = (current_price - position.entry_price) * position.quantity
                else:
                    pnl = (position.entry_price - current_price) * position.quantity

                # 포지션 업데이트
                position.mark_price = current_price
                position.unrealized_pnl = pnl
                session.add(position)

            except Exception as e:
                logger.error(f"❌ 포지션 {position.id} 업데이트 실패: {e}")
                continue

        session.commit()

    except Exception as e:
        logger.error(f"❌ 미실현 손익 업데이트 실패: {e}")


# =====================================================
# 5. 포지션 조회
# =====================================================


def get_futures_positions(
    session: Session, user_id: str, status: FuturesPositionStatus = None
) -> list:
    """
    사용자의 선물 포지션 목록 조회

    Args:
        session: DB 세션
        user_id: 사용자 ID
        status: 포지션 상태 필터 (None이면 전체)

    Returns:
        List[FuturesPosition]: 포지션 리스트
    """
    try:
        account = session.exec(
            select(FuturesAccount).where(FuturesAccount.user_id == user_id)
        ).first()

        if not account:
            return []

        query = select(FuturesPosition).where(FuturesPosition.account_id == account.id)

        if status:
            query = query.where(FuturesPosition.status == status)

        positions = session.exec(query.order_by(FuturesPosition.opened_at.desc())).all()

        return list(positions)

    except Exception as e:
        logger.error(f"❌ 포지션 조회 실패: {e}")
        return []
