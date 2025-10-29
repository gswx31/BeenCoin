# app/services/binance_service.py
"""
Binance API 서비스 - Redis 캐싱 통합 버전
기존 코드 + Redis 캐싱 + 성능 최적화
"""
import httpx
from decimal import Decimal
from typing import Dict, List, Optional
from fastapi import HTTPException
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Binance API URL
BINANCE_API_BASE = "https://api.binance.com/api/v3"

# 타임아웃 설정
TIMEOUT = httpx.Timeout(10.0, connect=5.0)

# 재시도 설정
MAX_RETRIES = 3

# ✅ Redis 캐시 (없으면 무시)
try:
    from app.cache.redis_cache import redis_cache
    REDIS_AVAILABLE = True
    logger.info("✅ Redis 캐시 사용 가능")
except ImportError:
    REDIS_AVAILABLE = False
    redis_cache = None
    logger.warning("⚠️ Redis 캐시 비활성화 (redis_cache 모듈 없음)")


async def get_current_price(symbol: str) -> Decimal:
    """
    현재 가격 조회 (Redis 캐시 우선)
    
    1. Redis 캐시 확인 (있으면 즉시 반환)
    2. 없으면 Binance API 호출
    3. 결과를 캐시에 저장 (TTL: 1초)
    
    Args:
        symbol: 거래 심볼 (예: BTCUSDT)
    
    Returns:
        Decimal: 현재 가격
    
    Raises:
        HTTPException: API 호출 실패 시
    """
    
    # ✅ 1단계: Redis 캐시 확인
    if REDIS_AVAILABLE and redis_cache:
        try:
            cached_price = await redis_cache.get_price(symbol)
            if cached_price is not None:
                logger.debug(f"💾 캐시 히트: {symbol} = ${cached_price}")
                return Decimal(str(cached_price))
        except Exception as e:
            logger.debug(f"캐시 조회 실패 (무시): {e}")
    
    # ✅ 2단계: Binance API 호출 (재시도 로직)
    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.get(
                    f"{BINANCE_API_BASE}/ticker/price",
                    params={"symbol": symbol}
                )
                
                # 상태 코드 확인
                if response.status_code == 200:
                    data = response.json()
                    price = Decimal(str(data["price"]))
                    
                    # ✅ 3단계: 캐시 저장
                    if REDIS_AVAILABLE and redis_cache:
                        try:
                            await redis_cache.set_price(symbol, float(price), ttl=1)
                        except Exception as e:
                            logger.debug(f"캐시 저장 실패 (무시): {e}")
                    
                    logger.info(f"🌐 API 호출: {symbol} = ${price}")
                    return price
                
                elif response.status_code == 400:
                    logger.error(f"❌ 잘못된 심볼: {symbol}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"유효하지 않은 거래 심볼: {symbol}"
                    )
                
                else:
                    logger.warning(f"⚠️ Binance API 오류: Status {response.status_code}")
                    if attempt < MAX_RETRIES - 1:
                        continue
                    raise HTTPException(
                        status_code=503,
                        detail=f"시장 가격 조회 실패 (상태 코드: {response.status_code})"
                    )
        
        except httpx.TimeoutException:
            logger.warning(f"⏱️ 타임아웃 (시도 {attempt + 1}/{MAX_RETRIES}): {symbol}")
            if attempt < MAX_RETRIES - 1:
                continue
            raise HTTPException(
                status_code=503,
                detail=f"{symbol} 가격 조회 시간 초과"
            )
        
        except httpx.ConnectError:
            logger.error(f"❌ 연결 실패 (시도 {attempt + 1}/{MAX_RETRIES}): {symbol}")
            if attempt < MAX_RETRIES - 1:
                continue
            raise HTTPException(
                status_code=503,
                detail="Binance API 연결 실패"
            )
        
        except KeyError as e:
            logger.error(f"❌ 응답 파싱 실패: {e}")
            raise HTTPException(
                status_code=500,
                detail="가격 데이터 형식 오류"
            )
        
        except Exception as e:
            logger.error(f"❌ 예상치 못한 오류: {e}")
            if attempt < MAX_RETRIES - 1:
                continue
            raise HTTPException(
                status_code=500,
                detail=f"가격 조회 중 오류 발생: {str(e)}"
            )
    
    raise HTTPException(
        status_code=503,
        detail=f"{symbol} 가격 조회 실패 (최대 재시도 횟수 초과)"
    )


