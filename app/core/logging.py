"""
구조적 로깅 — JSON 형식, correlation ID 포함.
"""
import logging
import json
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Optional

# Correlation ID — 요청별 추적용
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        cid = correlation_id_var.get()
        if cid:
            log_obj["correlation_id"] = cid

        # 예외 정보
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # 추가 컨텍스트
        for key, value in record.__dict__.items():
            if key not in ("name", "msg", "args", "levelname", "levelno", "pathname",
                           "filename", "module", "exc_info", "exc_text", "stack_info",
                           "lineno", "funcName", "created", "msecs", "relativeCreated",
                           "thread", "threadName", "processName", "process", "message",
                           "taskName", "asctime"):
                log_obj[key] = value

        return json.dumps(log_obj, ensure_ascii=False, default=str)


def setup_logging(level: str = "INFO"):
    """루트 로거 설정."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # uvicorn access 로그는 너무 시끄러우니 WARN으로
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def generate_correlation_id() -> str:
    return uuid.uuid4().hex[:12]


def set_correlation_id(cid: str):
    correlation_id_var.set(cid)
