# app/utils/security.py
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import get_session
from app.models.database import User

# 비밀번호 해싱 (Argon2로 교체: 길이 제한 없고 더 안전)
# schemes: argon2 우선, bcrypt fallback (기존 사용자 호환)
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

# HTTP Bearer 토큰 스킴
security = HTTPBearer()


def hash_password(password: str) -> str:
    """
    비밀번호 해싱
    Argon2 사용: 입력 길이 제한 없음 (보안상 validator에서 char 제한 추천)
    """
    return pwd_context.hash(password)


# ⭐ 별칭 함수 추가 (하위 호환성)
def get_password_hash(password: str) -> str:
    """
    비밀번호 해싱 (hash_password의 별칭)
    하위 호환성을 위해 추가
    """
    return hash_password(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    JWT 액세스 토큰 생성

    Args:
        data: 토큰에 포함할 데이터 (보통 {"sub": username})
        expires_delta: 만료 시간 (기본값: 24시간)

    Returns:
        JWT 토큰 문자열
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.utcnow(),  # 발급 시간
            "type": "access",
        }
    )

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    JWT 토큰 디코딩 및 검증

    Args:
        token: JWT 토큰 문자열

    Returns:
        디코딩된 페이로드

    Raises:
        HTTPException: 토큰이 유효하지 않을 경우
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 만료되었습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
) -> User:
    """
    현재 로그인한 사용자 조회 (의존성)

    사용법:
        @router.get("/protected")
        def protected_route(current_user: User = Depends(get_current_user)):
            return {"user": current_user.username}
    """
    token = credentials.credentials

    # 토큰 디코딩
    payload = decode_access_token(token)

    # username 추출
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 인증 정보입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 사용자 조회
    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 비활성화된 사용자 체크
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="비활성화된 계정입니다.")

    return user


def create_refresh_token(data: dict) -> str:
    """
    리프레시 토큰 생성 (선택사항)
    액세스 토큰보다 긴 유효기간을 가짐
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)  # 7일

    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "refresh"})

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
