"""
선물 거래 서비스 — Long/Short + 레버리지 + 청산.

핵심 개념:
- Margin (증거금): 사용자가 거는 돈
- Position Size: margin * leverage
- Liquidation Price: 손실이 증거금을 다 까먹는 가격
  - Long: entry * (1 - 1/leverage)
  - Short: entry * (1 + 1/leverage)
- PnL: (현재가 - 진입가) * 수량 * 방향
- 수수료: 진입 + 청산 시 각각 0.04% (선물 taker)
"""
from decimal import Decimal
from datetime import datetime
from sqlmodel import Session, select
from fastapi import HTTPException
from app.models.database import FuturesPosition, TradingAccount, User
from app.services.binance_service import get_current_price
from app.services.price_engine import price_engine

MAX_LEVERAGE = 50
FUTURES_FEE_RATE = Decimal('0.0004')  # 0.04% (선물 taker)
MAINTENANCE_MARGIN_RATE = Decimal('0.005')  # 0.5% (유지 증거금률)


def calculate_liquidation_price(entry: Decimal, leverage: int, side: str) -> Decimal:
    """청산가 계산 (유지증거금 0.5% 고려)."""
    lev = Decimal(str(leverage))
    if side == 'LONG':
        return entry * (Decimal('1') - (Decimal('1') / lev) + MAINTENANCE_MARGIN_RATE)
    else:  # SHORT
        return entry * (Decimal('1') + (Decimal('1') / lev) - MAINTENANCE_MARGIN_RATE)


def calculate_pnl(side: str, entry: Decimal, current: Decimal, quantity: Decimal) -> Decimal:
    """미실현 손익."""
    if side == 'LONG':
        return (current - entry) * quantity
    else:  # SHORT
        return (entry - current) * quantity


async def open_position(session: Session, user_id: int, symbol: str, side: str,
                        margin: Decimal, leverage: int) -> FuturesPosition:
    """포지션 진입."""
    if side not in ('LONG', 'SHORT'):
        raise HTTPException(status_code=400, detail="방향은 LONG 또는 SHORT여야 해요")
    if leverage < 1 or leverage > MAX_LEVERAGE:
        raise HTTPException(status_code=400, detail=f"레버리지는 1~{MAX_LEVERAGE}배 사이여야 해요")
    if margin <= 0:
        raise HTTPException(status_code=400, detail="증거금은 0보다 커야 해요")

    # 잔고 확인
    account = session.exec(
        select(TradingAccount).where(TradingAccount.user_id == user_id)
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="계좌를 찾을 수 없어요")
    if account.balance < margin:
        raise HTTPException(status_code=400, detail="잔고가 부족해요")

    # 현재가 조회
    entry = price_engine.get_price(symbol)
    if entry is None:
        entry = await get_current_price(symbol)

    # 포지션 크기 = margin * leverage / entry_price
    position_size = (margin * Decimal(str(leverage))) / entry
    fee = margin * Decimal(str(leverage)) * FUTURES_FEE_RATE

    if account.balance < margin + fee:
        raise HTTPException(status_code=400, detail="수수료까지 포함하면 잔고가 부족해요")

    liq_price = calculate_liquidation_price(entry, leverage, side)

    position = FuturesPosition(
        user_id=user_id, symbol=symbol, side=side,
        entry_price=entry, quantity=position_size,
        leverage=leverage, margin=margin,
        liquidation_price=liq_price,
    )

    # 증거금 + 수수료 차감
    account.balance -= (margin + fee)

    session.add(position)
    session.add(account)
    session.commit()
    session.refresh(position)

    # 활동 피드
    try:
        from app.services.feed_service import add_activity
        coin = symbol.replace("USDT", "")
        emoji = "🚀" if side == "LONG" else "📉"
        msg = f"{emoji} {coin} {side} {leverage}배 진입 (증거금 ${float(margin):,.0f})"
        add_activity(session, user_id, "FUTURES_OPEN", msg, symbol,
                     {"side": side, "leverage": leverage, "margin": float(margin)})
    except Exception:
        pass

    return position


async def close_position(session: Session, user_id: int, position_id: int) -> dict:
    """포지션 청산 (수동)."""
    position = session.exec(
        select(FuturesPosition)
        .where(FuturesPosition.id == position_id, FuturesPosition.user_id == user_id)
    ).first()
    if not position:
        raise HTTPException(status_code=404, detail="포지션을 찾을 수 없어요")
    if not position.is_open:
        raise HTTPException(status_code=400, detail="이미 종료된 포지션이에요")

    current = price_engine.get_price(position.symbol)
    if current is None:
        current = await get_current_price(position.symbol)

    return _close_position_internal(session, position, current, liquidated=False)


