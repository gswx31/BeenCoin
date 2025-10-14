import httpx
from fastapi import HTTPException
import asyncio
from typing import Callable, List, Dict
from decimal import Decimal
from datetime import datetime

# Binance Public API - API 키 불필요
BINANCE_API_URL = "https://api.binance.com/api/v3"

async def get_current_price(symbol: str) -> Decimal:
    """Binance 실시간 가격 조회"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{BINANCE_API_URL}/ticker/price",
                params={"symbol": symbol}
            )
            if response.status_code == 200:
                data = response.json()
                return Decimal(data['price'])
            else:
                raise HTTPException(status_code=503, detail=f"Binance API error: {response.status_code}")
    except httpx.TimeoutException:
        raise HTTPException(status_code=503, detail="Binance API timeout")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch price: {str(e)}")

async def get_multiple_prices(symbols: List[str]) -> Dict[str, Decimal]:
    """여러 심볼의 현재 가격 한번에 조회"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 모든 심볼 가격 한번에 조회
            response = await client.get(f"{BINANCE_API_URL}/ticker/price")
            if response.status_code == 200:
                all_prices = response.json()
                prices = {}
                for item in all_prices:
                    if item['symbol'] in symbols:
                        prices[item['symbol']] = Decimal(item['price'])
                return prices
            else:
                # 실패시 개별 조회
                prices = {}
                for symbol in symbols:
                    try:
                        price = await get_current_price(symbol)
                        prices[symbol] = price
                    except:
                        prices[symbol] = Decimal('0')
                return prices
    except Exception as e:
        print(f"Error fetching multiple prices: {e}")
        # 에러시 빈 딕셔너리 반환
        return {symbol: Decimal('0') for symbol in symbols}

async def get_coin_info(symbol: str) -> Dict:
    """코인 24시간 통계 정보"""
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
                    "name": symbol.replace('USDT', ''),
                    "price": data['lastPrice'],
                    "change": data['priceChangePercent'],
                    "volume": data['volume'],
                    "high": data['highPrice'],
                    "low": data['lowPrice'],
                    "quoteVolume": data['quoteVolume']
                }
            else:
                return {}
    except Exception as e:
        print(f"Error fetching coin info for {symbol}: {e}")
        return {}

async def get_historical_data(symbol: str, interval: str = "1h", limit: int = 24) -> List[Dict]:
    """과거 가격 데이터 (캔들스틱)
    interval: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
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
        print(f"Error fetching historical data for {symbol}: {e}")
        return []

# 주문 관련 (모의 구현)
async def monitor_limit_order(order_id: int, symbol: str, side: str, price: Decimal, quantity: Decimal, callback: Callable):
    """지정가 주문 모니터링 (모의 구현)"""
    try:
        await asyncio.sleep(2)
        await callback(order_id, quantity, price)
    except Exception as e:
        print(f"Order monitoring error for {order_id}: {str(e)}")

async def execute_market_order(symbol: str, side: str, quantity: Decimal) -> Decimal:
    """시장가 주문 실행 (모의 구현)"""
    price = await get_current_price(symbol)
    return price