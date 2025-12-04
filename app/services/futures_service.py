# app/services/futures_service.py
# =============================================================================
# 선물 거래 서비스 - 수정판
# - 100% 주문 시 수수료 선차감
# - 지정가 주문 유리한 가격 체결
# =============================================================================
"""
선물 거래 핵심 서비스

수정 사항:
1. 100% 주문 시 수수료를 먼저 차감하고 증거금 계산
2. 지정가 주문 시 지정가보다 유리한 가격에 체결
"""
from datetime import datetime
from decimal import Decimal
import logging
from uuid import uuid4

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.database import User
from app.models.futures import (
    FuturesAccount,
    FuturesOrder,
    FuturesOrderType,
    FuturesPosition,
    FuturesPositionSide,
    FuturesPositionStatus,
    FuturesTransaction,
)
from app.models.futures_fills import FuturesFill
from app.services.binance_service import get_current_price, get_recent_trades

logger = logging.getLogger(__name__)

# 수수료율
FEE_RATE = Decimal("0.0004")  # 0.04%


# =====================================================
# 선물 계정 관리
# =====================================================

def get_or_create_futures_account(session: Session, user_id: str) -> FuturesAccount:
    """선물 계정 조회 또는 생성"""
    account = session.exec(
        select(FuturesAccount).where(FuturesAccount.user_id == user_id)
    ).first()

    if not account:
        account = FuturesAccount(
            user_id=user_id,
            balance=Decimal("10000"),  # 초기 잔액
            margin_used=Decimal("0"),
            unrealized_pnl=Decimal("0"),
            total_profit=Decimal("0"),
        )
        session.add(account)
        session.commit()
        session.refresh(account)
        logger.info(f"✅ 선물 계정 생성: User {user_id}")

    return account


# =====================================================
# ⭐ 최대 주문 가능 수량 계산 (수수료 포함)
# =====================================================

def calculate_max_quantity(
    available_balance: Decimal,
    price: Decimal,
    leverage: int,
) -> dict:
    """
    최대 주문 가능 수량 계산 (수수료 포함)
    
    100% 주문 시 수수료를 먼저 차감하고 계산
    
    공식:
    - 포지션 가치 = 수량 × 가격 × 레버리지
    - 필요 증거금 = 포지션 가치 / 레버리지 = 수량 × 가격
    - 수수료 = 포지션 가치 × 0.0004 = 수량 × 가격 × 레버리지 × 0.0004
    - 총 필요 = 증거금 + 수수료 = 수량 × 가격 × (1 + 레버리지 × 0.0004)
    
    따라서:
    - 최대 수량 = 잔액 / (가격 × (1 + 레버리지 × 0.0004))
    """
    if price <= 0 or leverage <= 0:
        return {"max_quantity": Decimal("0"), "max_margin": Decimal("0"), "fee": Decimal("0")}
    
    # 수수료 승수 = 1 + (레버리지 × 수수료율)
    fee_multiplier = Decimal("1") + (Decimal(str(leverage)) * FEE_RATE)
    
    # 최대 수량 (원래 입력 수량 기준, 레버리지 적용 전)
    max_quantity = available_balance / (price * fee_multiplier)
    
    # 실제 포지션 크기 (레버리지 적용)
    actual_position_size = max_quantity * Decimal(str(leverage))
    
    # 포지션 가치
    position_value = actual_position_size * price
    
    # 필요 증거금
    max_margin = position_value / Decimal(str(leverage))
    
    # 수수료
    fee = position_value * FEE_RATE
    
    return {
        "max_quantity": max_quantity,
        "max_margin": max_margin,
        "fee": fee,
        "position_value": position_value,
        "total_required": max_margin + fee,
    }


# =====================================================
# ⭐ 지정가 주문 - 유리한 가격 체결
# =====================================================

