# app/core/config.py
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    from pydantic import BaseSettings

from typing import List
from dotenv import load_dotenv
import os
from pathlib import Path

# .env 파일 로드
load_dotenv()


class Settings(BaseSettings):
    # API 설정
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "BeenCoin API"
    VERSION: str = "2.0.0"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # 데이터베이스 설정
    DATABASE_URL: str = "sqlite:///./beencoin.db"
    DB_ECHO: bool = False
    
    # 성능 최적화 설정
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_PRE_PING: bool = True
    
    # 캐시 설정
    CACHE_TTL: int = 5  # 초
    
    # JWT 설정
    SECRET_KEY: str = "your-secret-key-change-in-production-please-make-it-very-long-and-random"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24시간
    
    # CORS 설정
    CORS_ORIGINS_STR: str = "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000"
    
    # Binance API
    BINANCE_API_URL: str = "https://api.binance.com/api/v3"
    BINANCE_API_KEY: str | None = None
    BINANCE_API_SECRET: str | None = None
    
    # 거래 설정
    INITIAL_BALANCE: float = 1000000.0
    SUPPORTED_SYMBOLS_STR: str = "BTCUSDT,ETHUSDT,BNBUSDT,ADAUSDT,XRPUSDT,SOLUSDT,DOGEUSDT"
    
    # 로깅
    LOG_LEVEL: str = "INFO"
    
    # Pydantic v2 설정
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="allow"
    )
    
    @property
    def CORS_ORIGINS(self) -> List[str]:
        """CORS_ORIGINS를 리스트로 반환"""
        cors_str = os.getenv("CORS_ORIGINS", self.CORS_ORIGINS_STR)
        return [origin.strip() for origin in cors_str.split(",")]
    
    @property
    def SUPPORTED_SYMBOLS(self) -> List[str]:
        """SUPPORTED_SYMBOLS를 리스트로 반환"""
        symbols_str = os.getenv("SUPPORTED_SYMBOLS", self.SUPPORTED_SYMBOLS_STR)
        return [symbol.strip() for symbol in symbols_str.split(",")]
    # Redis 설정
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_ENABLED: bool = True
    
    # 성능 설정
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    
    # API 타임아웃
    BINANCE_TIMEOUT: int = 10
    HTTP_TIMEOUT: int = 30
    
    class Config:
        env_file = ".env"

# 설정 인스턴스 생성
settings = Settings()

# DATABASE_URL을 절대 경로로 변환
if settings.DATABASE_URL.startswith("sqlite:///"):
    db_file = settings.DATABASE_URL.replace("sqlite:///", "")
    
    if not os.path.isabs(db_file):
        project_root = Path(__file__).parent.parent.parent
        db_path = project_root / db_file
        settings.DATABASE_URL = f"sqlite:///{str(db_path).replace(os.sep, '/')}"

# 환경 변수 오버라이드
if os.getenv("SECRET_KEY"):
    settings.SECRET_KEY = os.getenv("SECRET_KEY")

if os.getenv("INITIAL_BALANCE"):
    settings.INITIAL_BALANCE = float(os.getenv("INITIAL_BALANCE"))