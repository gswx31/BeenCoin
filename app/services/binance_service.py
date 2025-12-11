# app/services/binance_service.py
"""
Binance API 서비스 - 개선 버전
=============================================

주요 개선사항:
1. ✅ 유효하지 않은 심볼에 대한 일관된 처리
2. ✅ None 반환 시 안전한 에러 처리
3. ✅ 모든 함수에서 단일성 있는 에러 핸들링
4. ✅ CI/CD 환경 Mock 지원
"""

from datetime import datetime, timedelta
from decimal import Decimal
import logging
import os
import random

from fastapi import HTTPException
import httpx

logger = logging.getLogger(__name__)

# Binance API 설정
BINANCE_API_BASE = "https://api.binance.com/api/v3"
TIMEOUT = httpx.Timeout(10.0)


# =====================================================
# CI 환경 감지
# =====================================================


def is_ci_environment() -> bool:
    """CI 환경 감지"""
    return os.getenv("CI", "").lower() == "true" or os.getenv("MOCK_BINANCE", "").lower() == "true"


# =====================================================
# 📌 개선: 유효한 심볼 검증 함수 추가
# =====================================================


def validate_symbol(symbol: str) -> None:
    """
    심볼 유효성 검증
    
    Args:
        symbol: 거래 심볼
        
    Raises:
        HTTPException: 유효하지 않은 심볼일 경우
    """
    if is_ci_environment():
        if not MockBinanceData.is_valid_symbol(symbol):
            logger.error(f"❌ 유효하지 않은 심볼: {symbol}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid symbol: {symbol}. Supported symbols: {', '.join(MockBinanceData.SUPPORTED_SYMBOLS)}"
            )


# =====================================================
# Mock 데이터 클래스
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

    SUPPORTED_SYMBOLS = set(PRICES.keys())

    @classmethod
    def is_valid_symbol(cls, symbol: str) -> bool:
        """유효한 심볼인지 확인"""
        return symbol in cls.SUPPORTED_SYMBOLS

    @classmethod
    def get_price(cls, symbol: str) -> str | None:
        """
        가격 조회
        
        Returns:
            str | None: 가격 문자열 또는 None (유효하지 않은 심볼)
        """
        return cls.PRICES.get(symbol)

    @classmethod
    def get_ticker_24hr(cls, symbol: str) -> dict | None:
        """
        24시간 티커
        
        Returns:
            dict | None: 티커 데이터 또는 None (유효하지 않은 심볼)
        """
        price_str = cls.get_price(symbol)
        if price_str is None:
            return None
            
        price = float(price_str)
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
    def get_recent_trades(cls, symbol: str, limit: int = 100) -> list[dict]:
        """
        📌 개선: Mock 체결 내역 생성
        
        Returns:
            list[dict]: 체결 내역 (유효하지 않은 심볼은 빈 리스트)
        """
        price_str = cls.get_price(symbol)
        if price_str is None:
            logger.warning(f"⚠️ Mock 체결 내역: 유효하지 않은 심볼 {symbol}")
            return []
            
        base_price = float(price_str)
        trades = []
        base_time = datetime.utcnow()

        for i in range(limit):
            price_variation = random.uniform(-0.005, 0.005)
            trade_price = base_price * (1 + price_variation)
            trade_qty = round(random.uniform(0.01, 2.0), 4)

            trades.append({
                "id": 1000000 + i,
                "price": f"{trade_price:.2f}",
                "qty": f"{trade_qty:.4f}",
                "time": (base_time - timedelta(seconds=i * 2)).isoformat(),
                "isBuyerMaker": random.choice([True, False]),
            })

        return trades

    @classmethod
    def get_order_book(cls, symbol: str, limit: int = 20) -> dict:
        """
        📌 개선: Mock 호가창 생성
        
        Returns:
            dict: 호가창 (유효하지 않은 심볼은 빈 호가창)
        """
        price_str = cls.get_price(symbol)
        if price_str is None:
            logger.warning(f"⚠️ Mock 호가창: 유효하지 않은 심볼 {symbol}")
            return {"bids": [], "asks": []}
            
        base_price = float(price_str)

        bids = []
        asks = []

        for i in range(limit):
            bid_price = base_price * (1 - 0.0001 * (i + 1))
            bid_qty = round(random.uniform(0.1, 5.0), 4)
            bids.append([Decimal(f"{bid_price:.2f}"), Decimal(f"{bid_qty:.4f}")])

            ask_price = base_price * (1 + 0.0001 * (i + 1))
            ask_qty = round(random.uniform(0.1, 5.0), 4)
            asks.append([Decimal(f"{ask_price:.2f}"), Decimal(f"{ask_qty:.4f}")])

        return {"bids": bids, "asks": asks}

    @classmethod
    def get_klines(cls, symbol: str, interval: str = "1h", limit: int = 100) -> list[dict]:
        """
        📌 개선: Mock 캔들스틱 데이터 생성
        
        Returns:
            list[dict]: 캔들 데이터 (유효하지 않은 심볼은 빈 리스트)
        """
        price_str = cls.get_price(symbol)
        if price_str is None:
            logger.warning(f"⚠️ Mock 캔들 데이터: 유효하지 않은 심볼 {symbol}")
            return []
            
        base_price = float(price_str)
        klines = []

        interval_minutes = {
            "1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30,
            "1h": 60, "2h": 120, "4h": 240, "6h": 360,
            "12h": 720, "1d": 1440,
        }.get(interval, 60)

        base_time = datetime.utcnow()

        for i in range(limit):
            open_price = base_price * (1 + random.uniform(-0.02, 0.02))
            close_price = open_price * (1 + random.uniform(-0.01, 0.01))
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.01))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.01))
            volume = round(random.uniform(100, 1000), 2)

            kline_time = base_time - timedelta(minutes=interval_minutes * (limit - i))

            klines.append({
                "time": int(kline_time.timestamp() * 1000),
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
            })

        return klines