async def execute_limit_order_with_better_price(
    symbol: str,
    side: str,  # "BUY" or "SELL"
    quantity: Decimal,
    limit_price: Decimal,
    leverage: int,
) -> dict:
    """
    지정가 주문 체결 - 유리한 가격에 체결
    
    - 매수(LONG): 지정가 이하의 체결 가격 사용
    - 매도(SHORT): 지정가 이상의 체결 가격 사용
    
    실제 거래소처럼 호가창/체결 내역에서 유리한 가격 찾기
    """
    try:
        # 최근 체결 내역 조회
        trades = await get_recent_trades(symbol, limit=100)
        
        if not trades:
            # 체결 내역 없으면 지정가 그대로 사용
            return {
                "can_fill": True,
                "fill_price": limit_price,
                "fills": [{"price": limit_price, "quantity": quantity, "timestamp": datetime.utcnow().isoformat()}],
            }
        
        # 유리한 체결 찾기
        fills = []
        remaining_qty = quantity * Decimal(str(leverage))
        total_cost = Decimal("0")
        
        for trade in trades:
            trade_price = Decimal(str(trade.get("price", trade.get("p", "0"))))
            trade_qty = Decimal(str(trade.get("qty", trade.get("q", "0"))))
            
            # 가격 조건 확인
            if side == "BUY":
                # 매수: 지정가 이하에서만 체결
                if trade_price > limit_price:
                    continue
            else:
                # 매도: 지정가 이상에서만 체결
                if trade_price < limit_price:
                    continue
            
            # 체결
            fill_qty = min(remaining_qty, trade_qty)
            fills.append({
                "price": float(trade_price),
                "quantity": float(fill_qty),
                "timestamp": trade.get("time", datetime.utcnow().isoformat()),
            })
            
            total_cost += trade_price * fill_qty
            remaining_qty -= fill_qty
            
            if remaining_qty <= 0:
                break
        
        if not fills:
            # 유리한 가격 없음 → PENDING 상태로 대기
            return {
                "can_fill": False,
                "fill_price": limit_price,
                "fills": [],
                "message": "지정가 조건 미충족, 대기 주문으로 등록",
            }
        
        if remaining_qty > 0:
            # 부분 체결
            filled_qty = (quantity * Decimal(str(leverage))) - remaining_qty
            avg_price = total_cost / filled_qty if filled_qty > 0 else limit_price
            
            return {
                "can_fill": True,
                "partial": True,
                "fill_price": avg_price,
                "filled_quantity": filled_qty,
                "remaining_quantity": remaining_qty,
                "fills": fills,
            }
        
        # 완전 체결
        filled_qty = quantity * Decimal(str(leverage))
        avg_price = total_cost / filled_qty
        
        return {
            "can_fill": True,
            "partial": False,
            "fill_price": avg_price,
            "filled_quantity": filled_qty,
            "fills": fills,
        }
        
    except Exception as e:
        logger.error(f"지정가 체결 확인 실패: {e}")
        # 오류 시 지정가 그대로 사용
        return {
            "can_fill": True,
            "fill_price": limit_price,
            "fills": [{"price": float(limit_price), "quantity": float(quantity * leverage), "timestamp": datetime.utcnow().isoformat()}],
        }


# =====================================================
# 시장가 체결 (실제 체결 내역 기반)
# =====================================================

async def execute_market_order_with_real_trades(
    symbol: str,
    side: str,
    quantity: Decimal,
    leverage: int,
) -> dict:
    """
    시장가 주문 체결 - 실제 체결 내역 기반
    
    바이낸스 최근 체결 내역을 사용하여 현실적인 체결 시뮬레이션
    """
    try:
        trades = await get_recent_trades(symbol, limit=100)
        
        if not trades:
            current_price = await get_current_price(symbol)
            actual_qty = quantity * Decimal(str(leverage))
            return {
                "average_price": current_price,
                "actual_position_size": actual_qty,
                "fills": [{"price": float(current_price), "quantity": float(actual_qty), "timestamp": datetime.utcnow().isoformat()}],
            }
        
        # 체결 시뮬레이션
        fills = []
        remaining_qty = quantity * Decimal(str(leverage))
        total_cost = Decimal("0")
        
        for trade in trades:
            trade_price = Decimal(str(trade.get("price", trade.get("p", "0"))))
            trade_qty = Decimal(str(trade.get("qty", trade.get("q", "0"))))
            
            fill_qty = min(remaining_qty, trade_qty)
            fills.append({
                "price": float(trade_price),
                "quantity": float(fill_qty),
                "timestamp": trade.get("time", datetime.utcnow().isoformat()),
            })
            
            total_cost += trade_price * fill_qty
            remaining_qty -= fill_qty
            
            if remaining_qty <= 0:
                break
        
        # 남은 수량이 있으면 마지막 가격으로 채움
        if remaining_qty > 0 and trades:
            last_price = Decimal(str(trades[-1].get("price", trades[-1].get("p", "0"))))
            fills.append({
                "price": float(last_price),
                "quantity": float(remaining_qty),
                "timestamp": datetime.utcnow().isoformat(),
            })
            total_cost += last_price * remaining_qty
        
        actual_qty = quantity * Decimal(str(leverage))
        avg_price = total_cost / actual_qty if actual_qty > 0 else Decimal("0")
        
        return {
            "average_price": avg_price,
            "actual_position_size": actual_qty,
            "fills": fills,
        }
        
    except Exception as e:
        logger.error(f"시장가 체결 실패: {e}")
        current_price = await get_current_price(symbol)
        actual_qty = quantity * Decimal(str(leverage))
        return {
            "average_price": current_price,
            "actual_position_size": actual_qty,
            "fills": [{"price": float(current_price), "quantity": float(actual_qty), "timestamp": datetime.utcnow().isoformat()}],
        }


