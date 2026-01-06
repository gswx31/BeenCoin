# app/schemas/user_secure.py
"""
🔐 보안 강화된 사용자 스키마

개선 사항:
1. 비밀번호 복잡도 검증 강화
2. 사용자명 Sanitization
3. 추가 보안 필드
"""
import re
from datetime import datetime
from html import escape
from typing import Optional

from pydantic import BaseModel, Field, field_validator

# =============================================================================
# 비밀번호 강도 설정
# =============================================================================

class PasswordPolicy:
    """비밀번호 정책 설정"""

    MIN_LENGTH = 8
    MAX_LENGTH = 128  # Argon2는 길이 제한 없음

    # 최소 요구사항
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True

    # 특수문자 허용 목록
    SPECIAL_CHARS = r"!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\;'~`"

    # 일반적인 취약 비밀번호 목록 (확장 가능)
    WEAK_PASSWORDS = {
        "password", "password1", "password123",
        "123456", "12345678", "123456789",
        "qwerty", "qwerty123", "qwertyuiop",
        "abc123", "abcd1234",
        "letmein", "welcome", "admin",
        "passw0rd", "p@ssword", "p@ssw0rd",
    }

# =============================================================================
# 사용자 스키마
# =============================================================================

class UserBase(BaseModel):
    """사용자 기본 스키마"""
    username: str = Field(
        ...,
        min_length=3,
        max_length=20,
        description="사용자명 (영문자와 숫자만, 3-20자)"
    )

