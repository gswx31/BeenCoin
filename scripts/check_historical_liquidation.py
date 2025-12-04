# scripts/check_historical_liquidation.py
# =============================================================================
# 과거 가격 데이터를 기반으로 청산 여부 확인 (수정판)
# =============================================================================
"""
사용법:
    python -m scripts.check_historical_liquidation
"""
import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal

import httpx
from sqlmodel import Session, select

import sys
sys.path.insert(0, '.')

# ⭐ 핵심: 모든 모델을 먼저 import해서 관계 설정
from app.models.database import User  # User 먼저!
from app.models.futures import (
    FuturesAccount,
    FuturesPosition,
    FuturesPositionSide,
    FuturesPositionStatus,
    FuturesTransaction,
)
from app.core.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BINANCE_API = "https://api.binance.com/api/v3"


async def get_historical_klines(symbol: str, start_time: datetime, end_time: datetime = None):
    """바이낸스에서 과거 캔들 데이터 조회"""
    if end_time is None:
        end_time = datetime.now(timezone.utc)
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    all_klines = []
    
    async with httpx.AsyncClient(timeout=30) as client:
        while start_ms < end_ms:
            try:
                response = await client.get(
                    f"{BINANCE_API}/klines",
                    params={
                        "symbol": symbol,
                        "interval": "1m",
                        "startTime": start_ms,
                        "endTime": end_ms,
                        "limit": 1000,
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"API 오류: {response.status_code}")
                    break
                
                klines = response.json()
                
                if not klines:
                    break
                
                all_klines.extend(klines)
                start_ms = klines[-1][0] + 60000
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"캔들 조회 실패: {e}")
                break
    
    return all_klines


async def check_liquidation_in_history(position: FuturesPosition) -> dict:
    """포지션 개설 후 청산가에 도달한 적이 있는지 확인"""
    logger.info(f"📊 {position.symbol} 히스토리 데이터 조회 중...")
    logger.info(f"   개설 시간: {position.opened_at}")
    
    klines = await get_historical_klines(
        symbol=position.symbol,
        start_time=position.opened_at,
    )
    
    if not klines:
        return {
            "should_liquidate": False,
            "liquidation_time": None,
            "liquidation_candle": None,
            "lowest_price": None,
            "highest_price": None,
        }
    
    logger.info(f"   캔들 수: {len(klines)}개")
    
    lowest_price = float('inf')
    highest_price = 0
    liquidation_time = None
    liquidation_candle = None
    
    for kline in klines:
        open_time = datetime.fromtimestamp(kline[0] / 1000)
        high = float(kline[2])
        low = float(kline[3])
        
        lowest_price = min(lowest_price, low)
        highest_price = max(highest_price, high)
        
        if liquidation_time is None:
            if position.side == FuturesPositionSide.LONG:
                if low <= float(position.liquidation_price):
                    liquidation_time = open_time
                    liquidation_candle = {
                        "time": open_time,
                        "open": float(kline[1]),
                        "high": high,
                        "low": low,
                        "close": float(kline[4]),
                    }
            else:
                if high >= float(position.liquidation_price):
                    liquidation_time = open_time
                    liquidation_candle = {
                        "time": open_time,
                        "open": float(kline[1]),
                        "high": high,
                        "low": low,
                        "close": float(kline[4]),
                    }
    
    return {
        "should_liquidate": liquidation_time is not None,
        "liquidation_time": liquidation_time,
        "liquidation_candle": liquidation_candle,
        "lowest_price": lowest_price,
        "highest_price": highest_price,
    }


