"""DB 엔진 및 세션."""

from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy import text

from .config import settings

_connect_args = {"check_same_thread": False} if settings.DB_URL.startswith("sqlite") else {}
engine = create_engine(settings.DB_URL, echo=False, connect_args=_connect_args)


def _migrate() -> None:
    """기존 배포 DB에 대한 멱등 스키마 보정 (Google 로그인 도입).

    create_all은 신규 테이블만 만들고 기존 테이블 컬럼은 바꾸지 않으므로,
    이미 운영 중인 user 테이블에 google_sub 추가 + password_hash nullable 처리.
    새로 만들어진 DB에서는 모두 no-op이다.
    """
    is_pg = settings.DB_URL.startswith("postgresql")
    try:
        with engine.begin() as conn:
            if is_pg:
                conn.execute(text(
                    'ALTER TABLE "user" ALTER COLUMN password_hash DROP NOT NULL'))
                conn.execute(text(
                    'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS google_sub VARCHAR'))
            else:
                cols = [r[1] for r in conn.exec_driver_sql(
                    'PRAGMA table_info("user")').fetchall()]
                if cols and "google_sub" not in cols:
                    conn.exec_driver_sql(
                        'ALTER TABLE "user" ADD COLUMN google_sub VARCHAR')
    except Exception as e:  # noqa: BLE001  — 마이그레이션 실패가 기동을 막지 않도록
        print(f"[migrate] 스키마 보정 건너뜀: {e}")


def create_db_and_tables() -> None:
    from . import models  # noqa: F401  (테이블 등록)
    SQLModel.metadata.create_all(engine)
    _migrate()


def get_session():
    with Session(engine) as session:
        yield session
