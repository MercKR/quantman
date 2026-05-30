"""P1-1 — 신규 고급 블록 수학적 속성 검증.

명세 §3. 기존 엔진에 없던 연산이라 동치 대신 수학적 속성으로 정확성을 고정한다.

    cd platform && pytest tests/test_blocks_advanced.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

import pytest  # noqa: E402

from quant_core.blocks import EvalContext, Node, data, evaluate  # noqa: E402


def _ctx(data_dict):
    return EvalContext.from_dataset(data_dict)


@pytest.fixture
def _kr_groups(monkeypatch):
    """그룹 테스트용 — get_symbol_group이 읽는 classification 사이드카를 고정 매핑으로 대체.

    실제 KRX 업종은 수시로 바뀌어 테스트에 박으면 안 되므로, 그룹 *로직*(그룹 내 순위·집계)만
    검증하도록 작은 fixture를 주입한다.
    """
    groups = {"005930": {"Industry": "IT"}, "000660": {"Industry": "IT"},
              "005380": {"Industry": "Auto"}, "000270": {"Industry": "Auto"}}
    import quant_core.data.feeds.classification as cls
    monkeypatch.setattr(cls, "load", lambda: groups)


def _two_corr_data(rho_sign=1):
    idx = pd.date_range("2021-01-01", periods=120, freq="B")
    r = np.random.default_rng(7)
    base = r.normal(0, 1, 120).cumsum()
    a = pd.DataFrame({"AAA": base}, index=idx)
    b = pd.DataFrame({"AAA": rho_sign * base}, index=idx)  # 동일/반대 방향
    return {"AAA": pd.DataFrame({"x": a["AAA"], "y": b["AAA"]}, index=idx)}


# ── ts_corr ───────────────────────────────────────────────────────────────────

def test_ts_corr_identical_is_one():
    idx = pd.date_range("2021-01-01", periods=80, freq="B")
    s = np.random.default_rng(1).normal(0, 1, 80).cumsum()
    d = {"AAA": pd.DataFrame({"x": s, "y": s}, index=idx)}
    node = Node(op="ts_corr", params={"window": 20},
                inputs={"a": data("x"), "b": data("y")})
    out = evaluate(node, _ctx(d))
    assert np.isclose(out["AAA"].dropna().iloc[-1], 1.0, atol=1e-6)


def test_ts_corr_opposite_is_minus_one():
    idx = pd.date_range("2021-01-01", periods=80, freq="B")
    s = np.random.default_rng(2).normal(0, 1, 80).cumsum()
    d = {"AAA": pd.DataFrame({"x": s, "y": -s}, index=idx)}
    node = Node(op="ts_corr", params={"window": 20},
                inputs={"a": data("x"), "b": data("y")})
    out = evaluate(node, _ctx(d))
    assert np.isclose(out["AAA"].dropna().iloc[-1], -1.0, atol=1e-6)


# ── ts_regression ─────────────────────────────────────────────────────────────

def test_ts_regression_beta_recovers_slope():
    idx = pd.date_range("2021-01-01", periods=100, freq="B")
    x = np.random.default_rng(3).normal(0, 1, 100)
    y = 2.5 * x  # 정확히 기울기 2.5
    d = {"AAA": pd.DataFrame({"x": x, "y": y}, index=idx)}
    node = Node(op="ts_regression", params={"window": 30, "output": "beta"},
                inputs={"y": data("y"), "x": data("x")})
    out = evaluate(node, _ctx(d))
    assert np.isclose(out["AAA"].dropna().iloc[-1], 2.5, atol=1e-6)


def test_ts_regression_residual_zero_when_perfect():
    idx = pd.date_range("2021-01-01", periods=100, freq="B")
    x = np.random.default_rng(4).normal(0, 1, 100)
    y = 1.3 * x + 0.5
    d = {"AAA": pd.DataFrame({"x": x, "y": y}, index=idx)}
    node = Node(op="ts_regression", params={"window": 30, "output": "residual"},
                inputs={"y": data("y"), "x": data("x")})
    out = evaluate(node, _ctx(d))
    assert np.allclose(out["AAA"].dropna().iloc[-5:], 0.0, atol=1e-6)


# ── orthogonalize ─────────────────────────────────────────────────────────────

def test_orthogonalize_residual_uncorrelated():
    """직교화 잔차는 b와 횡단 무상관(≈0 상관)."""
    idx = pd.date_range("2021-01-01", periods=5, freq="B")
    syms = [f"S{i}" for i in range(10)]
    r = np.random.default_rng(5)
    d = {}
    for s in syms:
        bv = r.normal(0, 1, 5)
        d[s] = pd.DataFrame({"b": bv, "a": 3 * bv + r.normal(0, 0.1, 5)}, index=idx)
    node = Node(op="orthogonalize", inputs={"a": data("a"), "b": data("b")})
    out = evaluate(node, _ctx(d))
    # 마지막 날짜의 잔차와 b의 횡단 상관 ≈ 0
    t = idx[-1]
    resid = out.loc[t].to_numpy(dtype=float)
    bvals = np.array([d[s].loc[t, "b"] for s in syms])
    corr = np.corrcoef(resid, bvals)[0, 1]
    assert abs(corr) < 1e-6


# ── group_rank / group_aggregate ──────────────────────────────────────────────

def _group_data():
    # 005930/000660 → IT, 005380/000270 → Auto (_kr_groups fixture)
    idx = pd.date_range("2021-01-01", periods=10, freq="B")
    r = np.random.default_rng(6)
    return {s: pd.DataFrame({"momentum_12_1m": r.uniform(-10, 10, 10)}, index=idx)
            for s in ["005930", "000660", "005380", "000270"]}


def test_group_rank_within_group(_kr_groups):
    d = _group_data()
    node = Node(op="group_rank", inputs={"signal": data("momentum_12_1m")})
    out = evaluate(node, _ctx(d))
    # IT 그룹(2종목) 순위는 {0.5, 1.0} 형태 (pct rank, 2개)
    t = out.index[-1]
    it_ranks = sorted([out.loc[t, "005930"], out.loc[t, "000660"]])
    assert it_ranks == [0.5, 1.0]


def test_group_aggregate_mean(_kr_groups):
    d = _group_data()
    node = Node(op="group_aggregate", params={"stat": "mean"},
                inputs={"signal": data("momentum_12_1m")})
    out = evaluate(node, _ctx(d))
    t = out.index[-1]
    expected_it = (d["005930"].loc[t, "momentum_12_1m"] + d["000660"].loc[t, "momentum_12_1m"]) / 2
    assert np.isclose(out.loc[t, "005930"], expected_it)
    assert np.isclose(out.loc[t, "000660"], expected_it)


# ── cs_dispersion ─────────────────────────────────────────────────────────────

def test_cs_dispersion_zero_when_equal():
    idx = pd.date_range("2021-01-01", periods=5, freq="B")
    d = {s: pd.DataFrame({"v": [1.0] * 5}, index=idx) for s in ["A", "B", "C"]}
    node = Node(op="cs_dispersion", inputs={"signal": data("v")})
    out = evaluate(node, _ctx(d))
    assert np.allclose(out.to_numpy(), 0.0)


# ── bucket ────────────────────────────────────────────────────────────────────

def test_bucket_labels():
    idx = pd.date_range("2021-01-01", periods=4, freq="B")
    d = {"A": pd.DataFrame({"v": [0.5, 1.5, 2.5, 3.5]}, index=idx)}
    node = Node(op="bucket", params={"edges": [1.0, 2.0, 3.0]},
                inputs={"signal": data("v")})
    out = evaluate(node, _ctx(d))
    # digitize: <1→0, [1,2)→1, [2,3)→2, >=3→3
    assert list(out["A"].to_numpy()) == [0.0, 1.0, 2.0, 3.0]


# ── ts_autocorr / ts_halflife ─────────────────────────────────────────────────

def test_ts_autocorr_random_walk_high():
    idx = pd.date_range("2021-01-01", periods=120, freq="B")
    rw = np.random.default_rng(8).normal(0, 1, 120).cumsum()
    d = {"A": pd.DataFrame({"v": rw}, index=idx)}
    node = Node(op="ts_autocorr", params={"window": 30, "lag": 1},
                inputs={"signal": data("v")})
    out = evaluate(node, _ctx(d))
    assert out["A"].dropna().iloc[-1] > 0.8  # 랜덤워크 레벨은 lag1 자기상관 높음


def test_ts_halflife_mean_reverting_finite():
    """평균회귀(AR1 phi<1) 시계열 → 반감기 양수·유한."""
    idx = pd.date_range("2021-01-01", periods=200, freq="B")
    r = np.random.default_rng(9)
    v = np.zeros(200)
    for i in range(1, 200):
        v[i] = 0.9 * v[i - 1] + r.normal(0, 1)  # phi=0.9 → 반감기 ≈ 6.6
    d = {"A": pd.DataFrame({"v": v}, index=idx)}
    node = Node(op="ts_halflife", params={"window": 80},
                inputs={"signal": data("v")})
    out = evaluate(node, _ctx(d)).dropna()
    last = out["A"].iloc[-1]
    assert 1.0 < last < 30.0  # phi≈0.9 근방의 반감기 범위


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