async def execute_historical_liquidation(
    session: Session, 
    position: FuturesPosition, 
    liquidation_time: datetime,
):
    """과거 시점 청산 실행 - 간소화 버전"""
    try:
        # 직접 SQL로 처리 (외래키 문제 우회)
        from sqlalchemy import text
        
        liquidation_price = float(position.liquidation_price)
        loss = float(position.margin)
        liquidation_fee = liquidation_price * float(position.quantity) * 0.001
        
        # 1. 포지션 업데이트
        session.exec(
            text("""
                UPDATE futures_positions 
                SET status = 'LIQUIDATED',
                    mark_price = :liq_price,
                    realized_pnl = :loss,
                    closed_at = :closed_at
                WHERE id = :position_id
            """),
            params={
                "liq_price": liquidation_price,
                "loss": -loss,
                "closed_at": liquidation_time,
                "position_id": str(position.id),
            }
        )
        
        # 2. 계정 업데이트
        session.exec(
            text("""
                UPDATE futures_accounts 
                SET margin_used = margin_used - :margin,
                    total_profit = total_profit - :loss,
                    updated_at = :now
                WHERE id = :account_id
            """),
            params={
                "margin": float(position.margin),
                "loss": loss,
                "now": datetime.now(timezone.utc),
                "account_id": str(position.account_id),
            }
        )
        
        # 3. 거래 내역 추가
        import uuid
        tx_id = str(uuid.uuid4())
        
        # account에서 user_id 조회
        result = session.exec(
            text("SELECT user_id FROM futures_accounts WHERE id = :account_id"),
            params={"account_id": str(position.account_id)}
        )
        row = result.fetchone()
        user_id = str(row[0]) if row else None
        
        if user_id:
            session.exec(
                text("""
                    INSERT INTO futures_transactions 
                    (id, user_id, position_id, symbol, side, action, quantity, price, leverage, pnl, fee, timestamp)
                    VALUES (:id, :user_id, :position_id, :symbol, :side, 'LIQUIDATION', :quantity, :price, :leverage, :pnl, :fee, :timestamp)
                """),
                params={
                    "id": tx_id,
                    "user_id": user_id,
                    "position_id": str(position.id),
                    "symbol": position.symbol,
                    "side": position.side.value,
                    "quantity": float(position.quantity),
                    "price": liquidation_price,
                    "leverage": position.leverage,
                    "pnl": -loss,
                    "fee": liquidation_fee,
                    "timestamp": liquidation_time,
                }
            )
        
        session.commit()
        
        print(f"\n   ✅ 청산 처리 완료!")
        print(f"      청산가: ${liquidation_price:.2f}")
        print(f"      손실: -${loss:.2f} (증거금 전액)")
        print(f"      청산 시간: {liquidation_time}")
        
    except Exception as e:
        session.rollback()
        logger.error(f"청산 처리 실패: {e}")
        import traceback
        traceback.print_exc()


async def process_historical_liquidations():
    """모든 OPEN 포지션에 대해 과거 데이터 기반 청산 확인"""
    print("\n" + "=" * 70)
    print("🔍 과거 데이터 기반 청산 확인")
    print("=" * 70)
    
    with Session(engine) as session:
        open_positions = session.exec(
            select(FuturesPosition).where(
                FuturesPosition.status == FuturesPositionStatus.OPEN
            )
        ).all()
        
        if not open_positions:
            print("✅ 열린 포지션 없음")
            return
        
        print(f"📊 검사할 포지션: {len(open_positions)}개\n")
        
        for position in open_positions:
            print("-" * 70)
            print(f"📍 포지션 ID: {position.id}")
            print(f"   심볼: {position.symbol}")
            print(f"   방향: {position.side.value}")
            print(f"   진입가: ${position.entry_price:.2f}")
            print(f"   청산가: ${position.liquidation_price:.2f}")
            print(f"   레버리지: {position.leverage}x")
            print(f"   증거금: ${position.margin:.2f}")
            print(f"   개설일: {position.opened_at}")
            
            result = await check_liquidation_in_history(position)
            
            print(f"\n   📈 가격 범위:")
            print(f"      최저가: ${result['lowest_price']:.2f}")
            print(f"      최고가: ${result['highest_price']:.2f}")
            
            if result["should_liquidate"]:
                print(f"\n   🔴 청산 발생!")
                print(f"      청산 시간: {result['liquidation_time']}")
                if result["liquidation_candle"]:
                    candle = result["liquidation_candle"]
                    print(f"      캔들: O:{candle['open']:.2f} H:{candle['high']:.2f} L:{candle['low']:.2f} C:{candle['close']:.2f}")
                
                confirm = input("\n   ⚠️ 이 포지션을 청산 처리하시겠습니까? (y/n): ")
                
                if confirm.lower() == 'y':
                    await execute_historical_liquidation(
                        session, 
                        position, 
                        result['liquidation_time'],
                    )
                else:
                    print("   ⏭️ 건너뜀")
            else:
                if position.side == FuturesPositionSide.LONG:
                    current_price = result['highest_price']  # 최근 고가 기준
                    pnl = (Decimal(str(current_price)) - position.entry_price) * position.quantity
                else:
                    current_price = result['lowest_price']
                    pnl = (position.entry_price - Decimal(str(current_price))) * position.quantity
                
                pnl_percent = (pnl / position.margin) * 100
                print(f"\n   🟢 청산 미발생")
                print(f"      현재 추정 손익: ${float(pnl):.2f} ({float(pnl_percent):+.2f}%)")
            
            print()
        
        print("=" * 70)
        print("✅ 검사 완료")
        print("=" * 70)


if __name__ == "__main__":
    print("\n🔧 BeenCoin 과거 데이터 기반 청산 확인")
    asyncio.run(process_historical_liquidations())