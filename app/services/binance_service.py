# app/services/binance_service.py
"""
Binance API 서비스 - 실제 거래소 로직 구현
=============================================

주요 기능:
1. 실제 체결 내역 기반 시장가 주문
2. 지정가 주문의 실시간 부분 체결
3. 레버리지 반영 (100x → 거래량 100배)
4. 호가창 기반 체결
5. ✅ CI/CD 환경 Mock 지원 (451 에러 방지)
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import os
from typing import Dict, List, Optional, Tuple, Any
import random

from fastapi import HTTPException
import httpx

logger = logging.getLogger(__name__)


# =====================================================
# 추상화 인터페이스
# =====================================================

class IBinanceClient(ABC):
    """Binance API 클라이언트 인터페이스"""
    
    @abstractmethod
    async def get_current_price(self, symbol: str) -> Decimal:
        """현재가 조회"""
        pass
    
    @abstractmethod
    async def get_recent_trades(self, symbol: str, limit: int) -> List[Dict]:
        """최근 체결 내역 조회"""
        pass
    
    @abstractmethod
    async def get_24h_ticker(self, symbol: str) -> Optional[Dict]:
        """24시간 티커 정보 조회"""
        pass
    
    @abstractmethod
    async def get_multiple_prices(self, symbols: List[str]) -> Dict[str, Decimal]:
        """여러 코인 가격 일괄 조회"""
        pass
    
    @abstractmethod
    async def get_historical_data(self, symbol: str, interval: str, limit: int) -> List[Dict]:
        """과거 데이터 조회 (차트용)"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Binance API 연결 테스트"""
        pass
    
    @abstractmethod
    async def get_server_time(self) -> int:
        """Binance 서버 시간 조회"""
        pass
    
    @abstractmethod
    async def get_order_book(self, symbol: str, limit: int) -> Dict:
        """호가창 조회"""
        pass


# =====================================================
# Mock 데이터
# =====================================================

