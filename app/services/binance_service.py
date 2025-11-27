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

import httpx
import os
import logging
import random
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Binance API 설정
BINANCE_API_BASE = "https://api.binance.com/api/v3"
TIMEOUT = httpx.Timeout(10.0)


# =====================================================
# CI 환경 감지 및 Mock 데이터
# =====================================================

def is_ci_environment() -> bool:
    """CI 환경 감지"""
    return os.getenv("CI", "").lower() == "true" or \
           os.getenv("MOCK_BINANCE", "").lower() == "true"


class MockBinanceData:
    """CI 환경용 Mock 데이터"""
    PRICES = {
        "BTCUSDT": "95000.00",
        "ETHUSDT": "3500.00",
        "BNBUSDT": "600.00",
        "ADAUSDT": "0.90",
        "XRPUSDT": "2.20",
        "SOLUSDT": "180.00",
        "DOGEUSDT": "0.35"
    }
    
    @classmethod
    def get_price(cls, symbol: str) -> str:
        return cls.PRICES.get(symbol, "100.00")
    
    @classmethod
    def get_ticker_24hr(cls, symbol: str) -> dict:
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
            "count": 1000
        }
    
    @classmethod
    def get_recent_trades(cls, symbol: str, limit: int = 100) -> List[Dict]:
        """Mock 체결 내역 생성"""
        base_price = float(cls.get_price(symbol))
        trades = []
        base_time = datetime.utcnow()
        
        for i in range(limit):
            # 가격 변동 ±0.5%
            price_variation = random.uniform(-0.005, 0.005)
            trade_price = base_price * (1 + price_variation)
            trade_qty = round(random.uniform(0.01, 2.0), 4)
            
            trades.append({
                "id": 1000000 + i,
                "price": f"{trade_price:.2f}",
                "qty": f"{trade_qty:.4f}",
                "time": (base_time - timedelta(seconds=i * 2)).isoformat(),
                "isBuyerMaker": random.choice([True, False])
            })
        
        return trades
    
    @classmethod
    def get_order_book(cls, symbol: str, limit: int = 20) -> Dict:
        """Mock 호가창 생성"""
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
        base_price = float(cls.get_price(symbol))
        klines = []
        
        # 인터벌에 따른 시간 간격 (분 단위)
        interval_minutes = {
            "1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30,
            "1h": 60, "2h": 120, "4h": 240, "6h": 360, "8h": 480,
            "12h": 720, "1d": 1440, "3d": 4320, "1w": 10080
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
            
            klines.append({
                "time": int(candle_time.timestamp() * 1000),
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": round(volume, 2)
            })
            
            # 다음 캔들의 기준 가격 업데이트
            base_price = close_price
        
        return klines


# =====================================================
# 1. 기본 시세 조회 함수
# =====================================================

async def get_current_price(symbol: str) -> Decimal:
    """
    현재가 조회
    
    Args:
        symbol: 거래 심볼 (예: BTCUSDT)
    
    Returns:
        Decimal: 현재가
    """
    # ✅ CI 환경이면 Mock 반환
    if is_ci_environment():
        price = MockBinanceData.get_price(symbol)
        logger.info(f"🔧 [CI Mock] 현재가: {symbol} = ${price}")
        return Decimal(price)
    
    # 실제 API 호출
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
            elif response.status_code == 451:
                logger.error(f"❌ 지역 제한: Binance API 접근 불가 (451)")
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


async def get_recent_trades(symbol: str, limit: int = 100) -> List[Dict]:
    """
    최근 체결 내역 조회
    
    실제 거래소의 체결 내역을 가져옵니다.
    이 데이터를 기반으로 시장가/지정가 주문을 체결합니다.
    
    Args:
        symbol: 거래 심볼
        limit: 조회할 거래 개수 (최대 1000)
    
    Returns:
        List[Dict]: 체결 내역 리스트
    """
    # ✅ CI 환경이면 Mock 반환
    if is_ci_environment():
        trades = MockBinanceData.get_recent_trades(symbol, limit)
        logger.info(f"🔧 [CI Mock] 체결 내역: {symbol} - {len(trades)}건")
        return trades
    
    # 실제 API 호출
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"{BINANCE_API_BASE}/trades",
                params={"symbol": symbol, "limit": min(limit, 1000)}
            )
            
            if response.status_code == 200:
                trades = response.json()
                
                formatted_trades = []
                for trade in trades:
                    formatted_trades.append({
                        "id": trade["id"],
                        "price": str(trade["price"]),
                        "qty": str(trade["qty"]),
                        "time": datetime.fromtimestamp(
                            trade["time"] / 1000
                        ).isoformat(),
                        "isBuyerMaker": trade["isBuyerMaker"]
                    })
                
                logger.debug(
                    f"✅ 체결 내역 조회: {symbol} - {len(formatted_trades)}건"
                )
                return formatted_trades
            elif response.status_code == 451:
                logger.error(f"❌ 지역 제한: Binance API 접근 불가 (451)")
                return []
            else:
                logger.warning(
                    f"⚠️ 체결 내역 조회 실패: Status {response.status_code}"
                )
                return []
    
    except httpx.TimeoutException:
        logger.error(f"❌ 체결 내역 조회 타임아웃: {symbol}")
        return []
    except Exception as e:
        logger.error(f"❌ 체결 내역 조회 오류: {e}")
        return []


