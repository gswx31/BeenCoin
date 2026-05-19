"""
표준화된 에러 응답 — 일관된 JSON 구조 + 에러 코드.
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.logging import correlation_id_var


def _error_response(status_code: int, code: str, message: str, details=None) -> JSONResponse:
    body = {
        "error": {"code": code, "message": message},
        "detail": message,  # FastAPI 표준 호환
    }
    if details is not None:
        body["error"]["details"] = details
    cid = correlation_id_var.get()
    if cid:
        body["correlation_id"] = cid
    return JSONResponse(status_code=status_code, content=body)


async def http_exception_handler(request: Request, exc: HTTPException):
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        500: "INTERNAL_ERROR",
        503: "SERVICE_UNAVAILABLE",
    }
    code = code_map.get(exc.status_code, "ERROR")
    return _error_response(exc.status_code, code, str(exc.detail))


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return _error_response(
        422, "VALIDATION_ERROR",
        "요청 데이터가 유효하지 않습니다",
        details=[{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()],
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    import logging
    logging.getLogger("api").exception("unhandled_exception")
    return _error_response(500, "INTERNAL_ERROR", "서버 내부 오류가 발생했어요")
