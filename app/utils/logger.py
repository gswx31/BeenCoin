# app/utils/logger.py - 새 파일
import logging
import sys
from datetime import datetime
from pathlib import Path

def setup_logger(name: str = "beencoin", level: str = "INFO") -> logging.Logger:
    """로거 설정"""
    
    # 로그 디렉토리 생성
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # 포맷터 생성
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    
    # 파일 핸들러 (일별 로그)
    log_file = log_dir / f"beencoin_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # 에러 로그 파일 (별도)
    error_log_file = log_dir / f"error_{datetime.now().strftime('%Y%m%d')}.log"
    error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    
    # 핸들러 추가
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    
    return logger

# 전역 로거
logger = setup_logger()


# ================================
# app/main.py에 로깅 미들웨어 추가
# ================================
from fastapi import FastAPI, Request
from app.utils.logger import logger
import time

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """모든 HTTP 요청 로깅"""
    start_time = time.time()
    
    # 요청 정보 로깅
    logger.info(f"📥 {request.method} {request.url.path}")
    
    # 요청 처리
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # 응답 로깅
        logger.info(
            f"📤 {request.method} {request.url.path} "
            f"- Status: {response.status_code} "
            f"- Time: {process_time:.3f}s"
        )
        
        # 커스텀 헤더 추가
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"❌ {request.method} {request.url.path} "
            f"- Error: {str(e)} "
            f"- Time: {process_time:.3f}s"
        )
        raise


# ================================
# app/services/order_service.py에 로깅 추가
# ================================
from app.utils.logger import logger

async def create_order(session: Session, user_id: int, order_data: OrderCreate) -> Order:
    logger.info(
        f"📝 Creating order: User={user_id}, "
        f"Symbol={order_data.symbol}, "
        f"Side={order_data.side}, "
        f"Type={order_data.order_type}"
    )
    
    # ... 주문 생성 로직
    
    if order.order_type == 'MARKET':
        logger.info(f"✅ Market order executed: Order ID={order.id}, Price=${price}")
    elif order.order_type == 'LIMIT':
        logger.info(f"⏳ Limit order created: Order ID={order.id}, Target=${order.price}")
    
    return order

def update_position(
    session: Session,
    user_id: int,
    symbol: str,
    side: str,
    quantity: Decimal,
    price: Decimal,
    fee: Decimal
):
    logger.debug(
        f"📊 Updating position: User={user_id}, "
        f"Symbol={symbol}, Side={side}, "
        f"Qty={quantity}, Price=${price}"
    )
    
    # ... 포지션 업데이트
    
    if side == 'BUY':
        logger.info(
            f"💰 Position updated (BUY): User={user_id}, "
            f"New Qty={position.quantity}, "
            f"Avg Price=${position.average_price}"
        )
    elif side == 'SELL':
        logger.info(
            f"💸 Position updated (SELL): User={user_id}, "
            f"Remaining Qty={position.quantity}, "
            f"Profit=${profit}"
        )


# ================================
# app/services/binance_service.py에 로깅 추가
# ================================
from app.utils.logger import logger

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
                price = Decimal(data['price'])
                logger.debug(f"💱 Price fetched: {symbol} = ${price}")
                return price
            else:
                logger.error(
                    f"❌ Binance API error: Status {response.status_code}"
                )
                raise HTTPException(
                    status_code=503,
                    detail=f"Binance API error: {response.status_code}"
                )
    except httpx.TimeoutException:
        logger.error(f"⏱️ Binance API timeout for {symbol}")
        raise HTTPException(status_code=503, detail="Binance API timeout")
    except Exception as e:
        logger.error(f"❌ Price fetch failed for {symbol}: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Price fetch failed: {str(e)}")

