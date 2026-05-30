"""운영(admin) 엔드포인트 — 수동 데이터 변경 후 캐시를 강제 동기화.

데이터셋 캐시는 세대 마커로 cron·manage·백필(별도 프로세스) 변경을 자가 감지하지만,
마커 경로를 우회한 변경(예: parquet 파일 직접 삭제·편집)은 감지하지 못한다.
그런 수동 작업 후 즉시 반영하려면 이 엔드포인트로 강제 무효화한다.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from quant_core import data_fetcher

from .. import data_cache
from ..deps import get_current_user
from ..models import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/invalidate")
def invalidate_dataset_cache(user: User = Depends(get_current_user)):
    """데이터셋 캐시 강제 무효화 + 세대 마커 bump.

    수동 데이터 변경(파일 직접 삭제·편집) 후 호출하면 다음 읽기에 parquet에서 재로드한다.
    마커 bump로 다른 프로세스/레플리카의 캐시도 자가 무효화된다."""
    data_cache.invalidate()
    return {"ok": True, "generation": data_fetcher.data_generation()}
