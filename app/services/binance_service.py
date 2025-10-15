# app/services/binance_service.py
import httpx
from fastapi import HTTPException
import asyncio
from typing import Callable, List, Dict, Optional
from decimal import Decimal
from datetime import datetime
import json

# Binance Public API - API 키 불필요
BINANCE_API_URL = "https://api.binance.com/api/v3"
BINANCE_FUTURES_API_URL = "https://fapi.binance.com/fapi/v1"
BINANCE_WS_URL = "wss://stream.binance.com:9443/ws"
BINANCE_FUTURES_WS_URL = "wss://fstream.binance.com/ws"

class BinanceService:
    """개선된 Binance 서비스 클래스"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
        self._price_cache = {}
        self._ws_connections = {}
    
    async def get_current_price(self, symbol: str, futures: bool = False) -> Decimal:
        """현물/선물 실시간 가격 조회"""
        try:
            base_url = BINANCE_FUTURES_API_URL if futures else BINANCE_API_URL
            
            response = await self.client.get(
                f"{base_url}/ticker/price",
                params={"symbol": symbol}
            )
            
            if response.status_code == 200:
                data = response.json()
                price = Decimal(data['price'])
                self._price_cache[symbol] = price
                return price
            else:
                # 캐시된 가격 반환
                if symbol in self._price_cache:
                    return self._price_cache[symbol]
                raise HTTPException(status_code=503, detail=f"Binance API error: {response.status_code}")
                
        except httpx.TimeoutException:
            if symbol in self._price_cache:
                return self._price_cache[symbol]
            raise HTTPException(status_code=503, detail="Binance API timeout")
        except Exception as e:
            if symbol in self._price_cache:
                return self._price_cache[symbol]
            raise HTTPException(status_code=503, detail=f"Failed to fetch price: {str(e)}")

    async def get_multiple_prices(self, symbols: List[str], futures: bool = False) -> Dict[str, Decimal]:
        """여러 심볼의 현재 가격 한번에 조회"""
        try:
            base_url = BINANCE_FUTURES_API_URL if futures else BINANCE_API_URL
            
            response = await self.client.get(f"{base_url}/ticker/price")
            if response.status_code == 200:
                all_prices = response.json()
                prices = {}
                for item in all_prices:
                    if item['symbol'] in symbols:
                        prices[item['symbol']] = Decimal(item['price'])
                        self._price_cache[item['symbol']] = Decimal(item['price'])
                return prices
            else:
                # 캐시에서 반환
                return {s: self._price_cache.get(s, Decimal('0')) for s in symbols}
                
        except Exception as e:
            print(f"Error fetching multiple prices: {e}")
            return {s: self._price_cache.get(s, Decimal('0')) for s in symbols}

    async def get_24hr_ticker(self, symbol: str, futures: bool = False) -> Dict:
        """24시간 가격 변동 정보"""
        try:
            base_url = BINANCE_FUTURES_API_URL if futures else BINANCE_API_URL
            
            response = await self.client.get(
                f"{base_url}/ticker/24hr",
                params={"symbol": symbol}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "symbol": data['symbol'],
                    "price": float(data['lastPrice']),
                    "change": float(data['priceChangePercent']),
                    "high": float(data['highPrice']),
                    "low": float(data['lowPrice']),
                    "volume": float(data['volume']),
                    "quoteVolume": float(data.get('quoteVolume', 0))
                }
            return {}
        except Exception as e:
            print(f"Error fetching 24hr ticker: {e}")
            return {}

    async def get_klines(self, 
                        symbol: str, 
                        interval: str = "1m", 
                        limit: int = 100,
                        futures: bool = False) -> List[Dict]:
        """캔들스틱 데이터 조회
        interval: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
        """
        try:
            base_url = BINANCE_FUTURES_API_URL if futures else BINANCE_API_URL
            
            response = await self.client.get(
                f"{base_url}/klines",
                params={
                    "symbol": symbol,
                    "interval": interval,
                    "limit": min(limit, 1000)
                }
            )
            
            if response.status_code == 200:
                klines = response.json()
                formatted_data = []
                
                for kline in klines:
                    formatted_data.append({
                        "time": kline[0],  # 타임스탬프 (밀리초)
                        "open": float(kline[1]),
                        "high": float(kline[2]),
                        "low": float(kline[3]),
                        "close": float(kline[4]),
                        "volume": float(kline[5]),
                        "closeTime": kline[6],
                        "quoteVolume": float(kline[7]),
                        "trades": int(kline[8])
                    })
                
                return formatted_data
            return []
        except Exception as e:
            print(f"Error fetching klines: {e}")
            return []

    async def get_orderbook(self, symbol: str, limit: int = 20, futures: bool = False) -> Dict:
        """호가창 데이터 조회"""
        try:
            base_url = BINANCE_FUTURES_API_URL if futures else BINANCE_API_URL
            
            response = await self.client.get(
                f"{base_url}/depth",
                params={
                    "symbol": symbol,
                    "limit": limit
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "bids": [[float(p), float(q)] for p, q in data['bids']],
                    "asks": [[float(p), float(q)] for p, q in data['asks']],
                    "lastUpdateId": data['lastUpdateId']
                }
            return {"bids": [], "asks": []}
        except Exception as e:
            print(f"Error fetching orderbook: {e}")
            return {"bids": [], "asks": []}

    async def get_recent_trades(self, symbol: str, limit: int = 50, futures: bool = False) -> List[Dict]:
        """최근 체결 내역"""
        try:
            base_url = BINANCE_FUTURES_API_URL if futures else BINANCE_API_URL
            
            response = await self.client.get(
                f"{base_url}/trades",
                params={
                    "symbol": symbol,
                    "limit": min(limit, 1000)
                }
            )
            
            if response.status_code == 200:
                trades = response.json()
                return [
                    {
                        "id": t['id'],
                        "price": float(t['price']),
                        "qty": float(t['qty']),
                        "time": t['time'],
                        "isBuyerMaker": t['isBuyerMaker']
                    }
                    for t in trades
                ]
            return []
        except Exception as e:
            print(f"Error fetching recent trades: {e}")
            return []

    async def get_funding_rate(self, symbol: str) -> Dict:
        """선물 펀딩 요율 (선물 전용)"""
        try:
            response = await self.client.get(
                f"{BINANCE_FUTURES_API_URL}/fundingRate",
                params={"symbol": symbol, "limit": 1}
            )
            
            if response.status_code == 200 and response.json():
                data = response.json()[0]
                return {
                    "symbol": data['symbol'],
                    "fundingRate": float(data['fundingRate']),
                    "fundingTime": data['fundingTime']
                }
            return {}
        except Exception as e:
            print(f"Error fetching funding rate: {e}")
            return {}

    async def calculate_liquidation_price(self, 
                                         entry_price: Decimal,
                                         quantity: Decimal,
                                         leverage: int,
                                         side: str,
                                         margin_type: str = "ISOLATED") -> Decimal:
        """청산 가격 계산 (단순화된 버전)"""
        
        # 유지 마진율 (보통 0.5%)
        maintenance_margin_rate = Decimal('0.005')
        
        if margin_type == "ISOLATED":
            # 격리 마진 모드
            margin = (entry_price * quantity) / Decimal(leverage)
            
            if side == "LONG":
                # 롱 포지션 청산가 = 진입가 * (1 - 1/레버리지 + 유지마진율)
                liquidation_price = entry_price * (Decimal('1') - Decimal('1')/Decimal(leverage) + maintenance_margin_rate)
            else:  # SHORT
                # 숏 포지션 청산가 = 진입가 * (1 + 1/레버리지 - 유지마진율)
                liquidation_price = entry_price * (Decimal('1') + Decimal('1')/Decimal(leverage) - maintenance_margin_rate)
        else:
            # 교차 마진 모드 (전체 잔고 사용)
            # 더 복잡한 계산 필요 - 여기서는 단순화
            liquidation_price = Decimal('0')
        
        return max(liquidation_price, Decimal('0'))

    async def close(self):
        """클라이언트 종료"""
        await self.client.aclose()

# 전역 인스턴스
binance_service = BinanceService()

# 기존 함수들과의 호환성을 위한 래퍼
async def get_current_price(symbol: str) -> Decimal:
    return await binance_service.get_current_price(symbol)

async def get_multiple_prices(symbols: List[str]) -> Dict[str, Decimal]:
    return await binance_service.get_multiple_prices(symbols)

async def get_historical_data(symbol: str, interval: str = "1h", limit: int = 24) -> List[Dict]:
    klines = await binance_service.get_klines(symbol, interval, limit)
    # 기존 형식으로 변환
    return [
        {
            "timestamp": datetime.fromtimestamp(k['time'] / 1000).isoformat(),
            "open": k['open'],
            "high": k['high'],
            "low": k['low'],
            "close": k['close'],
            "volume": k['volume']
        }
        for k in klines
    ]

async def get_coin_info(symbol: str) -> Dict:
    ticker = await binance_service.get_24hr_ticker(symbol)
    if ticker:
        return {
            "symbol": ticker['symbol'],
            "name": symbol.replace('USDT', ''),
            "price": str(ticker['price']),
            "change": str(ticker['change']),
            "volume": str(ticker['volume']),
            "high": str(ticker['high']),
            "low": str(ticker['low']),
            "quoteVolume": str(ticker.get('quoteVolume', 0))
        }
    return {}

# 모의 주문 실행 (기존 호환성 유지)
async def monitor_limit_order(order_id: int, symbol: str, side: str, price: Decimal, quantity: Decimal, callback: Callable):
    """지정가 주문 모니터링 (모의)"""
    # 실제로는 WebSocket으로 가격을 모니터링해야 하지만, 
    # 여기서는 단순화하여 2초 후 체결되는 것으로 가정
    await asyncio.sleep(2)
    await callback(order_id, quantity, price)

async def execute_market_order(symbol: str, side: str, quantity: Decimal) -> Decimal:
    """시장가 주문 실행 (모의)"""
    price = await get_current_price(symbol)
    return price