class MockBinanceData:
    """CI 환경용 Mock 데이터"""
    
    PRICES = {
        "BTCUSDT": "95000.00",
        "ETHUSDT": "3500.00",
        "BNBUSDT": "600.00",
        "ADAUSDT": "0.90",
        "XRPUSDT": "2.20",
        "SOLUSDT": "180.00",
        "DOGEUSDT": "0.35",
    }
    
    # 지원하는 심볼 목록
    SUPPORTED_SYMBOLS = set(PRICES.keys())
    
    @classmethod
    def validate_symbol(cls, symbol: str) -> None:
        """심볼 유효성 검사"""
        if symbol not in cls.SUPPORTED_SYMBOLS:
            raise HTTPException(status_code=400, detail=f"Invalid symbol: {symbol}")
    
    @classmethod
    def get_price(cls, symbol: str) -> str:
        """가격 조회"""
        cls.validate_symbol(symbol)
        return cls.PRICES[symbol]
    
    @classmethod
    def get_ticker_24hr(cls, symbol: str) -> Dict:
        """24시간 티커"""
        cls.validate_symbol(symbol)
        price = float(cls.get_price(symbol))
        return {
            "symbol": symbol,
            "lastPrice": str(price),
            "priceChange": str(price * 0.025),
            "priceChangePercent": "2.50",
            "weightedAvgPrice": str(price * 0.99),
            "prevClosePrice": str(price * 0.975),
            "lastQty": "0.5",
            "bidPrice": str(price * 0.999),
            "askPrice": str(price * 1.001),
            "openPrice": str(price * 0.975),
            "highPrice": str(price * 1.05),
            "lowPrice": str(price * 0.95),
            "volume": "10000",
            "quoteVolume": str(price * 10000),
            "openTime": int((datetime.utcnow() - timedelta(days=1)).timestamp() * 1000),
            "closeTime": int(datetime.utcnow().timestamp() * 1000),
            "firstId": 1000000,
            "lastId": 1001000,
            "count": 1000,
        }
    
    @classmethod
    def get_recent_trades(cls, symbol: str, limit: int = 100) -> List[Dict]:
        """Mock 체결 내역 생성"""
        cls.validate_symbol(symbol)
        base_price = float(cls.get_price(symbol))
        trades = []
        base_time = datetime.utcnow()
        
        for i in range(limit):
            # 가격 변동 ±0.5%
            price_variation = random.uniform(-0.005, 0.005)
            trade_price = base_price * (1 + price_variation)
            trade_qty = round(random.uniform(0.01, 2.0), 4)
            
            trades.append(
                {
                    "id": 1000000 + i,
                    "price": f"{trade_price:.2f}",
                    "qty": f"{trade_qty:.4f}",
                    "time": (base_time - timedelta(seconds=i * 2)).isoformat(),
                    "isBuyerMaker": random.choice([True, False]),
                }
            )
        
        return trades
    
    @classmethod
    def get_order_book(cls, symbol: str, limit: int = 20) -> Dict:
        """Mock 호가창 생성"""
        cls.validate_symbol(symbol)
        base_price = float(cls.get_price(symbol))
        
        bids = []
        asks = []
        
        for i in range(limit):
            # 매수 호가: 현재가보다 낮게
            bid_price = base_price * (1 - 0.0001 * (i + 1))
            bid_qty = round(random.uniform(0.1, 5.0), 4)
            bids.append([Decimal(f"{bid_price:.2f}"), Decimal(f"{bid_qty:.4f}")])
            
            # 매도 호가: 현재가보다 높게
            ask_price = base_price * (1 + 0.0001 * (i + 1))
            ask_qty = round(random.uniform(0.1, 5.0), 4)
            asks.append([Decimal(f"{ask_price:.2f}"), Decimal(f"{ask_qty:.4f}")])
        
        return {"bids": bids, "asks": asks}
    
    @classmethod
    def get_klines(cls, symbol: str, interval: str = "1h", limit: int = 100) -> List[Dict]:
        """Mock 캔들스틱 데이터 생성"""
        cls.validate_symbol(symbol)
        base_price = float(cls.get_price(symbol))
        klines = []
        
        # 인터벌에 따른 시간 간격 (분 단위)
        interval_minutes = {
            "1m": 1,
            "3m": 3,
            "5m": 5,
            "15m": 15,
            "30m": 30,
            "1h": 60,
            "2h": 120,
            "4h": 240,
            "6h": 360,
            "8h": 480,
            "12h": 720,
            "1d": 1440,
            "3d": 4320,
            "1w": 10080,
        }.get(interval, 60)
        
        current_time = datetime.utcnow()
        
        for i in range(limit):
            time_offset = timedelta(minutes=interval_minutes * (limit - i - 1))
            candle_time = current_time - time_offset
            
            # 랜덤 가격 변동
            open_price = base_price * (1 + random.uniform(-0.02, 0.02))
            close_price = open_price * (1 + random.uniform(-0.01, 0.01))
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.005))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.005))
            volume = random.uniform(100, 10000)
            
            klines.append(
                {
                    "time": int(candle_time.timestamp() * 1000),
                    "open": round(open_price, 2),
                    "high": round(high_price, 2),
                    "low": round(low_price, 2),
                    "close": round(close_price, 2),
                    "volume": round(volume, 2),
                }
            )
            
            # 다음 캔들의 기준 가격 업데이트
            base_price = close_price
        
        return klines
    
    @classmethod
    def get_multiple_prices(cls, symbols: List[str]) -> Dict[str, str]:
        """다중 가격 조회"""
        result = {}
        for symbol in symbols:
            if symbol in cls.SUPPORTED_SYMBOLS:
                result[symbol] = cls.PRICES[symbol]
        return result


# =====================================================
# 실제 Binance API 클라이언트
# =====================================================