async def get_multiple_prices(symbols: List[str]) -> Dict[str, Decimal]:
    """
    여러 코인 가격 일괄 조회
    
    Args:
        symbols: 심볼 리스트
    
    Returns:
        Dict[str, Decimal]: 심볼별 가격
    """
    # ✅ CI 환경이면 Mock 반환
    if is_ci_environment():
        result = {}
        for symbol in symbols:
            result[symbol] = Decimal(MockBinanceData.get_price(symbol))
        logger.info(f"🔧 [CI Mock] 다중 가격 조회: {len(result)}개 심볼")
        return result
    
    # 실제 API 호출
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{BINANCE_API_BASE}/ticker/price")
            
            if response.status_code == 200:
                all_prices = response.json()
                result = {}
                
                for item in all_prices:
                    if item["symbol"] in symbols:
                        result[item["symbol"]] = Decimal(str(item["price"]))
                
                logger.info(f"✅ 다중 가격 조회: {len(result)}개 심볼")
                return result
            elif response.status_code == 451:
                logger.error(f"❌ 지역 제한: Binance API 접근 불가 (451)")
                return {}
            else:
                logger.error(
                    f"❌ 다중 가격 조회 실패: Status {response.status_code}"
                )
                return {}
    
    except Exception as e:
        logger.error(f"❌ 다중 가격 조회 오류: {e}")
        return {}


# =====================================================
# 2. 실제 거래소 로직 - 시장가 주문
# =====================================================