# =====================================================
# ⭐ 선물 포지션 개설 (수정판)
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
    선물 포지션 개설 (수정판)
    
    수정 사항:
    1. 100% 주문 시 수수료를 먼저 차감
    2. 지정가 주문은 유리한 가격에 체결
    """
    try:
        # 1. 계정 조회/생성
        account = get_or_create_futures_account(session, user_id)
        
        # 2. 시장가/지정가 처리
        entry_price = None
        actual_quantity = quantity * Decimal(str(leverage))
        fill_details = []
        position_status = FuturesPositionStatus.OPEN
        
        if order_type == FuturesOrderType.MARKET:
            # 시장가: 즉시 체결
            result = await execute_market_order_with_real_trades(
                symbol=symbol,
                side="BUY" if side == FuturesPositionSide.LONG else "SELL",
                quantity=quantity,
                leverage=leverage,
            )
            entry_price = result["average_price"]
            fill_details = result["fills"]
            actual_quantity = result["actual_position_size"]
            
            logger.info(f"✅ 시장가 체결: {len(fill_details)}건, 평균가: {entry_price:.2f}")
            
        elif order_type == FuturesOrderType.LIMIT:
            if price is None:
                raise HTTPException(status_code=400, detail="지정가 주문은 price가 필요합니다")
            
            # ⭐ 지정가: 유리한 가격 체결 시도
            result = await execute_limit_order_with_better_price(
                symbol=symbol,
                side="BUY" if side == FuturesPositionSide.LONG else "SELL",
                quantity=quantity,
                limit_price=price,
                leverage=leverage,
            )
            
            if result["can_fill"]:
                # 즉시 체결 가능
                entry_price = result["fill_price"]
                fill_details = result.get("fills", [])
                
                if result.get("partial"):
                    # 부분 체결 → PENDING 상태
                    position_status = FuturesPositionStatus.PENDING
                    logger.info(f"⏳ 지정가 부분 체결: {result['filled_quantity']} / {actual_quantity}")
                else:
                    logger.info(f"✅ 지정가 즉시 체결: 평균가 ${entry_price:.2f} (지정가 ${price:.2f})")
            else:
                # 체결 불가 → PENDING 상태로 대기
                entry_price = price
                position_status = FuturesPositionStatus.PENDING
                logger.info(f"📝 지정가 대기: {quantity} @ ${price:.2f}")
        
        # 3. ⭐ 증거금 및 수수료 계산 (수수료 선차감 방식)
        position_value = entry_price * actual_quantity
        required_margin = position_value / Decimal(str(leverage))
        fee = position_value * FEE_RATE
        total_required = required_margin + fee
        
        # 4. ⭐ 잔액 확인 (수정: 수수료 포함 확인)
        if account.balance < total_required:
            # 수수료를 차감한 최대 가능 금액 계산
            max_info = calculate_max_quantity(account.balance, entry_price, leverage)
            
            raise HTTPException(
                status_code=400,
                detail=(
                    f"잔액 부족\n"
                    f"필요: {total_required:.2f} USDT (증거금 {required_margin:.2f} + 수수료 {fee:.2f})\n"
                    f"보유: {account.balance:.2f} USDT\n"
                    f"최대 주문 가능: {max_info['max_quantity']:.6f} {symbol.replace('USDT', '')}"
                ),
            )
        
        # 5. 청산가 계산
        liquidation_margin = required_margin * Decimal("0.9")
        
        if side == FuturesPositionSide.LONG:
            liquidation_price = entry_price - (liquidation_margin / actual_quantity)
        else:
            liquidation_price = entry_price + (liquidation_margin / actual_quantity)
        
        # 6. 포지션 생성
        position = FuturesPosition(
            account_id=account.id,
            symbol=symbol,
            side=side,
            status=position_status,
            leverage=leverage,
            quantity=actual_quantity,
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
        session.flush()
        
        # 9. 체결 내역 기록
        for fill in fill_details:
            fill_record = FuturesFill(
                position_id=str(position.id),
                price=Decimal(str(fill["price"])),
                quantity=Decimal(str(fill["quantity"])),
                timestamp=datetime.fromisoformat(fill["timestamp"]) if isinstance(fill["timestamp"], str) else fill["timestamp"],
            )
            session.add(fill_record)
        
        # 10. 거래 내역 기록
        transaction = FuturesTransaction(
            user_id=user_id,
            position_id=position.id,
            symbol=symbol,
            side=side,
            action="OPEN" if position_status == FuturesPositionStatus.OPEN else "PENDING",
            quantity=actual_quantity,
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
            f"✅ 선물 포지션 {'개설' if position_status == FuturesPositionStatus.OPEN else '대기 등록'}:\n"
            f"   - ID: {position.id}\n"
            f"   - {side.value} {symbol}\n"
            f"   - 수량: {actual_quantity} ({quantity} × {leverage}x)\n"
            f"   - 진입가: ${entry_price:.2f}\n"
            f"   - 증거금: {required_margin:.2f} USDT\n"
            f"   - 수수료: {fee:.2f} USDT\n"
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
# 선물 포지션 청산
# =====================================================

async def close_futures_position(session: Session, user_id: str, position_id: str) -> dict:
    """선물 포지션 청산"""
    try:
        position = session.get(FuturesPosition, position_id)
        
        if not position:
            raise HTTPException(status_code=404, detail="포지션을 찾을 수 없습니다")
        
        if position.status not in [FuturesPositionStatus.OPEN, FuturesPositionStatus.PENDING]:
            raise HTTPException(
                status_code=400, 
                detail=f"청산할 수 없는 포지션 (상태: {position.status.value})"
            )
        
        account = session.get(FuturesAccount, position.account_id)
        if account.user_id != user_id:
            raise HTTPException(status_code=403, detail="권한이 없습니다")
        
        # PENDING 상태면 취소 처리
        if position.status == FuturesPositionStatus.PENDING:
            position.status = FuturesPositionStatus.CLOSED
            position.closed_at = datetime.utcnow()
            position.realized_pnl = Decimal("0")
            
            # 증거금 + 수수료 반환
            refund = position.margin + position.fee
            account.balance += refund
            account.margin_used -= position.margin
            account.updated_at = datetime.utcnow()
            
            transaction = FuturesTransaction(
                user_id=user_id,
                position_id=position.id,
                symbol=position.symbol,
                side=position.side,
                action="CANCELLED",
                quantity=position.quantity,
                price=position.entry_price,
                leverage=position.leverage,
                pnl=Decimal("0"),
                fee=Decimal("0"),
                timestamp=datetime.utcnow(),
            )
            
            session.add_all([position, account, transaction])
            session.commit()
            
            return {
                "message": "대기 주문이 취소되었습니다",
                "position_id": str(position.id),
                "refunded": float(refund),
            }
        
        # OPEN 상태: 청산 처리
        current_price = await get_current_price(position.symbol)
        
        if position.side == FuturesPositionSide.LONG:
            pnl = (current_price - position.entry_price) * position.quantity
        else:
            pnl = (position.entry_price - current_price) * position.quantity
        
        position_value = current_price * position.quantity
        exit_fee = position_value * FEE_RATE
        net_pnl = pnl - exit_fee
        roe = (net_pnl / position.margin) * 100 if position.margin > 0 else Decimal("0")
        
        position.status = FuturesPositionStatus.CLOSED
        position.mark_price = current_price
        position.realized_pnl = net_pnl
        position.closed_at = datetime.utcnow()
        
        account.balance += position.margin + net_pnl
        account.margin_used -= position.margin
        account.total_profit += net_pnl
        account.unrealized_pnl -= position.unrealized_pnl
        account.updated_at = datetime.utcnow()
        
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
            f"✅ 포지션 청산:\n"
            f"   - ID: {position.id}\n"
            f"   - {position.side.value} {position.symbol}\n"
            f"   - 진입가: ${position.entry_price:.2f}\n"
            f"   - 청산가: ${current_price:.2f}\n"
            f"   - 손익: {net_pnl:+.2f} USDT ({roe:+.2f}%)"
        )
        
        return {
            "message": "포지션이 청산되었습니다",
            "position_id": str(position.id),
            "entry_price": float(position.entry_price),
            "exit_price": float(current_price),
            "pnl": float(net_pnl),
            "roe_percent": float(roe),
            "fee": float(exit_fee),
        }
        
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 포지션 청산 실패: {e}")
        raise HTTPException(status_code=500, detail=f"청산 실패: {str(e)}")


# =====================================================
# 강제 청산
# =====================================================

async def liquidate_position(session: Session, position: FuturesPosition):
    """강제 청산"""
    try:
        account = session.get(FuturesAccount, position.account_id)
        liquidation_price = position.liquidation_price
        loss = position.margin
        liquidation_fee = (liquidation_price * position.quantity) * Decimal("0.001")
        
        position.status = FuturesPositionStatus.LIQUIDATED
        position.mark_price = liquidation_price
        position.realized_pnl = -loss
        position.closed_at = datetime.utcnow()
        
        account.margin_used -= position.margin
        account.total_profit -= loss
        account.unrealized_pnl -= position.unrealized_pnl
        account.updated_at = datetime.utcnow()
        
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
            f"⚠️ 강제 청산:\n"
            f"   - ID: {position.id}\n"
            f"   - {position.side.value} {position.symbol}\n"
            f"   - 청산가: ${liquidation_price:.2f}\n"
            f"   - 손실: -{loss:.2f} USDT"
        )
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 강제 청산 실패: {e}")


# =====================================================
# 청산 체크 (스케줄러용)
# =====================================================

async def check_liquidations(session: Session):
    """청산 체크"""
    try:
        open_positions = session.exec(
            select(FuturesPosition).where(
                FuturesPosition.status == FuturesPositionStatus.OPEN
            )
        ).all()
        
        for position in open_positions:
            try:
                current_price = await get_current_price(position.symbol)
                
                should_liquidate = False
                
                if position.side == FuturesPositionSide.LONG:
                    if current_price <= position.liquidation_price:
                        should_liquidate = True
                else:
                    if current_price >= position.liquidation_price:
                        should_liquidate = True
                
                if should_liquidate:
                    await liquidate_position(session, position)
                    
            except Exception as e:
                logger.error(f"포지션 {position.id} 청산 체크 실패: {e}")
                continue
                
    except Exception as e:
        logger.error(f"청산 체크 실패: {e}")


# =====================================================
# 미실현 손익 업데이트 (스케줄러용)
# =====================================================

async def update_positions_pnl(session: Session):
    """미실현 손익 업데이트"""
    try:
        open_positions = session.exec(
            select(FuturesPosition).where(
                FuturesPosition.status == FuturesPositionStatus.OPEN
            )
        ).all()
        
        for position in open_positions:
            try:
                current_price = await get_current_price(position.symbol)
                
                if position.side == FuturesPositionSide.LONG:
                    pnl = (current_price - position.entry_price) * position.quantity
                else:
                    pnl = (position.entry_price - current_price) * position.quantity
                
                position.mark_price = current_price
                position.unrealized_pnl = pnl
                session.add(position)
                
            except Exception as e:
                logger.error(f"포지션 {position.id} PnL 업데이트 실패: {e}")
                continue
        
        session.commit()
        
    except Exception as e:
        logger.error(f"PnL 업데이트 실패: {e}")
        session.rollback()