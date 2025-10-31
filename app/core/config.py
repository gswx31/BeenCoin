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
    DB_POOL_TIMEOUT: int = 30
    
    # 캐시 설정
    CACHE_TTL: int = 5  # 초
    CACHE_ENABLED: bool = True
    
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
    BINANCE_TIMEOUT: int = 10
    
    # 거래 설정
    INITIAL_BALANCE: float = 1000000.0
    SUPPORTED_SYMBOLS_STR: str = "BTCUSDT,ETHUSDT,BNBUSDT,ADAUSDT,XRPUSDT,SOLUSDT,DOGEUSDT"
    
    # Redis 설정
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # 로깅
    LOG_LEVEL: str = "INFO"
    
    # HTTP 타임아웃
    HTTP_TIMEOUT: int = 30
    
    # Pydantic v2 설정 (class Config 제거하고 이것만 사용)
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="allow"
    )
    
    def get_cors_origins(self) -> List[str]:
        """CORS_ORIGINS를 리스트로 반환"""
        cors_str = os.getenv("CORS_ORIGINS", self.CORS_ORIGINS_STR)
        return [origin.strip() for origin in cors_str.split(",")]
    
    def get_supported_symbols(self) -> List[str]:
        """SUPPORTED_SYMBOLS를 리스트로 반환"""
        symbols_str = os.getenv("SUPPORTED_SYMBOLS", self.SUPPORTED_SYMBOLS_STR)
        return [symbol.strip() for symbol in symbols_str.split(",")]
    # 손절/익절 기본 비율
    DEFAULT_STOP_LOSS_PERCENT: float = 3.0  # -3% 손절
    DEFAULT_TAKE_PROFIT_PERCENT: float = 6.0  # +6% 익절 (2:1 비율)
    
    # 자동 손절/익절 설정 활성화
    AUTO_STOP_LOSS_ENABLED: bool = True
    AUTO_TAKE_PROFIT_ENABLED: bool = True
    
    # OCO (One-Cancels-the-Other) 활성화
    OCO_ENABLED: bool = True

# 설정 인스턴스 생성
settings = Settings()

# CORS_ORIGINS와 SUPPORTED_SYMBOLS를 속성으로 추가
settings.CORS_ORIGINS = settings.get_cors_origins()
settings.SUPPORTED_SYMBOLS = settings.get_supported_symbols()

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

# 디버깅 정보 출력
if settings.LOG_LEVEL == "DEBUG":
    print("=" * 60)
    print("⚙️  BeenCoin Configuration")
    print("=" * 60)
    print(f"Database: {settings.DATABASE_URL}")
    print(f"CORS Origins: {settings.CORS_ORIGINS}")
    print(f"Supported Symbols: {settings.SUPPORTED_SYMBOLS}")
    print("=" * 60)