async def execute_market_order_with_real_trades(
    symbol: str,
    side: str,
    quantity: Decimal,
    leverage: int = 1
) -> Dict:
    """
    ⭐ 실제 체결 내역 기반 시장가 주문 (핵심 개선!)
    
    실제 거래소처럼 동작:
    1. Binance 최근 체결 내역 조회 (500건)
    2. 실제 거래된 가격/수량으로 순차 체결
    3. 레버리지 적용 (100x → 거래량 100배)
    
    Args:
        symbol: BTCUSDT
        side: BUY or SELL
        quantity: 주문 수량 (레버리지 적용 전)
        leverage: 레버리지 배율 (1~125)
    
    Returns:
        Dict: 체결 결과
    """
    try:
        # 레버리지 적용된 실제 거래 수량
        actual_quantity = quantity * Decimal(str(leverage))
        
        logger.info(
            f"📊 시장가 주문: {side} {quantity} {symbol} "
            f"(레버리지 {leverage}x → 실제 {actual_quantity})"
        )
        
        # 1. 최근 체결 내역 조회 (500건) - Mock도 자동 적용됨
        recent_trades = await get_recent_trades(symbol, limit=500)
        
        if not recent_trades or len(recent_trades) == 0:
            # 체결 내역이 없으면 현재가로 즉시 전체 체결
            logger.warning(f"⚠️ 체결 내역 없음, 현재가로 체결: {symbol}")
            current_price = await get_current_price(symbol)
            
            return {
                "filled_quantity": quantity,
                "average_price": current_price,
                "total_cost": current_price * actual_quantity,
                "fills": [{
                    "price": current_price,
                    "quantity": actual_quantity,
                    "timestamp": datetime.utcnow().isoformat()
                }],
                "leverage": leverage,
                "actual_position_size": actual_quantity
            }
        
        # 2. 실제 거래량만큼 순차적으로 체결
        fills = []
        remaining = actual_quantity
        total_cost = Decimal("0")
        
        for trade in recent_trades:
            if remaining <= Decimal("0"):
                break
            
            # 거래 정보 추출
            trade_price = Decimal(str(trade["price"]))
            trade_qty = Decimal(str(trade["qty"]))
            
            if trade_price <= 0 or trade_qty <= 0:
                continue
            
            # 남은 수량보다 많으면 일부만 체결
            fill_qty = min(trade_qty, remaining)
            
            fills.append({
                "price": trade_price,
                "quantity": fill_qty,
                "timestamp": trade["time"]
            })
            
            total_cost += trade_price * fill_qty
            remaining -= fill_qty
        
        # 3. 모든 체결 내역을 다 써도 부족한 경우
        if remaining > Decimal("0"):
            logger.warning(
                f"⚠️ 체결 내역 부족, 현재가로 추가 체결: {remaining}"
            )
            current_price = await get_current_price(symbol)
            
            fills.append({
                "price": current_price,
                "quantity": remaining,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            total_cost += current_price * remaining
        
        # 4. 평균 체결가 계산
        average_price = total_cost / actual_quantity
        
        logger.info(
            f"✅ 시장가 체결 완료: {side} {quantity} {symbol}\n"
            f"   - 실제 거래: {actual_quantity} (레버리지 {leverage}x)\n"
            f"   - 평균 체결가: ${average_price:.2f}\n"
            f"   - 총 비용: ${total_cost:.2f}\n"
            f"   - 분할 체결: {len(fills)}건"
        )
        
        return {
            "filled_quantity": quantity,
            "average_price": average_price,
            "total_cost": total_cost,
            "fills": fills,
            "leverage": leverage,
            "actual_position_size": actual_quantity
        }
    
    except Exception as e:
        logger.error(f"❌ 시장가 주문 실행 오류: {e}")
        
        # 실패 시 현재가로 폴백
        try:
            current_price = await get_current_price(symbol)
            actual_quantity = quantity * Decimal(str(leverage))
            
            return {
                "filled_quantity": quantity,
                "average_price": current_price,
                "total_cost": current_price * actual_quantity,
                "fills": [{
                    "price": current_price,
                    "quantity": actual_quantity,
                    "timestamp": datetime.utcnow().isoformat()
                }],
                "leverage": leverage,
                "actual_position_size": actual_quantity
            }
        except:
            raise HTTPException(
                status_code=500,
                detail="시장가 주문 실행 실패"
            )


# =====================================================
# 3. 실제 거래소 로직 - 지정가 주문 체결 확인
# =====================================================

async def check_limit_order_execution(
    symbol: str,
    order_side: str,
    limit_price: Decimal,
    remaining_quantity: Decimal,
    leverage: int = 1
) -> Optional[Dict]:
    """
    ⭐ 지정가 주문 실시간 체결 확인 (핵심 개선!)
    
    실제 거래소처럼 동작:
    1. 최근 체결 내역에서 지정가 매칭 확인
    2. 매칭되는 거래만큼 부분 체결
    3. 레버리지 적용
    
    Args:
        symbol: BTCUSDT
        order_side: BUY or SELL
        limit_price: 지정가
        remaining_quantity: 남은 수량 (레버리지 적용 후)
        leverage: 레버리지
    
    Returns:
        None (체결 없음) 또는 체결 결과 Dict
    """
    try:
        # 최근 체결 내역 조회 - Mock도 자동 적용됨
        recent_trades = await get_recent_trades(symbol, limit=100)
        
        if not recent_trades:
            return None
        
        fills = []
        filled_total = Decimal("0")
        remaining = remaining_quantity
        
        for trade in recent_trades:
            if remaining <= Decimal("0"):
                break
            
            trade_price = Decimal(str(trade["price"]))
            trade_qty = Decimal(str(trade["qty"]))
            
            # 매수: 시장 가격 <= 지정가
            # 매도: 시장 가격 >= 지정가
            can_fill = False
            if order_side == "BUY" and trade_price <= limit_price:
                can_fill = True
            elif order_side == "SELL" and trade_price >= limit_price:
                can_fill = True
            
            if can_fill:
                # 부분 체결
                fill_qty = min(trade_qty, remaining)
                
                fills.append({
                    "price": trade_price,
                    "quantity": fill_qty,
                    "timestamp": trade["time"]
                })
                
                filled_total += fill_qty
                remaining -= fill_qty
        
        if filled_total > Decimal("0"):
            logger.info(
                f"📈 지정가 부분 체결: {symbol} {order_side}\n"
                f"   - 체결: {filled_total} / {remaining_quantity}\n"
                f"   - 남은 수량: {remaining}\n"
                f"   - 분할: {len(fills)}건"
            )
            
            return {
                "filled_quantity": filled_total,
                "fills": fills,
                "remaining": remaining
            }
        
        return None
    
    except Exception as e:
        logger.error(f"❌ 지정가 주문 체결 확인 오류: {e}")
        return None


# =====================================================
# 4. 하위 호환성 유지
# =====================================================

async def execute_market_order(symbol: str, side: str, quantity: Decimal) -> Decimal:
    """
    시장가 주문 실행 (하위 호환성)
    
    새 함수를 호출하고 평균가만 반환
    """
    result = await execute_market_order_with_real_trades(
        symbol=symbol,
        side=side,
        quantity=quantity,
        leverage=1
    )
    return result["average_price"]


# =====================================================
# 5. 기타 유틸리티 함수 (기존 호환성)
# =====================================================

async def get_24h_ticker(symbol: str) -> Optional[Dict]:
    """
    24시간 티커 정보 조회
    
    Args:
        symbol: 거래 심볼
    
    Returns:
        Dict: 티커 정보 또는 None
    """
    # ✅ CI 환경이면 Mock 반환
    if is_ci_environment():
        ticker = MockBinanceData.get_ticker_24hr(symbol)
        logger.info(f"🔧 [CI Mock] 24h 티커: {symbol}")
        return ticker
    
    # 실제 API 호출
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
            elif response.status_code == 451:
                logger.error(f"❌ 지역 제한: Binance API 접근 불가 (451)")
                return None
            else:
                logger.warning(
                    f"⚠️ 24h 티커 조회 실패: {symbol} - "
                    f"Status {response.status_code}"
                )
                return None
    
    except Exception as e:
        logger.error(f"❌ 24h 티커 조회 오류: {symbol} - {e}")
        return None


async def get_coin_info(symbol: str) -> Dict:
    """
    코인 정보 조회 (가격 + 24h 변동)
    
    market.py에서 사용
    
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
    
    market.py에서 사용
    
    Args:
        symbol: 거래 심볼
        interval: 시간 간격 (1m, 5m, 15m, 1h, 4h, 1d 등)
        limit: 조회할 캔들 개수
    
    Returns:
        List[Dict]: 캔들스틱 데이터
    """
    # ✅ CI 환경이면 Mock 반환
    if is_ci_environment():
        klines = MockBinanceData.get_klines(symbol, interval, limit)
        logger.info(f"🔧 [CI Mock] 과거 데이터: {symbol} - {len(klines)}개")
        return klines
    
    # 실제 API 호출
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
                
                logger.info(
                    f"✅ 과거 데이터 조회 성공: {symbol} - "
                    f"{len(formatted_data)}개"
                )
                return formatted_data
            elif response.status_code == 451:
                logger.error(f"❌ 지역 제한: Binance API 접근 불가 (451)")
                return []
            else:
                logger.error(
                    f"❌ 과거 데이터 조회 실패: "
                    f"Status {response.status_code}"
                )
                return []
    
    except Exception as e:
        logger.error(f"❌ 과거 데이터 조회 오류: {e}")
        return []


async def test_connection() -> bool:
    """
    Binance API 연결 테스트
    
    Returns:
        bool: 연결 성공 여부
    """
    # ✅ CI 환경이면 항상 성공
    if is_ci_environment():
        logger.info("🔧 [CI Mock] Binance API 연결 테스트: 성공")
        return True
    
    # 실제 API 호출
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{BINANCE_API_BASE}/ping")
            
            if response.status_code == 200:
                logger.info("✅ Binance API 연결 정상")
                return True
            elif response.status_code == 451:
                logger.error(f"❌ 지역 제한: Binance API 접근 불가 (451)")
                return False
            else:
                logger.error(
                    f"❌ Binance API 연결 실패: "
                    f"Status {response.status_code}"
                )
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
    # ✅ CI 환경이면 현재 시간 반환
    if is_ci_environment():
        server_time = int(datetime.utcnow().timestamp() * 1000)
        logger.info(f"🔧 [CI Mock] 서버 시간: {server_time}")
        return server_time
    
    # 실제 API 호출
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{BINANCE_API_BASE}/time")
            
            if response.status_code == 200:
                data = response.json()
                return data["serverTime"]
            elif response.status_code == 451:
                logger.error(f"❌ 지역 제한: Binance API 접근 불가 (451)")
                return 0
            else:
                return 0
    
    except Exception as e:
        logger.error(f"❌ 서버 시간 조회 오류: {e}")
        return 0


async def get_order_book(symbol: str, limit: int = 20) -> Dict:
    """
    호가창 조회
    
    Args:
        symbol: 거래 심볼
        limit: 호가 개수 (5, 10, 20, 50, 100, 500, 1000, 5000)
    
    Returns:
        Dict: {"bids": [[가격, 수량], ...], "asks": [[가격, 수량], ...]}
    """
    # ✅ CI 환경이면 Mock 반환
    if is_ci_environment():
        order_book = MockBinanceData.get_order_book(symbol, limit)
        logger.info(f"🔧 [CI Mock] 호가창: {symbol} - {limit}호가")
        return order_book
    
    # 실제 API 호출
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"{BINANCE_API_BASE}/depth",
                params={"symbol": symbol, "limit": limit}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "bids": [
                        [Decimal(p), Decimal(q)] for p, q in data["bids"]
                    ],
                    "asks": [
                        [Decimal(p), Decimal(q)] for p, q in data["asks"]
                    ]
                }
            elif response.status_code == 451:
                logger.error(f"❌ 지역 제한: Binance API 접근 불가 (451)")
                return {"bids": [], "asks": []}
            else:
                logger.error(
                    f"❌ 호가창 조회 실패: Status {response.status_code}"
                )
                return {"bids": [], "asks": []}
    
    except Exception as e:
        logger.error(f"❌ 호가창 조회 오류: {e}")
        return {"bids": [], "asks": []}