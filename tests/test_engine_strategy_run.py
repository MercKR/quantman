"""S2 — 팩터/리밸런스 엔진 + 디스패치 회귀.

명세 §7·§3.3. 횡단·포트폴리오·롱숏 전략이 실제 백테스트로 실행되는지,
포지션 4부품(방향·사이징·top_n)이 가중치에 반영되는지 고정한다.

    cd platform && pytest tests/test_engine_strategy_run.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

from quant_core.backtest import run_backtest as legacy_run_backtest  # noqa: E402
from quant_core.blocks import Node, const, data  # noqa: E402
from quant_core.ir_engine import (  # noqa: E402
    Entry, Exit, PositionSpec, Sizing, SimSpec, StrategyIR, Universe,
    run_backtest_ir, run_strategy_ir,
)
from quant_core.ir_engine.run import _weights_row  # noqa: E402


# ── 포지션 4부품 단위 (_weights_row) ──────────────────────────────────────────

def test_weights_long_topn_equal():
    pos = PositionSpec(direction="long", sizing=Sizing(mode="equal_weight"),
                       entry=Entry(mode="scheduled", top_n=2))
    alpha = pd.Series({"A": 3.0, "B": 1.0, "C": 2.0, "D": 0.5})
    w = _weights_row(alpha, pos, None)
    assert set(w[w > 0].index) == {"A", "C"}          # top2 by alpha
    assert np.isclose(w.sum(), 1.0)                    # 롱 풀투자


def test_weights_long_short_dollar_neutral():
    pos = PositionSpec(direction="long_short", entry=Entry(mode="scheduled", top_n=1))
    alpha = pd.Series({"A": 3.0, "B": 1.0, "C": 2.0, "D": 0.5})
    w = _weights_row(alpha, pos, None)
    assert np.isclose(w.sum(), 0.0, atol=1e-9)         # 달러 중립
    assert np.isclose(w.abs().sum(), 1.0)              # 풀투자(절대비중)
    assert w["A"] > 0 and w["D"] < 0                    # 최고 롱·최저 숏


def test_weights_signal_proportional():
    pos = PositionSpec(direction="long", sizing=Sizing(mode="signal_proportional"),
                       entry=Entry(mode="scheduled", top_n=2))
    alpha = pd.Series({"A": 3.0, "B": 1.0})
    w = _weights_row(alpha, pos, None)
    # A:3, B:1 → 0.75 : 0.25
    assert np.isclose(w["A"], 0.75) and np.isclose(w["B"], 0.25)


# ── 통합: 팩터 백테스트 ───────────────────────────────────────────────────────

def _multi_data():
    idx = pd.date_range("2020-01-01", periods=252, freq="B")

    def mk(daily_drift, mom):
        close = 100 * (1 + daily_drift) ** np.arange(252)
        return pd.DataFrame({
            "Open": close, "High": close * 1.001, "Low": close * 0.999,
            "Close": close, "Volume": 1e6,
            "momentum_12_1m": float(mom),
            "ma_dev_20d": np.where(np.arange(252) % 2 == 0, 1.0, -1.0),
        }, index=idx)

    return {"AAA": mk(0.003, 10.0), "BBB": mk(-0.001, -5.0), "CCC": mk(0.0, -3.0)}


def test_factor_long_top1_picks_winner():
    """모멘텀 상위1 롱 → 상승 종목(AAA) 선택 → 벤치마크 초과."""
    s = StrategyIR(
        signal=data("momentum_12_1m"),                 # score 패널
        universe=Universe(kind="all"),
        position=PositionSpec(direction="long", sizing=Sizing(mode="equal_weight"),
                              entry=Entry(mode="scheduled", rebalance="monthly", top_n=1)),
        simulation=SimSpec(initial_capital=1e7),
    )
    res = run_strategy_ir(s, _multi_data())
    assert res["success"], res.get("error")
    m = res["metrics"]
    assert m["total_return"] > m["bench_total"]        # 승자 집중 > 동일가중
    assert "turnover" in m


def test_factor_long_short_profits_from_spread():
    """롱숏 상위1/하위1 → 승자 롱 + 패자 숏 둘 다 이익."""
    s = StrategyIR(
        signal=data("momentum_12_1m"), universe=Universe(kind="all"),
        position=PositionSpec(direction="long_short",
                              entry=Entry(mode="scheduled", rebalance="monthly", top_n=1)),
        simulation=SimSpec(initial_capital=1e7),
    )
    res = run_strategy_ir(s, _multi_data())
    assert res["success"]
    assert res["metrics"]["total_return"] > 0          # 스프레드 수익


def test_factor_condition_scheduled_equal_weight():
    """condition 신호 + 정기리밸런싱 → 참인 종목 동일가중 보유."""
    s = StrategyIR(
        signal=Node(op="compare", params={"op": ">"},
                    inputs={"left": data("ma_dev_20d"), "right": const(0.0)}),
        universe=Universe(kind="all"),
        position=PositionSpec(direction="long", sizing=Sizing(mode="equal_weight"),
                              entry=Entry(mode="scheduled", rebalance="weekly")),
        simulation=SimSpec(initial_capital=1e7),
    )
    res = run_strategy_ir(s, _multi_data())
    assert res["success"]
    assert res["equity"].iloc[-1] > 0


# ── 디스패치: on_signal 단일종목 == run_backtest_ir ───────────────────────────

def test_dispatch_on_signal_single():
    idx = pd.date_range("2020-01-01", periods=200, freq="B")
    r = np.random.default_rng(5)
    close = np.maximum(100 + np.cumsum(r.normal(0.05, 1.2, 200)), 5.0)
    d = {"005930": pd.DataFrame({
        "Open": np.r_[close[0], close[:-1]], "High": close * 1.01,
        "Low": close * 0.99, "Close": close, "Volume": r.uniform(1e5, 1e6, 200),
        "ma_dev_20d": r.uniform(-5, 5, 200),
    }, index=idx)}
    cond = Node(op="compare", params={"op": ">"},
                inputs={"left": data("__SELF__.ma_dev_20d"), "right": const(0.0)})
    s = StrategyIR(signal=cond, universe=Universe(kind="single", symbols=["005930"]),
                   position=PositionSpec(entry=Entry(mode="on_signal"),
                                         exit=Exit(mode="after_n_days", hold_days=10)),
                   simulation=SimSpec(initial_capital=1e7))
    via_ir = run_strategy_ir(s, d)
    direct = run_backtest_ir(d, "005930", cond, hold_days=10, initial_capital=1e7)
    assert via_ir["success"] and direct["success"]
    assert np.isclose(via_ir["metrics"]["total_return"], direct["metrics"]["total_return"])
    assert via_ir["metrics"]["n_trades"] == direct["metrics"]["n_trades"]


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
