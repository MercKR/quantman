"""피드 정책 타입 — manifest 단일 출처의 기본 구조.

의존: dataclass + spec.Adjustment 타입뿐(pandas/yfinance 비의존) — 메타 정의 모듈.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..spec import Adjustment


@dataclass(frozen=True)
class FeedPolicy:
    """한 피드(수급 단위)의 manifest 정책 — 출처·실측 조정수준·캘린더.

    adjustment는 **실측** 수준(게이트가 DataSpec 요구와 비교). data_fetcher 수급 동작과 일치시킨다.
    """

    source: str
    adjustment: Adjustment
    calendar: Optional[str] = None