# =====================================================
# 📌 개선: 현재가 조회 (단일성 강화)
# =====================================================


async def get_current_price(symbol: str) -> Decimal:
    """
    현재가 조회 (개선 버전)
    
    Args:
        symbol: 거래 심볼
        
    Returns:
        Decimal: 현재가
        
    Raises:
        HTTPException: 유효하지 않은 심볼 또는 API 오류
    """
    if is_ci_environment():
        # 📌 개선: 유효성 검증 먼저
        validate_symbol(symbol)
        
        price = MockBinanceData.get_price(symbol)
        logger.info(f"🔧 [CI Mock] 현재가: {symbol} = ${price}")
        return Decimal(price)

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"{BINANCE_API_BASE}/ticker/price",
                params={"symbol": symbol}
            )

            if response.status_code == 200:
                data = response.json()
                price = Decimal(str(data["price"]))
                logger.debug(f"✅ 현재가 조회: {symbol} = ${price:.2f}")
                return price
            elif response.status_code == 400:
                # 유효하지 않은 심볼
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid symbol: {symbol}"
                )
            elif response.status_code == 451:
                logger.error("❌ 지역 제한: Binance API 접근 불가 (451)")
                raise HTTPException(status_code=503, detail="Binance API 접근 불가 지역")
            else:
                logger.error(f"❌ 현재가 조회 실패: Status {response.status_code}")
                raise HTTPException(status_code=503, detail="가격 조회 실패")

    except httpx.TimeoutException:
        logger.error(f"❌ 현재가 조회 타임아웃: {symbol}")
        raise HTTPException(status_code=503, detail="Binance API 타임아웃")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 현재가 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# 📌 개선: 체결 내역 조회 (단일성 강화)
# =====================================================


