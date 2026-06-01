"""지표 등가성 — 벡터화한 add_consecutive_days가 과거 행단위 루프와 byte 동일.

streak은 키스톤 전략이 직접 쓰지 않으므로(test_backtest_golden 미커버) 여기서
루프 구현을 기준값으로 두고 엣지·랜덤 전수 비교해 결과 불변을 고정한다.

    cd platform && pytest tests/test_indicators.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

from quant_core import indicators as ind  # noqa: E402


def _streak_loop(close: list[float]) -> list[int]:
    """과거 행단위 구현(등가성 기준값) — 부호 있는 연속 동일방향 일수."""
    direction = np.sign(pd.Series(close).diff())
    streak: list[int] = []
    count = 0
    for d in direction:
        if d == 0 or np.isnan(d):
            streak.append(count)
            continue
        if count == 0 or np.sign(count) == d:
            count += int(d)
        else:
            count = int(d)
        streak.append(count)
    return streak


def _vectorized(close: list[float]) -> list[int]:
    out = ind.add_consecutive_days(pd.DataFrame({"Close": [float(c) for c in close]}))
    s = out["streak"]
    assert str(s.dtype).startswith("int"), f"streak dtype는 정수여야: {s.dtype}"
    return s.tolist()


EDGE_CASES = [
    [10, 11, 12, 11, 10, 9, 10, 11, 12, 13],   # 일반 상승/하락
    [10, 10, 10, 10],                           # 전부 flat
    [10],                                        # 단일 행(첫날 NaN)
    [10, 11, 11, 12, 12, 12, 11],               # flat이 같은 방향 런 사이
    [10, 11, 10, 11, 10, 11],                   # 매일 부호 교차
    [10, 10, 11, 9, 9, 10],                     # 선두 flat + 부호교차 + flat
    [10, 9, 9, 8, 8, 8, 9, 10, 10, 9],          # 하락 런 + flat 섞임
]


@pytest.mark.parametrize("close", EDGE_CASES)
def test_consecutive_days_matches_loop_edges(close):
    assert _vectorized(close) == _streak_loop(close), f"불일치: {close}"


def test_consecutive_days_matches_loop_random():
    """정수 랜덤워크 — 스텝 {-1,0,+1}로 자연스러운 flat·부호교차 다수 생성."""
    rng = np.random.default_rng(7)
    for _ in range(50):
        close = (100 + np.cumsum(rng.integers(-1, 2, 400))).astype(float).tolist()
        assert _vectorized(close) == _streak_loop(close)


def test_consecutive_days_matches_loop_continuous():
    """연속 가격(완전 flat 거의 없음) — 부호 런렝스 누적 일반 경로."""
    rng = np.random.default_rng(11)
    for _ in range(20):
        close = (100 + np.cumsum(rng.normal(0, 1.0, 500))).tolist()
        assert _vectorized(close) == _streak_loop(close)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
