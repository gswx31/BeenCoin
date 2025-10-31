# app/tasks/scheduler.py
"""
백그라운드 작업 스케줄러
- 대기 중인 주문 체크
- 손절/익절 자동 체결
- 가격 알림 체크
"""
import asyncio
import logging
from sqlmodel import Session
from app.core.database import engine
from app.services.order_service import check_pending_orders
from app.services.stop_loss_take_profit_service import (
    check_stop_loss_take_profit_orders,
    check_futures_stop_loss_take_profit
)
from app.routers.alerts import check_price_alerts

logger = logging.getLogger(__name__)


async def run_background_tasks():
    """
    백그라운드 작업 실행
    
    5초마다:
    - 대기 중인 주문 체크
    - 손절/익절 자동 체결 체크 ⭐ NEW
    - 가격 알림 체크
    """
    
    logger.info("🚀 백그라운드 작업 시작")
    
    while True:
        try:
            with Session(engine) as session:
                # 1. 대기 주문 체크 (지정가 등)
                logger.debug("⏰ 대기 주문 체크 중...")
                await check_pending_orders(session)
                
                # 2. ⭐ 손절/익절 자동 체결 체크 (현물)
                logger.debug("🔴🟢 현물 손절/익절 체크 중...")
                await check_stop_loss_take_profit_orders(session)
                
                # 3. ⭐ 손절/익절 자동 체결 체크 (선물)
                logger.debug("🔴🟢 선물 손절/익절 체크 중...")
                await check_futures_stop_loss_take_profit(session)
                
                # 4. 가격 알림 체크
                logger.debug("🔔 가격 알림 체크 중...")
                await check_price_alerts(session)
            
            # 5초 대기 (빠른 응답을 위해 10초 → 5초로 단축)
            await asyncio.sleep(5)
        
        except Exception as e:
            logger.error(f"❌ 백그라운드 작업 오류: {e}")
            await asyncio.sleep(5)


def start_background_tasks():
    """백그라운드 작업 시작 (FastAPI 시작 시 호출)"""
    
    asyncio.create_task(run_background_tasks())
    logger.info("✅ 백그라운드 작업 스케줄러 등록 완료")
    logger.info("   - 대기 주문 체크")
    logger.info("   - 손절/익절 자동 체결 ⭐")
    logger.info("   - 가격 알림 체크")