async def get_recent_trades(symbol: str, limit: int = 100) -> list[dict]:
    """
    최근 체결 내역 조회 (개선 버전)
    
    Args:
        symbol: 거래 심볼
        limit: 조회할 거래 개수
        
    Returns:
        list[dict]: 체결 내역 (빈 리스트 가능)
        
    Note:
        - 유효하지 않은 심볼: 빈 리스트 반환 (에러 발생 안 함)
        - API 실패: 빈 리스트 반환
    """
    if is_ci_environment():
        # 📌 개선: 유효하지 않은 심볼도 안전하게 처리
        trades = MockBinanceData.get_recent_trades(symbol, limit)
        logger.info(f"🔧 [CI Mock] 체결 내역: {symbol} - {len(trades)}건")
        return trades

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"{BINANCE_API_BASE}/trades",
                params={"symbol": symbol, "limit": min(limit, 1000)}
            )

            if response.status_code == 200:
                trades = response.json()
                formatted_trades = [
                    {
                        "id": trade["id"],
                        "price": str(trade["price"]),
                        "qty": str(trade["qty"]),
                        "time": datetime.fromtimestamp(trade["time"] / 1000).isoformat(),
                        "isBuyerMaker": trade["isBuyerMaker"],
                    }
                    for trade in trades
                ]
                logger.debug(f"✅ 체결 내역 조회: {symbol} - {len(formatted_trades)}건")
                return formatted_trades
            else:
                logger.warning(f"⚠️ 체결 내역 조회 실패: Status {response.status_code}")
                return []

    except Exception as e:
        logger.error(f"❌ 체결 내역 조회 오류: {e}")
        return []


# =====================================================
# 📌 개선: 호가창 조회 (단일성 강화)
# =====================================================


async def get_order_book(symbol: str, limit: int = 20) -> dict:
    """
    호가창 조회 (개선 버전)
    
    Args:
        symbol: 거래 심볼
        limit: 호가 개수
        
    Returns:
        dict: {"bids": [...], "asks": [...]}
        
    Note:
        - 유효하지 않은 심볼: 빈 호가창 반환
        - API 실패: 빈 호가창 반환
    """
    if is_ci_environment():
        order_book = MockBinanceData.get_order_book(symbol, limit)
        logger.info(f"🔧 [CI Mock] 호가창: {symbol}")
        return order_book

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"{BINANCE_API_BASE}/depth",
                params={"symbol": symbol, "limit": limit}
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "bids": [[Decimal(bid[0]), Decimal(bid[1])] for bid in data.get("bids", [])],
                    "asks": [[Decimal(ask[0]), Decimal(ask[1])] for ask in data.get("asks", [])],
                }
            else:
                logger.warning(f"⚠️ 호가창 조회 실패: Status {response.status_code}")
                return {"bids": [], "asks": []}

    except Exception as e:
        logger.error(f"❌ 호가창 조회 오류: {e}")
        return {"bids": [], "asks": []}


# =====================================================
# 다중 가격 조회
# =====================================================


async def get_multiple_prices(symbols: list[str]) -> dict[str, Decimal]:
    """
    여러 코인 가격 일괄 조회
    
    Args:
        symbols: 심볼 리스트
        
    Returns:
        dict[str, Decimal]: 심볼별 가격 (유효한 심볼만)
    """
    if is_ci_environment():
        result = {}
        for symbol in symbols:
            price_str = MockBinanceData.get_price(symbol)
            if price_str is not None:  # 📌 개선: 유효한 심볼만 포함
                result[symbol] = Decimal(price_str)
        logger.info(f"🔧 [CI Mock] 다중 가격 조회: {len(result)}개 심볼")
        return result

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{BINANCE_API_BASE}/ticker/price")

            if response.status_code == 200:
                all_prices = response.json()
                result = {
                    item["symbol"]: Decimal(str(item["price"]))
                    for item in all_prices
                    if item["symbol"] in symbols
                }
                logger.info(f"✅ 다중 가격 조회: {len(result)}개 심볼")
                return result
            else:
                logger.error(f"❌ 다중 가격 조회 실패: Status {response.status_code}")
                return {}

    except Exception as e:
        logger.error(f"❌ 다중 가격 조회 오류: {e}")
        return {}


# =====================================================
# 기타 함수들
# =====================================================


async def test_connection() -> bool:
    """Binance API 연결 테스트"""
    if is_ci_environment():
        logger.info("🔧 [CI Mock] Binance API 연결 테스트: 성공")
        return True

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{BINANCE_API_BASE}/ping")
            return response.status_code == 200
    except Exception as e:
        logger.error(f"❌ Binance API 연결 오류: {e}")
        return False


async def get_server_time() -> int:
    """Binance 서버 시간 조회"""
    if is_ci_environment():
        return int(datetime.utcnow().timestamp() * 1000)

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{BINANCE_API_BASE}/time")
            if response.status_code == 200:
                return response.json()["serverTime"]
    except Exception:
        pass
    
    return int(datetime.utcnow().timestamp() * 1000)