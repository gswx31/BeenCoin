# app/tasks/scheduler.py
"""
백그라운드 작업 스케줄러
- 대기 중인 주문 체크
- 가격 알림 체크
"""
import asyncio
import logging
from sqlmodel import Session
from app.core.database import engine
from app.services.order_service import check_pending_orders
from app.routers.alerts import check_price_alerts

logger = logging.getLogger(__name__)


async def run_background_tasks():
    """
    백그라운드 작업 실행
    
    10초마다:
    - 대기 중인 주문 체크
    - 가격 알림 체크
    """
    
    logger.info("🚀 백그라운드 작업 시작")
    
    while True:
        try:
            with Session(engine) as session:
                # 1. 대기 주문 체크
                logger.debug("⏰ 대기 주문 체크 중...")
                await check_pending_orders(session)
                
                # 2. 가격 알림 체크
                logger.debug("🔔 가격 알림 체크 중...")
                await check_price_alerts(session)
            
            # 10초 대기
            await asyncio.sleep(10)
        
        except Exception as e:
            logger.error(f"❌ 백그라운드 작업 오류: {e}")
            await asyncio.sleep(10)


def start_background_tasks():
    """백그라운드 작업 시작 (FastAPI 시작 시 호출)"""
    
    asyncio.create_task(run_background_tasks())
    logger.info("✅ 백그라운드 작업 스케줄러 등록 완료")