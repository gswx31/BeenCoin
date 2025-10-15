import httpx
from fastapi import HTTPException
import asyncio
from typing import Callable, List, Dict
from decimal import Decimal
from datetime import datetime

# Binance Public API
BINANCE_API_URL = "https://api.binance.com/api/v3"

def format_symbol(symbol: str) -> str:
    """심볼 형식 변환 (BTC -> BTCUSDT)"""
    if not symbol.endswith('USDT'):
        return f"{symbol}USDT"
    return symbol

async def get_current_price(symbol: str) -> Decimal:
    """Binance 실시간 가격 조회"""
    try:
        formatted_symbol = format_symbol(symbol)
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{BINANCE_API_URL}/ticker/price",
                params={"symbol": formatted_symbol}
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
                    symbol_without_usdt = item['symbol'].replace('USDT', '')
                    if symbol_without_usdt in symbols:
                        prices[symbol_without_usdt] = Decimal(item['price'])
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
        return {symbol: Decimal('0') for symbol in symbols}

async def get_coin_info(symbol: str) -> Dict:
    """코인 24시간 통계 정보"""
    try:
        formatted_symbol = format_symbol(symbol)
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{BINANCE_API_URL}/ticker/24hr",
                params={"symbol": formatted_symbol}
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "symbol": symbol,
                    "name": symbol,
                    "price": Decimal(data['lastPrice']),
                    "change": Decimal(data['priceChangePercent']),
                    "volume": Decimal(data['volume']),
                    "high": Decimal(data['highPrice']),
                    "low": Decimal(data['lowPrice']),
                    "quoteVolume": Decimal(data['quoteVolume'])
                }
            else:
                return {}
    except Exception as e:
        print(f"Error fetching coin info for {symbol}: {e}")
        return {}

async def get_historical_data(symbol: str, interval: str = "1h", limit: int = 24) -> List[Dict]:
    """과거 가격 데이터"""
    try:
        formatted_symbol = format_symbol(symbol)
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{BINANCE_API_URL}/klines",
                params={
                    "symbol": formatted_symbol,
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

async def execute_market_order(symbol: str, side: str, quantity: Decimal) -> Decimal:
    """시장가 주문 실행 (모의 구현)"""
    try:
        price = await get_current_price(symbol)
        # 실제 거래소에서는 여기서 주문을 실행하지만, 모의 거래에서는 현재가로 체결
        await asyncio.sleep(0.5)  # 거래 체결 시간 모의
        return price
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Market order execution failed: {str(e)}")

async def monitor_limit_order(order_id: int, symbol: str, side: str, limit_price: Decimal, quantity: Decimal, callback: Callable):
    """지정가 주문 모니터링 (모의 구현)"""
    try:
        # 실제 거래소에서는 웹소켓 등으로 가격 모니터링
        # 여기서는 간단히 2초 후 체결로 가정
        await asyncio.sleep(2)
        current_price = await get_current_price(symbol)
        
        # 지정가 조건 체크 (매수: 현재가 <= 지정가, 매도: 현재가 >= 지정가)
        if (side == 'BUY' and current_price <= limit_price) or (side == 'SELL' and current_price >= limit_price):
            await callback(order_id, quantity, limit_price)
        else:
            # 조건 미달시 10초 후 다시 체크 (실제로는 웹소켓으로 실시간 모니터링)
            await asyncio.sleep(10)
            current_price = await get_current_price(symbol)
            if (side == 'BUY' and current_price <= limit_price) or (side == 'SELL' and current_price >= limit_price):
                await callback(order_id, quantity, limit_price)
    except Exception as e:
        print(f"Limit order monitoring error for {order_id}: {str(e)}")