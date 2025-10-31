# app/services/futures_service.py
"""
선물 거래 서비스
"""
from sqlmodel import Session, select
from app.models.futures import (
    FuturesAccount, FuturesPosition, FuturesOrder, FuturesTransaction,
    FuturesPositionSide, FuturesOrderType, FuturesPositionStatus
)
from app.services.binance_service import get_current_price
from decimal import Decimal
from datetime import datetime
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


async def open_futures_position(
    session: Session,
    user_id: str,
    symbol: str,
    side: FuturesPositionSide,
    quantity: Decimal,
    leverage: int,
    order_type: FuturesOrderType = FuturesOrderType.MARKET,
    price: Decimal = None
) -> FuturesPosition:
    """
    선물 포지션 개설
    
    예시:
    - BTC 10x 롱 포지션
    - 수량: 0.1 BTC
    - 현재가: 50,000 USDT
    - 필요 증거금: 50,000 * 0.1 / 10 = 500 USDT
    
    Args:
        user_id: 사용자 ID
        symbol: 거래 심볼
        side: LONG or SHORT
        quantity: 계약 수량
        leverage: 레버리지 (1~125)
        order_type: 주문 타입
        price: 지정가 (LIMIT 주문만)
    
    Returns:
        FuturesPosition: 개설된 포지션
    """
    
    try:
        # 1. 계정 조회
        account = session.exec(
            select(FuturesAccount).where(FuturesAccount.user_id == user_id)
        ).first()
        
        if not account:
            # 선물 계정 생성
            account = FuturesAccount(
                user_id=user_id,
                balance=Decimal("1000000"),
                margin_used=Decimal("0"),
                total_profit=Decimal("0"),
                unrealized_pnl=Decimal("0"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(account)
            session.flush()
        
        # 2. 현재가 조회
        current_price = await get_current_price(symbol)
        entry_price = price if order_type == FuturesOrderType.LIMIT else current_price
        
        # 3. 필요 증거금 계산
        position_value = entry_price * quantity
        required_margin = position_value / Decimal(leverage)
        fee_rate = Decimal("0.0004")  # 0.04% (선물 수수료)
        fee = position_value * fee_rate
        total_required = required_margin + fee
        
        # 4. 잔액 확인
        if account.balance < total_required:
            raise HTTPException(
                status_code=400,
                detail=f"증거금 부족 (필요: {total_required:.2f} USDT, 보유: {account.balance:.2f} USDT)"
            )
        
        # 5. 청산 가격 계산
        liquidation_margin = required_margin * Decimal("0.9")
        if side == FuturesPositionSide.LONG:
            liquidation_price = entry_price - (liquidation_margin / quantity)
        else:  # SHORT
            liquidation_price = entry_price + (liquidation_margin / quantity)
        
        # 6. 포지션 생성
        position = FuturesPosition(
            account_id=account.id,
            symbol=symbol,
            side=side,
            status=FuturesPositionStatus.OPEN,
            leverage=leverage,
            quantity=quantity,
            entry_price=entry_price,
            mark_price=current_price,
            margin=required_margin,
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            liquidation_price=liquidation_price,
            fee=fee,
            opened_at=datetime.utcnow()
        )
        
        # 7. 계정 업데이트
        account.balance -= total_required
        account.margin_used += required_margin
        account.updated_at = datetime.utcnow()
        
        # 8. 포지션 저장 (먼저 ID 생성)
        session.add(position)
        session.add(account)
        session.flush()  # ✅ position.id 생성
        
        # 9. 거래 내역 기록 (position.id가 이제 존재함)
        transaction = FuturesTransaction(
            user_id=user_id,
            position_id=position.id,  # ✅ 이제 None이 아님
            symbol=symbol,
            side=side,
            action="OPEN",
            quantity=quantity,
            price=entry_price,
            leverage=leverage,
            pnl=Decimal("0"),
            fee=fee,
            timestamp=datetime.utcnow()
        )
        
        session.add(transaction)
        session.commit()
        session.refresh(position)
        session.refresh(account)
        
        logger.info(
            f"📈 선물 포지션 개설: {side.value} {symbol} "
            f"{quantity} @ {entry_price:.2f} USDT "
            f"({leverage}x 레버리지, 증거금: {required_margin:.2f} USDT)"
        )
        
        return position
    
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 선물 포지션 개설 실패: {e}")
        raise HTTPException(status_code=500, detail=f"포지션 개설 실패: {str(e)}")


async def close_futures_position(
    session: Session,
    user_id: str,
    position_id: str  # ✅ UUID
) -> dict:
    """
    선물 포지션 청산
    
    Args:
        session: DB 세션
        user_id: 사용자 ID
        position_id: 포지션 ID
    
    Returns:
        dict: 청산 결과 (실현 손익, 수익률 등)
    """
    
    try:
        # 1. 포지션 조회
        position = session.get(FuturesPosition, position_id)
        
        if not position:
            raise HTTPException(status_code=404, detail="포지션을 찾을 수 없습니다")
        
        if position.status != FuturesPositionStatus.OPEN:
            raise HTTPException(
                status_code=400,
                detail=f"청산할 수 없는 포지션 (상태: {position.status})"
            )
        
        # 계정 확인
        account = session.get(FuturesAccount, position.account_id)
        if account.user_id != user_id:
            raise HTTPException(status_code=403, detail="권한이 없습니다")
        
        # 2. 현재가 조회
        current_price = await get_current_price(position.symbol)
        
        # 3. 손익 계산
        if position.side == FuturesPositionSide.LONG:
            pnl = (current_price - position.entry_price) * position.quantity
        else:  # SHORT
            pnl = (position.entry_price - current_price) * position.quantity
        
        # 4. 수수료 계산
        position_value = current_price * position.quantity
        fee = position_value * Decimal("0.0004")
        net_pnl = pnl - fee
        
        # 5. 수익률 (ROE %)
        roe = (net_pnl / position.margin) * 100 if position.margin > 0 else Decimal("0")
        
        # 6. 포지션 업데이트
        position.status = FuturesPositionStatus.CLOSED
        position.mark_price = current_price
        position.realized_pnl = net_pnl
        position.closed_at = datetime.utcnow()
        
        # 7. 계정 업데이트
        account.balance += (position.margin + net_pnl)  # 증거금 반환 + 손익
        account.margin_used -= position.margin
        account.total_profit += net_pnl
        account.unrealized_pnl -= position.unrealized_pnl  # 미실현 손익 제거
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
            fee=fee,
            timestamp=datetime.utcnow()
        )
        
        session.add_all([position, account, transaction])
        session.commit()
        session.refresh(position)
        session.refresh(account)
        
        result = {
            "position_id": position.id,
            "symbol": position.symbol,
            "side": position.side.value,
            "entry_price": float(position.entry_price),
            "exit_price": float(current_price),
            "quantity": float(position.quantity),
            "leverage": position.leverage,
            "pnl": float(net_pnl),
            "roe_percent": float(roe),
            "fee": float(fee),
            "margin_returned": float(position.margin)
        }
        
        logger.info(
            f"💰 선물 포지션 청산: {position.symbol} "
            f"손익: {net_pnl:.2f} USDT ({roe:.2f}%)"
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 선물 포지션 청산 실패: {e}")
        raise HTTPException(status_code=500, detail=f"포지션 청산 실패: {str(e)}")


async def check_liquidations(session: Session):
    """
    청산 체크 (백그라운드 작업)
    
    - 모든 열린 포지션 체크
    - 현재가가 청산가에 도달하면 강제 청산
    """
    
    try:
        # 열린 포지션 조회
        open_positions = session.exec(
            select(FuturesPosition).where(
                FuturesPosition.status == FuturesPositionStatus.OPEN
            )
        ).all()
        
        for position in open_positions:
            current_price = await get_current_price(position.symbol)
            
            # 청산 조건 체크
            should_liquidate = False
            
            if position.side == FuturesPositionSide.LONG:
                # 롱: 현재가가 청산가 이하
                if current_price <= position.liquidation_price:
                    should_liquidate = True
            else:  # SHORT
                # 숏: 현재가가 청산가 이상
                if current_price >= position.liquidation_price:
                    should_liquidate = True
            
            if should_liquidate:
                # 강제 청산 실행
                await liquidate_position(session, position, current_price)
    
    except Exception as e:
        logger.error(f"❌ 청산 체크 실패: {e}")


async def liquidate_position(
    session: Session,
    position: FuturesPosition,
    liquidation_price: Decimal
):
    """
    강제 청산 실행
    
    - 증거금의 90%를 손실로 처리
    - 나머지 10%는 청산 수수료
    """
    
    try:
        account = session.get(FuturesAccount, position.account_id)
        
        # 손실 = 증거금의 90%
        loss = position.margin * Decimal("0.9")
        liquidation_fee = position.margin * Decimal("0.1")
        
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
        
        # 거래 내역 기록
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
            timestamp=datetime.utcnow()
        )
        
        session.add_all([position, account, transaction])
        session.commit()
        
        logger.warning(
            f"⚠️ 강제 청산: {position.symbol} {position.side.value} "
            f"손실: {loss:.2f} USDT (청산가: {liquidation_price:.2f})"
        )
    
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 강제 청산 실패: {e}")


async def update_positions_pnl(session: Session):
    """
    모든 포지션의 미실현 손익 업데이트 (백그라운드 작업)
    """
    
    try:
        open_positions = session.exec(
            select(FuturesPosition).where(
                FuturesPosition.status == FuturesPositionStatus.OPEN
            )
        ).all()
        
        for position in open_positions:
            current_price = await get_current_price(position.symbol)
            
            # 미실현 손익 계산
            if position.side == FuturesPositionSide.LONG:
                pnl = (current_price - position.entry_price) * position.quantity
            else:  # SHORT
                pnl = (position.entry_price - current_price) * position.quantity
            
            # 포지션 업데이트
            position.mark_price = current_price
            position.unrealized_pnl = pnl
            session.add(position)
        
        session.commit()
    
    except Exception as e:
        logger.error(f"❌ 미실현 손익 업데이트 실패: {e}")


def get_futures_positions(
    session: Session,
    user_id: str,
    status: FuturesPositionStatus = FuturesPositionStatus.OPEN
) -> list:
    """사용자의 선물 포지션 목록 조회"""
    
    try:
        account = session.exec(
            select(FuturesAccount).where(FuturesAccount.user_id == user_id)
        ).first()
        
        if not account:
            return []
        
        query = select(FuturesPosition).where(
            FuturesPosition.account_id == account.id
        )
        
        if status:
            query = query.where(FuturesPosition.status == status)
        
        positions = session.exec(
            query.order_by(FuturesPosition.opened_at.desc())
        ).all()
        
        return list(positions)
    
    except Exception as e:
        logger.error(f"❌ 포지션 조회 실패: {e}")
        return []