"""스크리너 API — 종목 자동 선택.

엔드포인트:
  GET  /screener/presets             — 기본 세트(프리셋) 카탈로그
  POST /screener/preset/{key}/run    — 기본 세트 실행 → 매칭 종목 리스트
  POST /screener/run                 — 사용자 정의 ScreenerSpec 실행
  GET    /screener/my-presets        — 내 세트 목록 (auth)
  POST   /screener/my-presets        — 내 세트 생성 (auth)
  PUT    /screener/my-presets/{id}   — 내 세트 수정 (auth)
  DELETE /screener/my-presets/{id}   — 내 세트 삭제 (auth)

스크리너 실행 입력은 공개 시세성 데이터로만 동작하므로 인증 불필요 (V1).
'내 세트' 저장은 계정 귀속이므로 JWT 인증을 요구한다.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from .. import krx_cache, screener
from ..db import get_session
from ..deps import get_current_user
from ..models import ScreenerUserPreset, User

router = APIRouter(prefix="/screener", tags=["screener"])


def _as_of() -> str | None:
    """현재 스크리너 데이터의 기준일(YYYY-MM-DD). UI가 '5/22(금) 기준' 표기에 사용."""
    return krx_cache.get_status().get("snapshot_date")


@router.get("/presets")
def get_presets():
    """프리셋 카탈로그 + 편집용 spec + 데이터 기준일."""
    return {"presets": screener.list_presets(), "as_of": _as_of()}


@router.get("/fields")
def get_fields():
    """커스터마이징 UI용 필드 카탈로그."""
    return {"fields": screener.field_catalog()}


@router.post("/preset/{key}/run")
def run_preset(key: str):
    """프리셋 실행 → 매칭 종목 리스트."""
    try:
        matches = screener.run_preset(key)
    except screener.ScreenerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"preset": key, "count": len(matches), "matches": matches,
            "as_of": _as_of()}


@router.post("/run")
def run_custom(spec: dict):
    """사용자 정의 ScreenerSpec 실행 → 매칭 종목 + 기준일."""
    try:
        parsed = screener.parse_spec(spec)
        matches = screener.run(parsed)
    except screener.ScreenerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"count": len(matches), "matches": matches, "as_of": _as_of()}


# ── 내 세트 (계정 저장 사용자 정의 프리셋) ─────────────────────────────────────

class MyPresetIn(BaseModel):
    name: str
    spec: dict


def _my_preset_out(row: ScreenerUserPreset) -> dict:
    return {"id": row.id, "name": row.name, "spec": row.spec,
            "created_at": row.created_at, "updated_at": row.updated_at}


def _validate_spec(spec: dict) -> None:
    """parse_spec으로 검증만 — 통과 못 하면 400. label 등 미지원 키는 무시된다."""
    try:
        screener.parse_spec(spec)
    except screener.ScreenerError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _clean_name(name: str) -> str:
    n = (name or "").strip()
    if not n:
        raise HTTPException(status_code=400, detail="세트 이름을 입력하세요.")
    return n[:60]


@router.get("/my-presets")
def list_my_presets(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    rows = session.exec(
        select(ScreenerUserPreset)
        .where(ScreenerUserPreset.user_id == user.id)
        .order_by(ScreenerUserPreset.updated_at.desc())
    ).all()
    return {"presets": [_my_preset_out(r) for r in rows]}


@router.post("/my-presets", status_code=status.HTTP_201_CREATED)
def create_my_preset(
    body: MyPresetIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    name = _clean_name(body.name)
    _validate_spec(body.spec)
    row = ScreenerUserPreset(user_id=user.id, name=name, spec=body.spec)
    session.add(row)
    session.commit()
    session.refresh(row)
    return _my_preset_out(row)


@router.put("/my-presets/{preset_id}")
def update_my_preset(
    preset_id: int,
    body: MyPresetIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    row = session.get(ScreenerUserPreset, preset_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "세트를 찾을 수 없습니다.")
    row.name = _clean_name(body.name)
    _validate_spec(body.spec)
    row.spec = body.spec
    row.updated_at = datetime.now(timezone.utc)
    session.add(row)
    session.commit()
    session.refresh(row)
    return _my_preset_out(row)


@router.delete("/my-presets/{preset_id}")
def delete_my_preset(
    preset_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    row = session.get(ScreenerUserPreset, preset_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "세트를 찾을 수 없습니다.")
    session.delete(row)
    session.commit()
    return {"ok": True}
