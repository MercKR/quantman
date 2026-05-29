"""P1-5 — 비교·검증층 회귀.

명세 §9. 2표본 검정·부트스트랩·워크포워드·분포·초과수익을 고정한다.

    cd platform && pytest tests/test_engine_compare.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

from quant_core.ir_engine import (  # noqa: E402
    bootstrap_mean_ci, compare_partition, distribution, excess_distribution,
    two_sample_test, walk_forward_consistency,
)


# ── 2표본 검정 ────────────────────────────────────────────────────────────────

def test_two_sample_clearly_different():
    r = np.random.default_rng(1)
    a = pd.Series(r.normal(0.05, 0.01, 300))
    b = pd.Series(r.normal(-0.05, 0.01, 300))
    res = two_sample_test(a, b)
    assert res["p_value"] < 1e-6
    assert res["mean_diff"] > 0


def test_two_sample_identical_is_p1():
    a = pd.Series([0.01, -0.02, 0.03, 0.0, 0.015])
    res = two_sample_test(a, a)
    assert np.isclose(res["t_stat"], 0.0)
    assert np.isclose(res["p_value"], 1.0)


def test_two_sample_insufficient():
    res = two_sample_test(pd.Series([0.01]), pd.Series([0.02, 0.03]))
    assert np.isnan(res["p_value"])


# ── 부트스트랩 ────────────────────────────────────────────────────────────────

def test_bootstrap_ci_brackets_mean():
    r = pd.Series(np.random.default_rng(2).normal(0.01, 0.01, 500))
    res = bootstrap_mean_ci(r, n_boot=1000, seed=42)
    assert res["ci_low"] < res["mean"] < res["ci_high"]


def test_bootstrap_deterministic_with_seed():
    r = pd.Series(np.random.default_rng(3).normal(0.0, 0.02, 200))
    a = bootstrap_mean_ci(r, n_boot=500, seed=7)
    b = bootstrap_mean_ci(r, n_boot=500, seed=7)
    assert a == b


# ── 워크포워드 ────────────────────────────────────────────────────────────────

def test_walk_forward_all_positive():
    r = pd.Series(np.abs(np.random.default_rng(4).normal(0.01, 0.005, 100)) + 1e-4)
    res = walk_forward_consistency(r, n_folds=4)
    assert res["n_folds"] == 4
    assert res["consistency"] == 1.0


def test_walk_forward_mixed():
    r = pd.Series([0.02] * 25 + [-0.02] * 25 + [0.02] * 25 + [-0.02] * 25)
    res = walk_forward_consistency(r, n_folds=4)
    assert res["positive_folds"] == 2  # 양/음 교대


# ── 분포 ──────────────────────────────────────────────────────────────────────

def test_distribution_quantiles():
    r = pd.Series(np.linspace(-0.1, 0.1, 101))  # 대칭
    d = distribution(r, bins=5)
    assert d["n"] == 101
    assert np.isclose(d["quantiles"]["q50"], 0.0, atol=1e-6)
    assert sum(d["hist_counts"]) == 101


# ── compare_partition ─────────────────────────────────────────────────────────

def test_compare_partition():
    r = np.random.default_rng(6)
    parts = {0: pd.Series(r.normal(0.03, 0.01, 100)),
             1: pd.Series(r.normal(-0.03, 0.01, 100))}
    res = compare_partition(parts)
    assert set(res["by_label"].keys()) == {0, 1}
    assert "0_vs_1" in res["pairwise"]
    assert res["pairwise"]["0_vs_1"]["p_value"] < 1e-6


# ── 초과수익 ──────────────────────────────────────────────────────────────────

def test_excess_distribution_positive_when_outperform():
    idx = pd.date_range("2021-01-01", periods=50, freq="B")
    strat = pd.Series((1 + np.full(49, 0.01)).cumprod(), index=idx[1:])
    strat = pd.concat([pd.Series([1.0], index=[idx[0]]), strat]) * 1e7
    bench = pd.Series((1 + np.full(49, 0.002)).cumprod(), index=idx[1:])
    bench = pd.concat([pd.Series([1.0], index=[idx[0]]), bench]) * 1e7
    res = excess_distribution(strat, bench)
    assert res["car"] > 0
    assert res["mean_excess"] > 0


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