async def get_multiple_prices(symbols: List[str]) -> Dict[str, Decimal]:
    """
    여러 심볼의 가격을 동시에 조회 (Redis 캐시 최적화)
    
    1. Redis에서 캐시된 가격 일괄 조회
    2. 없는 것만 Binance API 호출
    3. 결과 캐시 저장
    
    Args:
        symbols: 심볼 리스트
    
    Returns:
        Dict[str, Decimal]: 심볼별 가격
    """
    
    result = {}
    missing_symbols = list(symbols)
    
    # ✅ 1단계: Redis 캐시 일괄 조회
    if REDIS_AVAILABLE and redis_cache:
        try:
            cached = await redis_cache.get_multiple_prices(symbols)
            for symbol, price in cached.items():
                result[symbol] = Decimal(str(price))
                if symbol in missing_symbols:
                    missing_symbols.remove(symbol)
            
            if cached:
                logger.info(f"💾 캐시 히트: {len(cached)}개 심볼")
        except Exception as e:
            logger.debug(f"캐시 일괄 조회 실패 (무시): {e}")
    
    # ✅ 2단계: 없는 것만 API 호출
    if missing_symbols:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.get(f"{BINANCE_API_BASE}/ticker/price")
                
                if response.status_code == 200:
                    all_prices = response.json()
                    
                    for item in all_prices:
                        symbol = item["symbol"]
                        if symbol in missing_symbols:
                            price = Decimal(str(item["price"]))
                            result[symbol] = price
                            
                            # ✅ 3단계: 캐시 저장
                            if REDIS_AVAILABLE and redis_cache:
                                try:
                                    await redis_cache.set_price(symbol, float(price), ttl=1)
                                except:
                                    pass
                    
                    logger.info(f"🌐 API 호출: {len(missing_symbols)}개 심볼")
                else:
                    logger.error(f"❌ 다중 가격 조회 실패: Status {response.status_code}")
        
        except Exception as e:
            logger.error(f"❌ 다중 가격 조회 오류: {e}")
    
    # 통계 로그
    if len(result) > 0:
        cache_hits = len(result) - len(missing_symbols)
        hit_rate = (cache_hits / len(result)) * 100 if result else 0
        logger.info(f"📊 캐시 히트율: {hit_rate:.1f}% ({cache_hits}/{len(result)})")
    
    return result


async def execute_market_order(symbol: str, side: str, quantity: Decimal) -> Decimal:
    """
    시장가 주문 실행 (시뮬레이션)
    
    실제 거래소 주문이 아니라 현재가를 반환합니다.
    
    Args:
        symbol: 거래 심볼
        side: BUY 또는 SELL
        quantity: 수량
    
    Returns:
        Decimal: 체결 가격
    """
    
    logger.info(f"🔄 시장가 주문 시뮬레이션: {side} {quantity} {symbol}")
    
    # 현재가 조회 (캐시 우선)
    price = await get_current_price(symbol)
    
    logger.info(f"✅ 체결 가격: ${price}")
    return price


async def get_24h_ticker(symbol: str) -> Optional[Dict]:
    """
    24시간 티커 정보 조회
    
    Args:
        symbol: 거래 심볼
    
    Returns:
        Dict: 티커 정보 또는 None
    """
    
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"{BINANCE_API_BASE}/ticker/24hr",
                params={"symbol": symbol}
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.debug(f"✅ 24h 티커 조회 성공: {symbol}")
                return data
            else:
                logger.warning(f"⚠️ 24h 티커 조회 실패: {symbol} - Status {response.status_code}")
                return None
    
    except Exception as e:
        logger.error(f"❌ 24h 티커 조회 오류: {symbol} - {e}")
        return None


async def get_coin_info(symbol: str) -> Dict:
    """
    코인 정보 조회 (가격 + 24h 변동)
    
    Args:
        symbol: 거래 심볼
    
    Returns:
        Dict: 코인 정보
    """
    
    try:
        ticker = await get_24h_ticker(symbol)
        
        if ticker:
            return {
                "symbol": symbol,
                "price": ticker.get("lastPrice", "0"),
                "change": ticker.get("priceChangePercent", "0"),
                "volume": ticker.get("volume", "0"),
                "high": ticker.get("highPrice", "0"),
                "low": ticker.get("lowPrice", "0")
            }
        else:
            # 티커 실패 시 최소한 현재가라도 조회
            price = await get_current_price(symbol)
            return {
                "symbol": symbol,
                "price": str(price),
                "change": "0",
                "volume": "0",
                "high": "0",
                "low": "0"
            }
    
    except Exception as e:
        logger.error(f"❌ 코인 정보 조회 실패: {symbol} - {e}")
        raise HTTPException(
            status_code=503,
            detail=f"{symbol} 정보 조회 실패"
        )


