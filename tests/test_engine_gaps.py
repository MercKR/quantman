"""A3·A4·A7·A8·A9 — 구조 갭 보완 회귀.

명세 §3.3·§3.4·§3.2·§4. 짝제약 검증·screener 거부·성과 지표·winsorize·달력.

    cd platform && pytest tests/test_engine_gaps.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

from quant_core.blocks import EvalContext, Node, catalog_spec, data, evaluate  # noqa: E402
from quant_core.ir_engine import (  # noqa: E402
    Entry, Exit, PositionSpec, Sizing, SimSpec, StrategyIR, Universe,
    run_strategy_ir, strategy_from_spec, validate_strategy,
)


def _multi():
    idx = pd.date_range("2020-01-01", periods=200, freq="B")

    def mk(seed):
        r = np.random.default_rng(seed)
        close = np.maximum(100 + np.cumsum(r.normal(0.05, 1.2, 200)), 5.0)
        return pd.DataFrame({
            "Open": close, "High": close * 1.01, "Low": close * 0.99,
            "Close": close, "Volume": 1e6, "momentum_12_1m": r.uniform(-10, 10, 200),
        }, index=idx)
    return {"AAA": mk(1), "BBB": mk(2), "CCC": mk(3)}


# ── A7: 성과 지표 보강 ────────────────────────────────────────────────────────

def test_extra_metrics_present():
    s = StrategyIR(
        signal=data("momentum_12_1m"), universe=Universe(kind="all"),
        position=PositionSpec(entry=Entry(mode="scheduled", rebalance="monthly", top_n=2)),
        simulation=SimSpec(initial_capital=1e7))
    m = run_strategy_ir(s, _multi())["metrics"]
    for k in ["sortino", "calmar", "var_95", "cvar_95", "beta"]:
        assert k in m, f"{k} 누락"


# ── A8: winsorize ─────────────────────────────────────────────────────────────

def test_winsorize_clips_outlier():
    idx = pd.date_range("2021-01-01", periods=3, freq="B")
    d = {s: pd.DataFrame({"x": [v] * 3}, index=idx)
         for s, v in [("A", 1.0), ("B", 2.0), ("C", 3.0), ("D", 1000.0)]}
    out = evaluate(Node(op="winsorize", params={"lower": 10, "upper": 90},
                        inputs={"signal": data("x")}), EvalContext.from_dataset(d))
    assert out.to_numpy().max() < 1000.0     # 이상치 절단
    assert "winsorize" in {b["op"] for b in catalog_spec()}


# ── A9: 달력 라벨 ─────────────────────────────────────────────────────────────

def test_calendar_weekday():
    idx = pd.date_range("2021-01-04", periods=10, freq="B")  # 월요일 시작
    d = {"A": pd.DataFrame({"Close": range(10)}, index=idx)}
    out = evaluate(Node(op="calendar", params={"unit": "weekday"}), EvalContext.from_dataset(d))
    assert set(np.unique(out["A"].dropna())) <= {0, 1, 2, 3, 4}   # 영업일 월~금
    assert "calendar" in {b["op"] for b in catalog_spec()}


# ── A3: 포지션 짝 제약 ────────────────────────────────────────────────────────

def test_fixed_risk_requires_atr():
    s = StrategyIR(
        signal=data("momentum_12_1m"), universe=Universe(kind="all"),
        position=PositionSpec(sizing=Sizing(mode="fixed_risk"),
                              entry=Entry(mode="scheduled")))
    assert any(i.rule == "S-pair" and i.is_error for i in validate_strategy(s))


def test_kelly_warns_not_error():
    s = StrategyIR(
        signal=data("momentum_12_1m"), universe=Universe(kind="all"),
        position=PositionSpec(sizing=Sizing(mode="kelly"), entry=Entry(mode="scheduled")))
    iss = validate_strategy(s)
    assert any(i.rule == "S-pair" and not i.is_error for i in iss)   # 경고지 에러 아님
    assert not any(i.rule == "S-pair" and i.is_error for i in iss)


# ── A4: screener 유니버스 거부 ────────────────────────────────────────────────

def test_screener_universe_rejected():
    s = StrategyIR(
        signal=data("momentum_12_1m"), universe=Universe(kind="screener"),
        position=PositionSpec(entry=Entry(mode="scheduled")))
    assert any(i.rule == "S-univ" and i.is_error for i in validate_strategy(s))


# ── A5: 기간분할 ──────────────────────────────────────────────────────────────

def _factor_spec(**sim):
    return {"signal": {"op": "data", "params": {"ref": "momentum_12_1m"}},
            "universe": {"kind": "all"},
            "position": {"entry": {"mode": "scheduled", "rebalance": "monthly", "top_n": 2}},
            "simulation": {"initial_capital": 1e7, **sim}}


def test_period_split_walk_forward():
    res = strategy_from_spec(_factor_spec(period_split="walk_forward"), _multi())
    assert res["success"] and res["axis"] == "period_split"
    assert len(res["buckets"]) >= 2
    assert "consistency" in res


def test_period_split_oos_two_folds():
    res = strategy_from_spec(_factor_spec(period_split="oos"), _multi())
    assert res["success"]
    assert set(res["buckets"].keys()) == {"인샘플", "아웃샘플"}


def test_period_split_vs_sweep_conflict():
    spec = _factor_spec(period_split="oos")
    spec["sweep"] = {"axis": "parameter", "param_path": "position.entry.top_n",
                     "param_values": [1, 2]}
    res = strategy_from_spec(spec, _multi())
    assert not res["success"]
    assert any(i["rule"] == "S-split" for i in res["issues"])


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
