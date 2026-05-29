"""P1-4 — 펼침층 SWEEP 조건축 회귀.

명세 §8. 결과를 조건 라벨로 사후 분할하는 로직을 고정한다.

    cd platform && pytest tests/test_engine_sweep.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

from quant_core.blocks import Node, const, data  # noqa: E402
from quant_core.ir_engine import (  # noqa: E402
    partition_by_label, run_condition_sweep, summarize_returns, sweep_condition,
)


# ── 코어 함수 ─────────────────────────────────────────────────────────────────

def test_summarize_returns():
    r = pd.Series([0.01, -0.02, 0.03])
    s = summarize_returns(r)
    assert s["n"] == 3
    assert np.isclose(s["win_rate"], 2 / 3 * 100)
    assert np.isclose(s["mean"], np.mean([0.01, -0.02, 0.03]) * 100)


def test_summarize_empty():
    s = summarize_returns(pd.Series([], dtype=float))
    assert s["n"] == 0 and np.isnan(s["mean"])


def test_partition_by_label_drops_nan_label():
    idx = pd.date_range("2021-01-01", periods=5, freq="B")
    returns = pd.Series([0.01, 0.02, -0.01, 0.03, -0.02], index=idx)
    labels = pd.Series([0, 1, 0, 1, np.nan], index=idx)
    parts = partition_by_label(returns, labels)
    assert set(parts.keys()) == {0, 1}
    assert list(parts[0].index) == [idx[0], idx[2]]
    assert list(parts[1].index) == [idx[1], idx[3]]  # nan 라벨(idx[4]) 제외


def test_partition_counts_sum():
    idx = pd.date_range("2021-01-01", periods=20, freq="B")
    rng = np.random.default_rng(3)
    returns = pd.Series(rng.normal(0, 0.01, 20), index=idx)
    labels = pd.Series(rng.integers(0, 3, 20), index=idx)
    parts = partition_by_label(returns, labels)
    assert sum(len(s) for s in parts.values()) == 20


def test_sweep_condition_separates_regimes():
    """국면별 수익률 차이를 분할이 포착하는지 — 라벨 0은 음수, 1은 양수로 구성."""
    idx = pd.date_range("2021-01-01", periods=10, freq="B")
    # equity 구성: 라벨에 따라 다른 일별 수익률
    labels = pd.Series([0, 0, 0, 0, 0, 1, 1, 1, 1, 1], index=idx, dtype=float)
    rets = pd.Series([-0.01] * 5 + [0.02] * 5, index=idx)
    equity = pd.Series((1 + rets).cumprod() * 1e7, index=idx)
    # equity의 일별수익률은 첫날 제외 → 라벨도 그에 맞춰 정렬됨
    res = sweep_condition(equity, labels)
    assert set(res.keys()) == {0.0, 1.0}
    assert res[0.0]["mean"] < 0 < res[1.0]["mean"]


# ── end-to-end: 전략 + 국면 라벨 ──────────────────────────────────────────────

def _dataset():
    idx = pd.date_range("2020-01-01", periods=250, freq="B")
    r = np.random.default_rng(5)
    close = 100 + np.cumsum(r.normal(0.05, 1.2, 250))
    close = np.maximum(close, 5.0)
    aaa = pd.DataFrame({
        "Open": np.concatenate([[close[0]], close[:-1]]),
        "High": close * 1.01, "Low": close * 0.99, "Close": close,
        "Volume": r.uniform(1e5, 1e6, 250),
        "ma_dev_20d": r.uniform(-5, 5, 250),
    }, index=idx)
    vix = pd.DataFrame({"Close": r.uniform(10, 40, 250)}, index=idx)
    return {"AAA": aaa, "VIX": vix}


def test_run_condition_sweep_end_to_end():
    d = _dataset()
    buy = Node(op="compare", params={"op": ">"},
               inputs={"left": data("__SELF__.ma_dev_20d"), "right": const(0.0)})
    # VIX 국면: <20 저변동성(0), [20,30) 중(1), >=30 고(2)
    regime = Node(op="bucket", params={"edges": [20.0, 30.0]},
                  inputs={"signal": data("VIX.Close")})
    res = run_condition_sweep(d, "AAA", buy, regime, hold_days=10)
    assert res["success"]
    assert res["overall"]["n"] > 0
    # 버킷 카운트 합 == overall 카운트 (라벨 NaN 없음 — VIX 전기간 존재)
    bucket_total = sum(b["n"] for b in res["buckets"].values())
    assert bucket_total == res["overall"]["n"]
    # 적어도 2개 국면이 잡힘
    assert len(res["buckets"]) >= 2


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
