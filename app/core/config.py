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
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # 데이터베이스 설정
    DATABASE_URL: str = "sqlite:///./beencoin.db"
    
    # JWT 설정
    SECRET_KEY: str = "your-secret-key-change-in-production-please"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24시간
    
    # CORS 설정 - 문자열로 받아서 나중에 파싱
    CORS_ORIGINS_STR: str = "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000"
    
    # Binance API
    BINANCE_API_URL: str = "https://api.binance.com/api/v3"
    BINANCE_API_KEY: str | None = None
    BINANCE_API_SECRET: str | None = None
    
    # Redis (선택사항)
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # 거래 설정 - 문자열로 받아서 나중에 파싱
    INITIAL_BALANCE: float = 1000000.0
    SUPPORTED_SYMBOLS_STR: str = "BTCUSDT,ETHUSDT,BNBUSDT,ADAUSDT"
    
    # 로깅
    LOG_LEVEL: str = "INFO"
    
    # Pydantic v2 스타일 설정
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

# 설정 인스턴스 생성
settings = Settings()

# DATABASE_URL을 절대 경로로 변환
if settings.DATABASE_URL.startswith("sqlite:///"):
    db_file = settings.DATABASE_URL.replace("sqlite:///", "")
    
    # 상대 경로면 절대 경로로 변환
    if not os.path.isabs(db_file):
        project_root = Path(__file__).parent.parent.parent
        db_path = project_root / db_file
        settings.DATABASE_URL = f"sqlite:///{str(db_path).replace(os.sep, '/')}"

# 환경 변수에서 값 읽기
if os.getenv("SECRET_KEY"):
    settings.SECRET_KEY = os.getenv("SECRET_KEY")

if os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"):
    settings.ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

if os.getenv("INITIAL_BALANCE"):
    settings.INITIAL_BALANCE = float(os.getenv("INITIAL_BALANCE"))

if os.getenv("LOG_LEVEL"):
    settings.LOG_LEVEL = os.getenv("LOG_LEVEL")

if os.getenv("API_HOST"):
    settings.API_HOST = os.getenv("API_HOST")

if os.getenv("API_PORT"):
    settings.API_PORT = int(os.getenv("API_PORT"))