class BinanceAPIClient(IBinanceClient):
    """실제 Binance API 클라이언트"""
    
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        self.timeout = httpx.Timeout(10.0)
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """비동기 클라이언트 가져오기"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """API 요청 공통 로직"""
        client = await self._get_client()
        
        try:
            response = await client.get(
                f"{self.base_url}/{endpoint}",
                params=params
            )
            
            if response.status_code == 451:
                logger.error("❌ 지역 제한: Binance API 접근 불가 (451)")
                raise HTTPException(status_code=503, detail="Binance API 접근 불가 지역")
            
            response.raise_for_status()
            return response.json()
            
        except httpx.TimeoutException:
            logger.error(f"❌ API 타임아웃: {endpoint}")
            raise HTTPException(status_code=503, detail="Binance API 타임아웃")
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ API 오류: {e.response.status_code}")
            raise HTTPException(status_code=503, detail=f"Binance API 오류: {e.response.status_code}")
        except Exception as e:
            logger.error(f"❌ API 예외: {e}")
            raise HTTPException(status_code=500, detail=f"API 요청 중 오류 발생: {str(e)}")
    
    async def get_current_price(self, symbol: str) -> Decimal:
        """현재가 조회"""
        data = await self._make_request("ticker/price", {"symbol": symbol})
        return Decimal(str(data["price"]))
    
    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """최근 체결 내역 조회"""
        try:
            data = await self._make_request("trades", {
                "symbol": symbol, 
                "limit": min(limit, 1000)
            })
            
            return [
                {
                    "id": trade["id"],
                    "price": str(trade["price"]),
                    "qty": str(trade["qty"]),
                    "time": datetime.fromtimestamp(trade["time"] / 1000).isoformat(),
                    "isBuyerMaker": trade["isBuyerMaker"],
                }
                for trade in data
            ]
        except HTTPException:
            return []
        except Exception as e:
            logger.error(f"❌ 체결 내역 조회 오류: {e}")
            return []
    
    async def get_24h_ticker(self, symbol: str) -> Optional[Dict]:
        """24시간 티커 정보 조회"""
        try:
            return await self._make_request("ticker/24hr", {"symbol": symbol})
        except HTTPException:
            return None
        except Exception as e:
            logger.error(f"❌ 24h 티커 조회 오류: {e}")
            return None
    
    async def get_multiple_prices(self, symbols: List[str]) -> Dict[str, Decimal]:
        """여러 코인 가격 일괄 조회"""
        try:
            data = await self._make_request("ticker/price")
            result = {}
            
            for item in data:
                if item["symbol"] in symbols:
                    result[item["symbol"]] = Decimal(str(item["price"]))
            
            logger.info(f"✅ 다중 가격 조회: {len(result)}개 심볼")
            return result
        except HTTPException:
            return {}
        except Exception as e:
            logger.error(f"❌ 다중 가격 조회 오류: {e}")
            return {}
    
    async def get_historical_data(self, symbol: str, interval: str = "1h", limit: int = 100) -> List[Dict]:
        """과거 데이터 조회 (차트용)"""
        try:
            data = await self._make_request("klines", {
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            })
            
            return [
                {
                    "time": k[0],
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                }
                for k in data
            ]
        except HTTPException:
            return []
        except Exception as e:
            logger.error(f"❌ 과거 데이터 조회 오류: {e}")
            return []
    
    async def test_connection(self) -> bool:
        """Binance API 연결 테스트"""
        try:
            await self._make_request("ping")
            logger.info("✅ Binance API 연결 정상")
            return True
        except HTTPException as e:
            logger.error(f"❌ Binance API 연결 실패: {e.detail}")
            return False
        except Exception as e:
            logger.error(f"❌ Binance API 연결 오류: {e}")
            return False
    
    async def get_server_time(self) -> int:
        """Binance 서버 시간 조회"""
        try:
            data = await self._make_request("time")
            return data["serverTime"]
        except HTTPException:
            logger.error("❌ 서버 시간 조회 실패, 로컬 시간 반환")
            return int(datetime.utcnow().timestamp() * 1000)
        except Exception as e:
            logger.error(f"❌ 서버 시간 조회 오류: {e}")
            return int(datetime.utcnow().timestamp() * 1000)
    
    async def get_order_book(self, symbol: str, limit: int = 20) -> Dict:
        """호가창 조회"""
        try:
            data = await self._make_request("depth", {
                "symbol": symbol,
                "limit": limit
            })
            
            return {
                "bids": [[Decimal(p), Decimal(q)] for p, q in data["bids"]],
                "asks": [[Decimal(p), Decimal(q)] for p, q in data["asks"]],
            }
        except HTTPException:
            return {"bids": [], "asks": []}
        except Exception as e:
            logger.error(f"❌ 호가창 조회 오류: {e}")
            return {"bids": [], "asks": []}
    
    async def close(self):
        """클라이언트 종료"""
        if self._client:
            await self._client.aclose()
            self._client = None


# =====================================================
# Mock Binance 클라이언트
# =====================================================

class MockBinanceClient(IBinanceClient):
    """Mock Binance 클라이언트 (CI/CD 환경용)"""
    
    async def get_current_price(self, symbol: str) -> Decimal:
        """현재가 조회"""
        MockBinanceData.validate_symbol(symbol)
        price = MockBinanceData.get_price(symbol)
        logger.info(f"🔧 [Mock] 현재가: {symbol} = ${price}")
        return Decimal(price)
    
    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Mock 체결 내역 생성"""
        MockBinanceData.validate_symbol(symbol)
        trades = MockBinanceData.get_recent_trades(symbol, limit)
        logger.info(f"🔧 [Mock] 체결 내역: {symbol} - {len(trades)}건")
        return trades
    
    async def get_24h_ticker(self, symbol: str) -> Optional[Dict]:
        """24시간 티커 정보 조회"""
        MockBinanceData.validate_symbol(symbol)
        ticker = MockBinanceData.get_ticker_24hr(symbol)
        logger.info(f"🔧 [Mock] 24h 티커: {symbol}")
        return ticker
    
    async def get_multiple_prices(self, symbols: List[str]) -> Dict[str, Decimal]:
        """여러 코인 가격 일괄 조회"""
        result = {}
        for symbol in symbols:
            try:
                MockBinanceData.validate_symbol(symbol)
                result[symbol] = Decimal(MockBinanceData.get_price(symbol))
            except HTTPException:
                continue
        
        logger.info(f"🔧 [Mock] 다중 가격 조회: {len(result)}개 심볼")
        return result
    
    async def get_historical_data(self, symbol: str, interval: str = "1h", limit: int = 100) -> List[Dict]:
        """과거 데이터 조회 (차트용)"""
        MockBinanceData.validate_symbol(symbol)
        klines = MockBinanceData.get_klines(symbol, interval, limit)
        logger.info(f"🔧 [Mock] 과거 데이터: {symbol} - {len(klines)}개")
        return klines
    
    async def test_connection(self) -> bool:
        """Binance API 연결 테스트"""
        logger.info("🔧 [Mock] Binance API 연결 테스트: 성공")
        return True
    
    async def get_server_time(self) -> int:
        """Binance 서버 시간 조회"""
        server_time = int(datetime.utcnow().timestamp() * 1000)
        logger.info(f"🔧 [Mock] 서버 시간: {server_time}")
        return server_time
    
    async def get_order_book(self, symbol: str, limit: int = 20) -> Dict:
        """호가창 조회"""
        MockBinanceData.validate_symbol(symbol)
        order_book = MockBinanceData.get_order_book(symbol, limit)
        logger.info(f"🔧 [Mock] 호가창: {symbol} - {limit}호가")
        return order_book


