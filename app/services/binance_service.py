# app/services/binance_service.py
import httpx
import asyncio
from decimal import Decimal
from typing import Dict, List
from fastapi import HTTPException, status
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

BINANCE_API_URL = "https://api.binance.com/api/v3"
MAX_RETRIES = 3
RETRY_DELAY = 1

async def get_current_price(symbol: str, retry_count: int = 0) -> Decimal:
    """바이낸스 실시간 가격 조회 (재시도 로직)"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{BINANCE_API_URL}/ticker/price",
                params={"symbol": symbol}
            )
            
            if response.status_code == 200:
                data = response.json()
                price = Decimal(data['price'])
                return price
            else:
                raise HTTPException(
                    status_code=503,
                    detail=f"Binance API 오류: {response.status_code}"
                )
                
    except httpx.TimeoutException:
        if retry_count < MAX_RETRIES:
            logger.warning(f"⏱️ Timeout, 재시도 ({retry_count + 1}/{MAX_RETRIES})...")
            await asyncio.sleep(RETRY_DELAY * (retry_count + 1))
            return await get_current_price(symbol, retry_count + 1)
        else:
            logger.error(f"❌ Timeout after {MAX_RETRIES} retries")
            raise HTTPException(status_code=503, detail="Binance API 타임아웃")
            
    except Exception as e:
        if retry_count < MAX_RETRIES:
            logger.warning(f"⚠️ Error, 재시도 ({retry_count + 1}/{MAX_RETRIES}): {e}")
            await asyncio.sleep(RETRY_DELAY * (retry_count + 1))
            return await get_current_price(symbol, retry_count + 1)
        else:
            logger.error(f"❌ Failed after {MAX_RETRIES} retries: {e}")
            raise HTTPException(status_code=503, detail=f"Binance API 오류: {str(e)}")


async def get_multiple_prices(symbols: List[str]) -> Dict[str, Decimal]:
    """여러 코인 가격 조회"""
    prices = {}
    
    for symbol in symbols:
        try:
            prices[symbol] = await get_current_price(symbol)
        except:
            logger.warning(f"⚠️ 가격 조회 실패: {symbol}")
            prices[symbol] = Decimal('0')
    
    return prices


async def execute_market_order(symbol: str, side: str, quantity: Decimal) -> Decimal:
    """시장가 주문 실행 (현재가 반환)"""
    price = await get_current_price(symbol)
    logger.info(f"✅ 시장가: {side} {quantity} {symbol} @ ${price}")
    return price


async def get_coin_info(symbol: str) -> dict:
    """코인 상세 정보"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{BINANCE_API_URL}/ticker/24hr",
                params={"symbol": symbol}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "symbol": data['symbol'],
                    "price": data['lastPrice'],
                    "change": data['priceChangePercent'],
                    "volume": data['volume'],
                    "high": data['highPrice'],
                    "low": data['lowPrice'],
                    "quoteVolume": data['quoteVolume']
                }
            return {}
    except Exception as e:
        logger.error(f"❌ 코인 정보 조회 실패: {e}")
        return {}


async def get_historical_data(symbol: str, interval: str, limit: int) -> List[dict]:
    """과거 가격 데이터"""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{BINANCE_API_URL}/klines",
                params={
                    "symbol": symbol,
                    "interval": interval,
                    "limit": limit
                }
            )
            
            if response.status_code == 200:
                klines = response.json()
                historical_data = []
                for kline in klines:
                    historical_data.append({
                        "timestamp": datetime.fromtimestamp(kline[0] / 1000).isoformat(),
                        "open": float(kline[1]),
                        "high": float(kline[2]),
                        "low": float(kline[3]),
                        "close": float(kline[4]),
                        "volume": float(kline[5])
                    })
                return historical_data
            else:
                return []
    except Exception as e:
        logger.error(f"❌ 과거 데이터 조회 실패: {e}")
        return []


async def get_recent_trades(symbol: str, limit: int = 100) -> List[Dict]:
    """바이낸스 실제 체결 내역 조회"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{BINANCE_API_URL}/trades",
                params={"symbol": symbol, "limit": limit}
            )
            
            if response.status_code == 200:
                trades = response.json()
                return [
                    {
                        "id": trade["id"],
                        "price": float(trade["price"]),
                        "quantity": float(trade["qty"]),
                        "time": trade["time"],
                        "isBuyerMaker": trade["isBuyerMaker"]
                    }
                    for trade in trades
                ]
            else:
                logger.error(f"❌ Binance trades API: {response.status_code}")
                return []
                
    except httpx.TimeoutException:
        logger.error(f"❌ Binance trades timeout: {symbol}")
        return []
    except Exception as e:
        logger.error(f"❌ 체결 내역 조회 실패: {e}")
        return []