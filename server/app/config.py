"""서버 설정. 환경변수로 덮어쓸 수 있다."""

import os
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent

_DEFAULT_SECRET = "dev-insecure-secret-change-me"


class Settings:
    # 실행 환경 — production 배포 시 QP_ENV=production 설정 (fail-fast 검증 활성).
    ENV: str = os.getenv("QP_ENV", "development")

    # 인증
    SECRET_KEY: str = os.getenv("QP_SECRET_KEY", _DEFAULT_SECRET)
    JWT_ALGO: str = "HS256"

    # /health/*/refresh 무인증 보호용 토큰 — production에서만 검증.
    # 미설정 시 production 부팅 차단(fail-fast).
    HEALTH_TOKEN: str = os.getenv("QP_HEALTH_TOKEN", "")
    ACCESS_TOKEN_HOURS: int = int(os.getenv("QP_ACCESS_TOKEN_HOURS", "168"))  # 7일

    # Google 소셜 로그인 — ID 토큰 검증 시 audience(aud) 확인용. 미설정 시 비활성.
    GOOGLE_CLIENT_ID: str = os.getenv("QP_GOOGLE_CLIENT_ID", "")

    # DB
    DB_URL: str = os.getenv("QP_DB_URL", f"sqlite:///{_BASE / 'data.db'}")

    # 기기 페어링
    PAIRING_TTL_MIN: int = 10            # 페어링 코드 유효시간(분)
    WEB_URL: str = os.getenv("QP_WEB_URL", "http://localhost:5173")

    # CORS 허용 오리진 (웹 SPA 개발 서버)
    CORS_ORIGINS: list[str] = os.getenv(
        "QP_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")


settings = Settings()


# 프로덕션에서 기본(개발용) 시크릿을 그대로 쓰면 JWT 위조가 가능하다.
# QP_ENV=production인데 SECRET_KEY가 기본값이면 부팅을 막는다 (fail-fast).
if settings.ENV == "production" and settings.SECRET_KEY == _DEFAULT_SECRET:
    raise RuntimeError(
        "QP_SECRET_KEY가 설정되지 않았습니다 (기본 개발용 시크릿 사용 중). "
        "프로덕션 배포 시 QP_SECRET_KEY 환경변수를 반드시 설정하세요.")

# /health/*/refresh는 부작용이 작지만(공개데이터 재다운로드) 무인증이면 누구나
# 호출해 상류 API rate limit·비용을 소모시킬 수 있다. production에선 토큰 강제.
if settings.ENV == "production" and not settings.HEALTH_TOKEN:
    raise RuntimeError(
        "QP_HEALTH_TOKEN이 설정되지 않았습니다. "
        "프로덕션 배포 시 /health/*/refresh 보호 토큰을 반드시 설정하세요.")