# =====================================================
# 주 로직 서비스 클래스
# =====================================================

class BinanceService:
    """Binance 거래 로직 서비스"""
    
    def __init__(self, client: Optional[IBinanceClient] = None):
        self.client = client or self._create_client()
    
    @staticmethod
    def _create_client() -> IBinanceClient:
        """환경에 맞는 클라이언트 생성"""
        if os.getenv("CI", "").lower() == "true" or os.getenv("MOCK_BINANCE", "").lower() == "true":
            return MockBinanceClient()
        return BinanceAPIClient()
    
    def _calculate_actual_quantity(self, quantity: Decimal, leverage: int) -> Decimal:
        """실제 거래 수량 계산"""
        return quantity * Decimal(str(leverage))
    
    async def execute_market_order(
        self, symbol: str, side: str, quantity: Decimal, leverage: int = 1
    ) -> Dict:
        """
        ⭐ 실제 체결 내역 기반 시장가 주문 (핵심 개선!)
        
        실제 거래소처럼 동작:
        1. 최근 체결 내역 조회
        2. 실제 거래된 가격/수량으로 순차 체결
        3. 레버리지 적용
        """
        try:
            actual_quantity = self._calculate_actual_quantity(quantity, leverage)
            
            logger.info(
                f"📊 시장가 주문: {side} {quantity} {symbol} "
                f"(레버리지 {leverage}x → 실제 {actual_quantity})"
            )
            
            # 1. 최근 체결 내역 조회
            recent_trades = await self.client.get_recent_trades(symbol, limit=500)
            
            if not recent_trades:
                logger.warning(f"⚠️ 체결 내역 없음, 현재가로 체결")
                return await self._fallback_to_current_price(symbol, side, quantity, leverage)
            
            # 2. 실제 체결 내역으로 순차 체결
            fills, total_cost, remaining = self._execute_against_trades(
                recent_trades, actual_quantity
            )
            
            # 3. 체결 내역 부족 시 현재가로 추가 체결
            if remaining > Decimal("0"):
                logger.warning(f"⚠️ 체결 내역 부족, 현재가로 추가 체결: {remaining}")
                await self._add_fallback_fills(symbol, remaining, fills, total_cost)
            
            # 4. 결과 계산 및 반환
            return self._create_order_result(
                symbol, side, quantity, actual_quantity, leverage, fills, total_cost
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ 시장가 주문 실행 오류: {e}")
            return await self._fallback_to_current_price(symbol, side, quantity, leverage)
    
    def _execute_against_trades(
        self, trades: List[Dict], total_quantity: Decimal
    ) -> Tuple[List[Dict], Decimal, Decimal]:
        """체결 내역 기반 거래 실행"""
        fills = []
        total_cost = Decimal("0")
        remaining = total_quantity
        
        for trade in trades:
            if remaining <= Decimal("0"):
                break
            
            trade_price = Decimal(str(trade["price"]))
            trade_qty = Decimal(str(trade["qty"]))
            fill_qty = min(trade_qty, remaining)
            
            fills.append({
                "price": trade_price,
                "quantity": fill_qty,
                "timestamp": trade["time"],
            })
            
            total_cost += trade_price * fill_qty
            remaining -= fill_qty
        
        return fills, total_cost, remaining
    
    async def _add_fallback_fills(
        self, symbol: str, remaining: Decimal, fills: List[Dict], total_cost: Decimal
    ) -> None:
        """현재가로 부족분 채우기"""
        current_price = await self.client.get_current_price(symbol)
        
        fills.append({
            "price": current_price,
            "quantity": remaining,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        total_cost += current_price * remaining
    
    def _create_order_result(
        self, symbol: str, side: str, quantity: Decimal, actual_quantity: Decimal,
        leverage: int, fills: List[Dict], total_cost: Decimal
    ) -> Dict:
        """주문 결과 생성"""
        average_price = total_cost / actual_quantity if actual_quantity > Decimal("0") else Decimal("0")
        
        logger.info(
            f"✅ 시장가 체결 완료: {side} {quantity} {symbol}\n"
            f"   - 실제 거래: {actual_quantity} (레버리지 {leverage}x)\n"
            f"   - 평균 체결가: ${average_price:.2f}\n"
            f"   - 총 비용: ${total_cost:.2f}\n"
            f"   - 분할 체결: {len(fills)}건"
        )
        
        return {
            "symbol": symbol,
            "side": side,
            "filled_quantity": quantity,
            "average_price": average_price,
            "total_cost": total_cost,
            "fills": fills,
            "leverage": leverage,
            "actual_position_size": actual_quantity,
        }
    
    async def _fallback_to_current_price(
        self, symbol: str, side: str, quantity: Decimal, leverage: int
    ) -> Dict:
        """현재가 폴백 로직"""
        current_price = await self.client.get_current_price(symbol)
        actual_quantity = self._calculate_actual_quantity(quantity, leverage)
        
        return {
            "symbol": symbol,
            "side": side,
            "filled_quantity": quantity,
            "average_price": current_price,
            "total_cost": current_price * actual_quantity,
            "fills": [{
                "price": current_price,
                "quantity": actual_quantity,
                "timestamp": datetime.utcnow().isoformat(),
            }],
            "leverage": leverage,
            "actual_position_size": actual_quantity,
        }
    
    async def check_limit_order_execution(
        self, symbol: str, order_side: str, limit_price: Decimal,
        remaining_quantity: Decimal, leverage: int = 1
    ) -> Optional[Dict]:
        """
        ⭐ 지정가 주문 실시간 체결 확인
        
        실제 거래소처럼 동작:
        1. 최근 체결 내역에서 지정가 매칭 확인
        2. 매칭되는 거래만큼 부분 체결
        3. 레버리지 적용
        """
        try:
            recent_trades = await self.client.get_recent_trades(symbol, limit=100)
            
            if not recent_trades:
                return None
            
            fills, filled_total, remaining = self._match_limit_order(
                recent_trades, order_side, limit_price, remaining_quantity
            )
            
            if filled_total > Decimal("0"):
                logger.info(
                    f"📈 지정가 부분 체결: {symbol} {order_side}\n"
                    f"   - 체결: {filled_total} / {remaining_quantity}\n"
                    f"   - 남은 수량: {remaining}\n"
                    f"   - 분할: {len(fills)}건"
                )
                
                return {
                    "symbol": symbol,
                    "side": order_side,
                    "filled_quantity": filled_total,
                    "fills": fills,
                    "remaining": remaining,
                    "leverage": leverage,
                    "limit_price": limit_price,
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 지정가 주문 체결 확인 오류: {e}")
            return None
    
    def _match_limit_order(
        self, trades: List[Dict], order_side: str, limit_price: Decimal,
        remaining_quantity: Decimal
    ) -> Tuple[List[Dict], Decimal, Decimal]:
        """지정가 주문 매칭 로직"""
        fills = []
        filled_total = Decimal("0")
        remaining = remaining_quantity
        
        for trade in trades:
            if remaining <= Decimal("0"):
                break
            
            trade_price = Decimal(str(trade["price"]))
            trade_qty = Decimal(str(trade["qty"]))
            
            # 주문 조건 확인
            if self._is_order_condition_met(order_side, trade_price, limit_price):
                fill_qty = min(trade_qty, remaining)
                
                fills.append({
                    "price": trade_price,
                    "quantity": fill_qty,
                    "timestamp": trade["time"]
                })
                
                filled_total += fill_qty
                remaining -= fill_qty
        
        return fills, filled_total, remaining
    
    @staticmethod
    def _is_order_condition_met(
        order_side: str, trade_price: Decimal, limit_price: Decimal
    ) -> bool:
        """주문 조건 만족 여부 확인"""
        if order_side == "BUY":
            return trade_price <= limit_price
        elif order_side == "SELL":
            return trade_price >= limit_price
        return False
    
    async def get_coin_info(self, symbol: str) -> Dict:
        """
        코인 정보 조회 (가격 + 24h 변동)
        market.py에서 사용
        """
        try:
            ticker = await self.client.get_24h_ticker(symbol)
            
            if ticker:
                return {
                    "symbol": symbol,
                    "price": ticker.get("lastPrice", "0"),
                    "change": ticker.get("priceChangePercent", "0"),
                    "volume": ticker.get("volume", "0"),
                    "high": ticker.get("highPrice", "0"),
                    "low": ticker.get("lowPrice", "0"),
                }
            else:
                # 티커 실패 시 최소한 현재가라도 조회
                price = await self.client.get_current_price(symbol)
                return {
                    "symbol": symbol,
                    "price": str(price),
                    "change": "0",
                    "volume": "0",
                    "high": "0",
                    "low": "0",
                }
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ 코인 정보 조회 실패: {symbol} - {e}")
            raise HTTPException(status_code=503, detail=f"{symbol} 정보 조회 실패")
    
    async def close(self):
        """리소스 정리"""
        if isinstance(self.client, BinanceAPIClient):
            await self.client.close()


# =====================================================
# 싱글톤 인스턴스 및 하위 호환성 함수
# =====================================================

# 전역 서비스 인스턴스
_binance_service: Optional[BinanceService] = None


def get_binance_service() -> BinanceService:
    """BinanceService 싱글톤 인스턴스 가져오기"""
    global _binance_service
    if _binance_service is None:
        _binance_service = BinanceService()
    return _binance_service


async def close_binance_service():
    """BinanceService 리소스 정리"""
    global _binance_service
    if _binance_service:
        await _binance_service.close()
        _binance_service = None


# =====================================================
# 하위 호환성을 위한 기존 함수들
# =====================================================

async def is_ci_environment() -> bool:
    """CI 환경 감지 (하위 호환성)"""
    return os.getenv("CI", "").lower() == "true" or os.getenv("MOCK_BINANCE", "").lower() == "true"


async def get_current_price(symbol: str) -> Decimal:
    """현재가 조회 (하위 호환성)"""
    service = get_binance_service()
    return await service.client.get_current_price(symbol)


async def get_recent_trades(symbol: str, limit: int = 100) -> List[Dict]:
    """최근 체결 내역 조회 (하위 호환성)"""
    service = get_binance_service()
    return await service.client.get_recent_trades(symbol, limit)


async def execute_market_order_with_real_trades(
    symbol: str, side: str, quantity: Decimal, leverage: int = 1
) -> Dict:
    """시장가 주문 실행 (하위 호환성)"""
    service = get_binance_service()
    return await service.execute_market_order(symbol, side, quantity, leverage)


async def check_limit_order_execution(
    symbol: str, order_side: str, limit_price: Decimal,
    remaining_quantity: Decimal, leverage: int = 1
) -> Optional[Dict]:
    """지정가 주문 체결 확인 (하위 호환성)"""
    service = get_binance_service()
    return await service.check_limit_order_execution(
        symbol, order_side, limit_price, remaining_quantity, leverage
    )


async def execute_market_order(symbol: str, side: str, quantity: Decimal) -> Decimal:
    """시장가 주문 실행 (하위 호환성 - 레버리지 없음)"""
    service = get_binance_service()
    result = await service.execute_market_order(symbol, side, quantity, 1)
    return result["average_price"]


async def get_multiple_prices(symbols: List[str]) -> Dict[str, Decimal]:
    """여러 코인 가격 일괄 조회 (하위 호환성)"""
    service = get_binance_service()
    return await service.client.get_multiple_prices(symbols)


async def get_24h_ticker(symbol: str) -> Optional[Dict]:
    """24시간 티커 정보 조회 (하위 호환성)"""
    service = get_binance_service()
    return await service.client.get_24h_ticker(symbol)


async def get_coin_info(symbol: str) -> Dict:
    """코인 정보 조회 (하위 호환성)"""
    service = get_binance_service()
    return await service.get_coin_info(symbol)


async def get_historical_data(symbol: str, interval: str = "1h", limit: int = 100) -> List[Dict]:
    """과거 데이터 조회 (하위 호환성)"""
    service = get_binance_service()
    return await service.client.get_historical_data(symbol, interval, limit)


async def test_connection() -> bool:
    """Binance API 연결 테스트 (하위 호환성)"""
    service = get_binance_service()
    return await service.client.test_connection()


async def get_server_time() -> int:
    """Binance 서버 시간 조회 (하위 호환성)"""
    service = get_binance_service()
    return await service.client.get_server_time()


async def get_order_book(symbol: str, limit: int = 20) -> Dict:
    """호가창 조회 (하위 호환성)"""
    service = get_binance_service()
    return await service.client.get_order_book(symbol, limit)