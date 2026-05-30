"""데이터셋 메모리 캐시.

parquet 로딩 + 지표 계산은 비용이 크므로 프로세스 수명 동안 1회만 수행한다.
데이터는 하루 1회 갱신되므로 프로세스 캐시로 충분하다.
"""

from __future__ import annotations

import threading

import pandas as pd
import quant_core as qc

_lock = threading.Lock()
_dataset: dict[str, pd.DataFrame] | None = None
_manifest = None        # DataManifest — 실측 메타(무결성 게이트 입력). dataset과 수명 동일.
# dataset이 바뀔 때마다 증가. /symbols 등 dataset 파생 응답 캐시의 키로 쓴다.
_version: int = 0


def get_dataset() -> dict[str, pd.DataFrame]:
    global _dataset
    if _dataset is None:
        with _lock:
            if _dataset is None:
                _dataset = qc.load_dataset(with_indicators=True)
    return _dataset


def get_manifest():
    """현재 dataset의 DataManifest(실측 메타). 무결성 게이트가 요구↔실측 비교에 사용."""
    global _manifest
    if _manifest is None:
        with _lock:
            if _manifest is None:
                from .data_manifest import build_dataset_manifest
                _manifest = build_dataset_manifest(get_dataset(), version=_version)
    return _manifest


def get_version() -> int:
    """현재 dataset 버전. invalidate() 호출마다 증가하므로 파생 캐시 무효화에 쓴다."""
    return _version


def invalidate() -> None:
    """캐시된 dataset·매니페스트를 비운다. 다음 호출 시 parquet에서 재로드·재빌드."""
    global _dataset, _manifest, _version
    with _lock:
        _dataset = None
        _manifest = None
        _version += 1