async def get_historical_data(
    symbol: str,
    interval: str = "1h",
    limit: int = 100
) -> List[Dict]:
    """
    과거 데이터 조회 (차트용)
    
    Args:
        symbol: 거래 심볼
        interval: 시간 간격 (1m, 5m, 15m, 1h, 4h, 1d 등)
        limit: 조회할 캔들 개수
    
    Returns:
        List[Dict]: 캔들스틱 데이터
    """
    
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"{BINANCE_API_BASE}/klines",
                params={
                    "symbol": symbol,
                    "interval": interval,
                    "limit": limit
                }
            )
            
            if response.status_code == 200:
                klines = response.json()
                
                formatted_data = []
                for k in klines:
                    formatted_data.append({
                        "time": k[0],
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5])
                    })
                
                logger.info(f"✅ 과거 데이터 조회 성공: {symbol} - {len(formatted_data)}개")
                return formatted_data
            else:
                logger.error(f"❌ 과거 데이터 조회 실패: Status {response.status_code}")
                return []
    
    except Exception as e:
        logger.error(f"❌ 과거 데이터 조회 오류: {e}")
        return []


async def get_recent_trades(symbol: str, limit: int = 50) -> List[Dict]:
    """
    최근 거래 내역 조회
    
    Args:
        symbol: 거래 심볼
        limit: 조회할 거래 개수
    
    Returns:
        List[Dict]: 거래 내역
    """
    
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"{BINANCE_API_BASE}/trades",
                params={
                    "symbol": symbol,
                    "limit": limit
                }
            )
            
            if response.status_code == 200:
                trades = response.json()
                
                formatted_trades = []
                for trade in trades:
                    formatted_trades.append({
                        "id": trade["id"],
                        "price": float(trade["price"]),
                        "quantity": float(trade["qty"]),
                        "time": datetime.fromtimestamp(trade["time"] / 1000).isoformat(),
                        "isBuyerMaker": trade["isBuyerMaker"]
                    })
                
                logger.debug(f"✅ 거래 내역 조회 성공: {symbol} - {len(formatted_trades)}개")
                return formatted_trades
            else:
                logger.warning(f"⚠️ 거래 내역 조회 실패: Status {response.status_code}")
                return []
    
    except Exception as e:
        logger.error(f"❌ 거래 내역 조회 오류: {e}")
        return []


async def test_connection() -> bool:
    """
    Binance API 연결 테스트
    
    Returns:
        bool: 연결 성공 여부
    """
    
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{BINANCE_API_BASE}/ping")
            
            if response.status_code == 200:
                logger.info("✅ Binance API 연결 정상")
                return True
            else:
                logger.error(f"❌ Binance API 연결 실패: Status {response.status_code}")
                return False
    
    except Exception as e:
        logger.error(f"❌ Binance API 연결 오류: {e}")
        return False


async def get_server_time() -> int:
    """
    Binance 서버 시간 조회
    
    Returns:
        int: 서버 타임스탬프 (밀리초)
    """
    
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{BINANCE_API_BASE}/time")
            
            if response.status_code == 200:
                data = response.json()
                return data["serverTime"]
            else:
                return 0
    
    except Exception as e:
        logger.error(f"❌ 서버 시간 조회 오류: {e}")
        return 0


# ================================
# 추가 고급 기능
# ================================

async def get_order_book(symbol: str, limit: int = 20) -> Dict:
    """
    호가창 조회
    
    Args:
        symbol: 거래 심볼
        limit: 호가 개수 (5, 10, 20, 50, 100, 500, 1000, 5000)
    
    Returns:
        Dict: {"bids": [[가격, 수량], ...], "asks": [[가격, 수량], ...]}
    """
    
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"{BINANCE_API_BASE}/depth",
                params={"symbol": symbol, "limit": limit}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "bids": [[Decimal(p), Decimal(q)] for p, q in data["bids"]],
                    "asks": [[Decimal(p), Decimal(q)] for p, q in data["asks"]]
                }
            else:
                logger.error(f"❌ 호가창 조회 실패: Status {response.status_code}")
                return {"bids": [], "asks": []}
    
    except Exception as e:
        logger.error(f"❌ 호가창 조회 오류: {e}")
        return {"bids": [], "asks": []}


async def check_binance_status() -> bool:
    """
    Binance API 상태 확인
    
    Returns:
        bool: 정상 여부
    """
    return await test_connection()