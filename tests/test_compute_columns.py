"""컬럼 프로젝션 안전망 — compute_columns(부분 지표)가 compute_all(전체)과
요청 컬럼에 대해 **byte 동일**함을 고정한다(결과 불변 = 부작용 없음의 핵심 근거).

근거: 각 add_*는 OHLCV의 순수 함수, 소프트 의존(zscore→log_return_1d,
momentum→pct_change_252d)은 동일 공식 자가복구. 따라서 일부만 계산해도 값 불변.
이 테스트가 깨지면 컬럼 프로젝션을 신뢰할 수 없다(메모리 최적화의 전제 붕괴).

    cd platform && pytest tests/test_compute_columns.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

from quant_core.indicators import (  # noqa: E402
    compute_all, compute_columns, get_all_indicator_columns,
    _COL_TO_PRODUCER_IDX, BASE_INDICATOR_COLS, FUND_INDICATOR_COLS,
)


def _raw(seed: int = 1, n: int = 400) -> pd.DataFrame:
    idx = pd.date_range("2020-01-02", periods=n, freq="B")
    r = np.random.default_rng(seed)
    steps = r.normal(0.05, 1.2, n)
    close = np.maximum(100.0 * np.cumprod(1.0 + steps / 100.0), 1.0)
    open_ = np.concatenate([[close[0]], close[:-1]])
    return pd.DataFrame({
        "Open": open_, "High": np.maximum(open_, close) * 1.01,
        "Low": np.minimum(open_, close) * 0.99, "Close": close,
        "Volume": r.uniform(1e5, 2e6, n),
    }, index=idx)


def _fund(idx: pd.DatetimeIndex, seed: int = 2) -> pd.DataFrame:
    r = np.random.default_rng(seed)
    q = pd.date_range(idx[0], idx[-1], freq="QE")
    cols = ["shares_outstanding", "ttm_fcf", "ttm_ni", "stockholders_equity",
            "ttm_ebitda", "ttm_rev", "total_debt", "cash", "gross_margin",
            "op_margin", "net_debt_ebitda", "roic",
            "z_wc_ta", "z_re_ta", "z_ebit_ta", "z_tl", "z_rev_ta"]
    data = {}
    for c in cols:
        if c in ("shares_outstanding",):
            data[c] = r.uniform(1e7, 1e8, len(q))
        elif c in ("z_tl",):
            data[c] = r.uniform(1e6, 1e8, len(q))
        elif c.startswith("z_"):
            data[c] = r.uniform(0.0, 1.0, len(q))
        elif c in ("gross_margin", "op_margin", "roic", "net_debt_ebitda"):
            data[c] = r.uniform(0.0, 40.0, len(q))
        else:
            data[c] = r.uniform(1e6, 1e9, len(q))
    return pd.DataFrame(data, index=q)


_RAW = _raw()
_FUND = _fund(_RAW.index)
_FULL = compute_all(_RAW, _FUND)
_ALL_COLS = list(_FULL.columns)
# 펀더멘털 중 이 합성 fund_df로 실제 생성되는 것만(가용 컬럼에 따라 조건부 생성)
_FUND_PRODUCED = [c for c in FUND_INDICATOR_COLS if c in _FULL.columns]


def _eq(name: str, a: pd.Series, b: pd.Series) -> None:
    assert a.equals(b), (
        f"컬럼 '{name}' 불일치: compute_columns != compute_all "
        f"(dtype {a.dtype} vs {b.dtype}, "
        f"첫 불일치 idx={next((i for i,(x,y) in enumerate(zip(a,b)) if not (x==y or (pd.isna(x) and pd.isna(y)))), None)})")


# ── 1. 레지스트리가 모든 지표를 커버 (드리프트 방지) ──────────────────────────

def test_registry_covers_all_indicators():
    """get_all_indicator_columns()의 모든 컬럼이 producer 레지스트리 또는
    펀더멘털 집합으로 생성 가능해야 한다. 새 지표 추가 시 등록을 강제."""
    for c in BASE_INDICATOR_COLS:
        assert c in _COL_TO_PRODUCER_IDX, f"BASE 지표 '{c}'가 _PRODUCERS에 미등록"
    for c in FUND_INDICATOR_COLS:
        assert c in get_all_indicator_columns()


# ── 2. 전체 동치 — compute_columns(ALL) == compute_all ───────────────────────

def test_full_equivalence_all_columns():
    proj = compute_columns(_RAW, _ALL_COLS, _FUND)
    for c in _ALL_COLS:
        assert c in proj.columns, f"전체 요청인데 '{c}' 누락"
        _eq(c, proj[c], _FULL[c])


# ── 3. 단일 컬럼 불변 — 각 지표를 하나만 요청해도 값 동일 ─────────────────────

@pytest.mark.parametrize("col", list(BASE_INDICATOR_COLS))
def test_single_column_invariance(col):
    proj = compute_columns(_RAW, {col}, _FUND)
    assert col in proj.columns
    _eq(col, proj[col], _FULL[col])


@pytest.mark.parametrize("col", [c for c in FUND_INDICATOR_COLS])
def test_single_fund_column_invariance(col):
    if col not in _FUND_PRODUCED:
        pytest.skip(f"{col}: 합성 fund_df로 생성 안 됨")
    proj = compute_columns(_RAW, {col}, _FUND)
    assert col in proj.columns, f"펀더멘털 '{col}' 요청했는데 누락"
    _eq(col, proj[col], _FULL[col])


# ── 4. 랜덤 부분집합 — 조합 요청에서도 모든 요청 컬럼 동일 ────────────────────

def test_random_subsets_invariance():
    rng = np.random.default_rng(7)
    pool = list(BASE_INDICATOR_COLS) + _FUND_PRODUCED
    for _ in range(20):
        k = int(rng.integers(1, 6))
        subset = list(rng.choice(pool, size=k, replace=False))
        proj = compute_columns(_RAW, subset, _FUND)
        for c in subset:
            _eq(c, proj[c], _FULL[c])


# ── 5. 하드 의존 — rsi_bear_div 요청 시 rsi_14도 생성되고 둘 다 동일 ──────────

def test_hard_dependency_rsi_bear_div():
    proj = compute_columns(_RAW, {"rsi_bear_div"}, _FUND)
    assert "rsi_14" in proj.columns, "rsi_bear_div의 하드 의존 rsi_14 미생성"
    _eq("rsi_bear_div", proj["rsi_bear_div"], _FULL["rsi_bear_div"])
    _eq("rsi_14", proj["rsi_14"], _FULL["rsi_14"])


# ── 6. 실제 프로젝션이 일어남 — 요청 안 한 컬럼은 안 만들어짐(메모리 절감 근거) ─

def test_projection_actually_limits():
    proj = compute_columns(_RAW, {"momentum_12_1m"}, _FUND)
    assert "momentum_12_1m" in proj.columns
    # 무관한 무거운 지표들은 생성되지 않아야 한다(프로젝션의 핵심).
    for c in ("atr_14_pct", "bb_width", "rsi_14", "zscore_20d", "trailing_pe"):
        assert c not in proj.columns, f"프로젝션 실패: 요청 안 한 '{c}'가 생성됨"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
