from app.background_tasks.celery_app import celery_app
from app.services.order_service import update_position
from app.core.database import engine
from sqlmodel import Session, select
from app.models.database import User
from app.services.binance_service import get_current_price
import asyncio


