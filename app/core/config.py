# app/core/config.py
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings

from typing import Optional
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

class Settings(BaseSettings):
    # API 설정
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "BeenCoin API"
    
    # 데이터베이스
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./beencoin.db")
    
    # JWT 설정
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-please")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24시간
    
    # Binance API (Public API 사용, 키 불필요)
    BINANCE_API_URL: str = "https://api.binance.com/api/v3"
    BINANCE_API_KEY: Optional[str] = os.getenv("BINANCE_API_KEY")
    BINANCE_API_SECRET: Optional[str] = os.getenv("BINANCE_API_SECRET")
    
    # Redis (선택사항)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    
    # 거래 설정
    INITIAL_BALANCE: float = 1000000.0  # 초기 잔액 100만원
    SUPPORTED_SYMBOLS: list = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT"]
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()

# 설정 출력
print("=" * 60)
print("⚙️  BeenCoin Settings")
print("=" * 60)
print(f"Database: {settings.DATABASE_URL}")
print(f"Initial Balance: ${settings.INITIAL_BALANCE:,.0f}")
print(f"Supported Coins: {', '.join(settings.SUPPORTED_SYMBOLS)}")
print(f"Token Expiry: {settings.ACCESS_TOKEN_EXPIRE_MINUTES} minutes")
print("=" * 60)