class UserCreate(UserBase):
    """
    회원가입 스키마

    보안 강화:
    - 사용자명: 영문+숫자만, XSS 방지
    - 비밀번호: 복잡도 검증
    """
    password: str = Field(
        ...,
        min_length=PasswordPolicy.MIN_LENGTH,
        max_length=PasswordPolicy.MAX_LENGTH,
        description="비밀번호 (8자 이상, 대소문자/숫자/특수문자 포함)"
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """
        사용자명 검증

        규칙:
        - 영문자와 숫자만 허용
        - 3-20자
        - XSS 방지를 위한 이스케이프
        """
        if not v:
            raise ValueError("사용자명은 필수입니다.")

        # 공백 제거
        v = v.strip()

        # 길이 확인
        if len(v) < 3:
            raise ValueError("사용자명은 3자 이상이어야 합니다.")
        if len(v) > 20:
            raise ValueError("사용자명은 20자 이하여야 합니다.")

        # 영문+숫자만 허용
        if not v.isalnum():
            raise ValueError(
                "사용자명은 영문자와 숫자만 사용 가능합니다. "
                "특수문자, 공백, 언더스코어(_)는 사용할 수 없습니다."
            )

        # 숫자로만 구성된 사용자명 금지
        if v.isdigit():
            raise ValueError("사용자명은 숫자로만 구성될 수 없습니다.")

        # 예약어 확인
        reserved = {"admin", "root", "system", "api", "null", "undefined"}
        if v.lower() in reserved:
            raise ValueError(f"'{v}'는 사용할 수 없는 사용자명입니다.")

        # XSS 방지 (HTML 이스케이프)
        return escape(v)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        비밀번호 강도 검증

        규칙:
        - 최소 8자, 최대 128자
        - 대문자 1개 이상
        - 소문자 1개 이상
        - 숫자 1개 이상
        - 특수문자 1개 이상
        - 일반적인 취약 비밀번호 금지
        """
        if not v:
            raise ValueError("비밀번호는 필수입니다.")

        # 길이 확인
        if len(v) < PasswordPolicy.MIN_LENGTH:
            raise ValueError(
                f"비밀번호는 {PasswordPolicy.MIN_LENGTH}자 이상이어야 합니다."
            )
        if len(v) > PasswordPolicy.MAX_LENGTH:
            raise ValueError(
                f"비밀번호는 {PasswordPolicy.MAX_LENGTH}자 이하여야 합니다."
            )

        # 공백 확인
        if " " in v:
            raise ValueError("비밀번호에 공백을 포함할 수 없습니다.")

        # 복잡도 검증
        errors = []

        if PasswordPolicy.REQUIRE_UPPERCASE and not re.search(r"[A-Z]", v):
            errors.append("대문자 1개 이상")

        if PasswordPolicy.REQUIRE_LOWERCASE and not re.search(r"[a-z]", v):
            errors.append("소문자 1개 이상")

        if PasswordPolicy.REQUIRE_DIGIT and not re.search(r"\d", v):
            errors.append("숫자 1개 이상")

        if PasswordPolicy.REQUIRE_SPECIAL:
            special_pattern = f"[{re.escape(PasswordPolicy.SPECIAL_CHARS)}]"
            if not re.search(special_pattern, v):
                errors.append("특수문자 1개 이상 (!@#$%^&* 등)")

        if errors:
            raise ValueError(
                f"비밀번호에 다음이 포함되어야 합니다: {', '.join(errors)}"
            )

        # 취약 비밀번호 확인
        if v.lower() in PasswordPolicy.WEAK_PASSWORDS:
            raise ValueError(
                "너무 일반적인 비밀번호입니다. 더 복잡한 비밀번호를 사용해주세요."
            )

        # 연속된 문자/숫자 확인 (예: abc, 123)
        if _has_sequential_chars(v, 4):
            raise ValueError(
                "비밀번호에 4자 이상의 연속된 문자나 숫자를 포함할 수 없습니다. "
                "(예: abcd, 1234)"
            )

        # 반복된 문자 확인 (예: aaaa)
        if _has_repeated_chars(v, 3):
            raise ValueError(
                "비밀번호에 3자 이상의 반복된 문자를 포함할 수 없습니다. "
                "(예: aaa, 111)"
            )

        return v

class UserLogin(UserBase):
    """로그인 스키마"""
    password: str = Field(..., description="비밀번호")

class UserOut(UserBase):
    """사용자 응답 스키마"""
    id: str = Field(..., description="사용자 UUID")
    created_at: str = Field(..., description="가입일시")

    class Config:
        from_attributes = True

class UserProfile(UserOut):
    """사용자 프로필 (확장)"""
    is_active: bool = Field(default=True, description="계정 활성화 상태")
    last_login: Optional[datetime] = Field(None, description="마지막 로그인")

    class Config:
        from_attributes = True

# =============================================================================
# 비밀번호 변경 스키마
# =============================================================================

class PasswordChange(BaseModel):
    """비밀번호 변경 스키마"""

    current_password: str = Field(..., description="현재 비밀번호")
    new_password: str = Field(
        ...,
        min_length=PasswordPolicy.MIN_LENGTH,
        max_length=PasswordPolicy.MAX_LENGTH,
        description="새 비밀번호"
    )
    confirm_password: str = Field(..., description="새 비밀번호 확인")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """새 비밀번호 검증 (UserCreate와 동일한 규칙)"""
        # UserCreate의 validate_password 로직 재사용
        return UserCreate.validate_password(v)

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        """비밀번호 일치 확인"""
        # Pydantic v2에서는 info.data로 다른 필드 접근
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("새 비밀번호가 일치하지 않습니다.")
        return v

# =============================================================================
# 헬퍼 함수
# =============================================================================

def _has_sequential_chars(s: str, min_length: int = 4) -> bool:
    """
    연속된 문자/숫자 확인

    예: abc, 123, cba (역순도 포함)
    """
    if len(s) < min_length:
        return False

    s_lower = s.lower()

    for i in range(len(s_lower) - min_length + 1):
        substring = s_lower[i:i + min_length]

        # 연속 증가 확인
        is_sequential = True
        for j in range(len(substring) - 1):
            if ord(substring[j + 1]) - ord(substring[j]) != 1:
                is_sequential = False
                break

        if is_sequential:
            return True

        # 연속 감소 확인
        is_reverse = True
        for j in range(len(substring) - 1):
            if ord(substring[j]) - ord(substring[j + 1]) != 1:
                is_reverse = False
                break

        if is_reverse:
            return True

    return False

def _has_repeated_chars(s: str, min_length: int = 3) -> bool:
    """
    반복된 문자 확인

    예: aaa, 111
    """
    if len(s) < min_length:
        return False

    s_lower = s.lower()

    for i in range(len(s_lower) - min_length + 1):
        substring = s_lower[i:i + min_length]
        if len(set(substring)) == 1:
            return True

    return False

# =============================================================================
# 비밀번호 강도 측정
# =============================================================================

def get_password_strength(password: str) -> dict:
    """
    비밀번호 강도 측정

    Returns:
        {
            "score": 0-100,
            "level": "weak" | "medium" | "strong" | "very_strong",
            "suggestions": [...]
        }
    """
    score = 0
    suggestions = []

    # 길이 점수 (최대 30점)
    length = len(password)
    if length >= 8:
        score += 10
    if length >= 12:
        score += 10
    if length >= 16:
        score += 10
    else:
        suggestions.append("16자 이상 사용을 권장합니다.")

    # 문자 종류 점수 (최대 40점)
    if re.search(r"[a-z]", password):
        score += 10
    else:
        suggestions.append("소문자를 포함하세요.")

    if re.search(r"[A-Z]", password):
        score += 10
    else:
        suggestions.append("대문자를 포함하세요.")

    if re.search(r"\d", password):
        score += 10
    else:
        suggestions.append("숫자를 포함하세요.")

    if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        score += 10
    else:
        suggestions.append("특수문자를 포함하세요.")

    # 다양성 점수 (최대 30점)
    unique_chars = len(set(password))
    if unique_chars >= 8:
        score += 15
    if unique_chars >= 12:
        score += 15
    else:
        suggestions.append("더 다양한 문자를 사용하세요.")

    # 패턴 감점
    if _has_sequential_chars(password, 3):
        score -= 10
        suggestions.append("연속된 문자를 피하세요.")

    if _has_repeated_chars(password, 3):
        score -= 10
        suggestions.append("반복된 문자를 피하세요.")

    if password.lower() in PasswordPolicy.WEAK_PASSWORDS:
        score = 0
        suggestions = ["이 비밀번호는 너무 일반적입니다. 완전히 다른 비밀번호를 사용하세요."]

    # 점수 보정
    score = max(0, min(100, score))

    # 레벨 결정
    if score < 30:
        level = "weak"
    elif score < 60:
        level = "medium"
    elif score < 80:
        level = "strong"
    else:
        level = "very_strong"

    return {
        "score": score,
        "level": level,
        "suggestions": suggestions
    }
