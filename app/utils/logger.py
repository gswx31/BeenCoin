# app/utils/logger.py
"""
통합 로깅 시스템
모든 파일에서 일관되게 사용할 수 있는 로거 설정
"""
from datetime import datetime
import logging
from pathlib import Path
import sys

from app.core.config import settings

# 로그 디렉토리 생성
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# 로그 포맷
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(name: str) -> logging.Logger:
    """
    애플리케이션 로거 설정

    Args:
        name: 로거 이름 (보통 __name__ 사용)

    Returns:
        설정된 Logger 인스턴스

    사용법:
        from app.utils.logger import setup_logger
        logger = setup_logger(__name__)

        logger.info("정보 로그")
        logger.warning("경고 로그")
        logger.error("에러 로그")
        logger.critical("치명적 에러")
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))

    # 핸들러가 이미 있으면 추가하지 않음 (중복 방지)
    if logger.handlers:
        return logger

    # 1. 콘솔 핸들러 (터미널 출력)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    # 2. 일반 로그 파일 핸들러 (일별 로그)
    today = datetime.now().strftime("%Y-%m-%d")
    file_handler = logging.FileHandler(LOG_DIR / f"app_{today}.log", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    # 3. 에러 로그 파일 핸들러 (ERROR 이상만 별도 저장)
    error_handler = logging.FileHandler(LOG_DIR / f"error_{today}.log", encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    # 핸들러 추가
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)

    return logger


# 기본 로거 (import하여 바로 사용 가능)
logger = setup_logger("beencoin")

# 로그 레벨별 사용 예시 출력 (개발 환경에서만)
if settings.LOG_LEVEL == "DEBUG":
    logger.debug("디버그 로그 - 상세한 진단 정보")
    logger.info("정보 로그 - 일반 실행 정보")
    logger.warning("경고 로그 - 주의가 필요한 상황")
    logger.error("에러 로그 - 실패한 작업")
    logger.critical("치명적 로그 - 시스템 중단 위험")
