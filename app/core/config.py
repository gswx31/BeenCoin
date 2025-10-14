# app/core/config.py - Pydantic v2 호환
try:
    from pydantic_settings import BaseSettings
    from pydantic import Field, computed_field
except ImportError:
    from pydantic import BaseSettings, Field

from typing import Optional
from dotenv import load_dotenv
import os
from pathlib import Path

# .env 파일 로드
load_dotenv()

class Settings(BaseSettings):
    # API 설정
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "BeenCoin API"
    
    # 데이터베이스 URL (간단한 방식)
    DATABASE_URL: str = Field(default="sqlite:///beencoin.db")
    
    # JWT 설정
    SECRET_KEY: str = "your-secret-key-change-in-production-please"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    
    # Binance API
    BINANCE_API_URL: str = "https://api.binance.com/api/v3"
    BINANCE_API_KEY: Optional[str] = None
    BINANCE_API_SECRET: Optional[str] = None
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # 거래 설정
    INITIAL_BALANCE: float = 1000000.0
    SUPPORTED_SYMBOLS: list = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT"]
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "allow"  # 추가 필드 허용

# 설정 인스턴스 생성
settings = Settings()

# DATABASE_URL을 절대 경로로 변환 (한 번만)
if settings.DATABASE_URL.startswith("sqlite:///"):
    db_file = settings.DATABASE_URL.replace("sqlite:///", "")
    # 상대 경로면 절대 경로로 변환
    if not os.path.isabs(db_file):
        project_root = Path(__file__).parent.parent.parent
        db_path = project_root / db_file
        settings.DATABASE_URL = f"sqlite:///{str(db_path).replace(os.sep, '/')}"

# 설정 출력
print("=" * 60)
print("⚙️  BeenCoin Settings")
print("=" * 60)
print(f"Database: {settings.DATABASE_URL}")
print(f"Initial Balance: ${settings.INITIAL_BALANCE:,.0f}")
print(f"Supported Coins: {', '.join(settings.SUPPORTED_SYMBOLS)}")
print(f"Token Expiry: {settings.ACCESS_TOKEN_EXPIRE_MINUTES} minutes")
print("=" * 60)