def _close_position_internal(session: Session, position: FuturesPosition,
                              close_price: Decimal, liquidated: bool = False) -> dict:
    """포지션 종료 처리 (수동/강제 청산 공통)."""
    pnl = calculate_pnl(position.side, position.entry_price, close_price, position.quantity)
    # 종료 수수료
    notional = close_price * position.quantity
    fee = notional * FUTURES_FEE_RATE
    final_pnl = pnl - fee

    account = session.exec(
        select(TradingAccount).where(TradingAccount.user_id == position.user_id)
    ).first()

    # 청산: 증거금 0 / 청산 아님: 증거금 + PnL 반환
    if liquidated:
        # 증거금 전액 손실 (이미 차감되어 있음)
        returned = Decimal('0')
        final_pnl = -position.margin
    else:
        returned = position.margin + final_pnl
        if returned < 0:
            returned = Decimal('0')

    if account:
        account.balance += returned
        account.total_profit += final_pnl
        session.add(account)

    position.is_open = False
    position.closed_at = datetime.utcnow()
    position.close_price = close_price
    position.realized_pnl = final_pnl
    position.is_liquidated = liquidated
    session.add(position)
    session.commit()

    # 활동 피드
    try:
        from app.services.feed_service import add_activity
        coin = position.symbol.replace("USDT", "")
        if liquidated:
            msg = f"💥 {coin} {position.side} {position.leverage}배 강제 청산! (-${float(position.margin):,.0f})"
            atype = "LIQUIDATION"
        else:
            sign = "+" if final_pnl >= 0 else ""
            msg = f"{'💚' if final_pnl >= 0 else '💔'} {coin} {position.side} 종료 ({sign}${float(final_pnl):,.0f})"
            atype = "FUTURES_CLOSE"
        add_activity(session, position.user_id, atype, msg, position.symbol,
                     {"pnl": float(final_pnl), "liquidated": liquidated})
    except Exception:
        pass

    return {
        "success": True,
        "realized_pnl": float(final_pnl),
        "returned": float(returned),
        "liquidated": liquidated,
    }


def get_user_positions(session: Session, user_id: int, only_open: bool = True) -> list:
    q = select(FuturesPosition).where(FuturesPosition.user_id == user_id)
    if only_open:
        q = q.where(FuturesPosition.is_open == True)
    positions = session.exec(q.order_by(FuturesPosition.opened_at.desc())).all()

    result = []
    for p in positions:
        current = price_engine.get_price(p.symbol) or p.entry_price
        unrealized = calculate_pnl(p.side, p.entry_price, current, p.quantity) if p.is_open else Decimal('0')
        pnl_pct = (unrealized / p.margin * 100) if p.margin > 0 else Decimal('0')
        result.append({
            "id": p.id,
            "symbol": p.symbol,
            "side": p.side,
            "entry_price": float(p.entry_price),
            "current_price": float(current),
            "quantity": float(p.quantity),
            "leverage": p.leverage,
            "margin": float(p.margin),
            "liquidation_price": float(p.liquidation_price),
            "unrealized_pnl": float(unrealized),
            "pnl_pct": float(pnl_pct),
            "is_open": p.is_open,
            "is_liquidated": p.is_liquidated,
            "realized_pnl": float(p.realized_pnl),
            "opened_at": str(p.opened_at),
            "closed_at": str(p.closed_at) if p.closed_at else None,
        })
    return result


def check_liquidations(session: Session, symbol: str, current_price: Decimal):
    """PriceEngine에서 호출 — 청산 조건 충족된 포지션 강제 종료."""
    positions = session.exec(
        select(FuturesPosition).where(
            FuturesPosition.symbol == symbol,
            FuturesPosition.is_open == True,
        )
    ).all()

    for p in positions:
        should_liquidate = False
        if p.side == 'LONG' and current_price <= p.liquidation_price:
            should_liquidate = True
        elif p.side == 'SHORT' and current_price >= p.liquidation_price:
            should_liquidate = True

        if should_liquidate:
            try:
                _close_position_internal(session, p, current_price, liquidated=True)
                print(f"[Liquidation] #{p.id} {p.side} {p.symbol} @ {current_price}")
            except Exception as e:
                print(f"[Liquidation] Failed #{p.id}: {e}")
