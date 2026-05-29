"""S3 — 이벤트 드리븐 다종목 포트폴리오 (on_signal + 리스트) 동치 검증.

명세 §7. 검증된 레거시 _run_portfolio_backtest와 metric 비트 동일함을 고정한다.
(레거시는 golden 검증을 통과하므로 전이적으로 신뢰)

    cd platform && pytest tests/test_engine_portfolio_ir.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

from quant_core.backtest import run_backtest as legacy_run_backtest  # noqa: E402
from quant_core.blocks import Node, const, data  # noqa: E402
from quant_core.ir_engine import (  # noqa: E402
    Entry, Exit, PositionSpec, SimSpec, StrategyIR, Universe, run_strategy_ir,
)

SYMS = ["AAA", "BBB", "CCC"]


def _multi():
    idx = pd.date_range("2020-01-01", periods=300, freq="B")

    def mk(seed, drift):
        r = np.random.default_rng(seed)
        close = np.maximum(100 + np.cumsum(r.normal(drift, 1.3, 300)), 5.0)
        high = close * (1 + np.abs(r.normal(0, 0.008, 300)))
        low = close * (1 - np.abs(r.normal(0, 0.008, 300)))
        atr = pd.Series(high - low).rolling(14).mean().bfill().to_numpy()
        return pd.DataFrame({
            "Open": np.r_[close[0], close[:-1]], "High": high, "Low": low,
            "Close": close, "Volume": r.uniform(1e5, 1e6, 300),
            "ma_dev_20d": r.uniform(-5, 5, 300), "atr_14": atr,
        }, index=idx)
    return {"AAA": mk(1, 0.05), "BBB": mk(2, 0.0), "CCC": mk(3, -0.03)}


def _legacy_cond(indicator, op, value):
    return {"left": {"kind": "indicator", "symbol": "__SELF__", "indicator": indicator},
            "op": op, "right": {"kind": "constant", "value": value}}


def _node(indicator, op, value):
    return Node(op="compare", params={"op": op},
                inputs={"left": data(f"__SELF__.{indicator}"), "right": const(value)})


def _eq(a, b):
    keys = ["total_return", "cagr", "mdd", "sharpe", "n_trades", "win_rate",
            "avg_hold", "avg_trade_return", "bench_total", "excess_return"]
    for k in keys:
        va, vb = a.get(k), b.get(k)
        if va is None or (isinstance(va, float) and np.isnan(va)):
            if not ((va is None and vb is None)
                    or (isinstance(va, float) and isinstance(vb, float)
                        and np.isnan(va) and np.isnan(vb))):
                return False
            continue
        if not np.isclose(float(va), float(vb), rtol=1e-9, atol=1e-9):
            return False
    return True


def _check(exit_kw_legacy, exit_spec):
    d = _multi()
    old = legacy_run_backtest(
        data=d, trade_symbol=",".join(SYMS),
        buy_conditions=[_legacy_cond("ma_dev_20d", ">", 0.0)], buy_logic="AND",
        amount_pct=10.0, initial_capital=1e7, **exit_kw_legacy)
    s = StrategyIR(
        signal=_node("ma_dev_20d", ">", 0.0),
        universe=Universe(kind="list", symbols=SYMS),
        position=PositionSpec(entry=Entry(mode="on_signal"), exit=exit_spec),
        simulation=SimSpec(initial_capital=1e7))
    new = run_strategy_ir(s, d)
    assert old["success"] and new["success"], (old.get("error"), new.get("error"))
    assert _eq(old["metrics"], new["metrics"]), (
        f"불일치\n old={old['metrics']}\n new={new['metrics']}")
    return old["metrics"]


def test_portfolio_hold():
    m = _check({"hold_days": 15}, Exit(mode="after_n_days", hold_days=15))
    assert m["n_trades"] >= 1


def test_portfolio_tp_sl():
    _check({"hold_days": 30, "take_profit": 8.0, "stop_loss": -4.0},
           Exit(mode="stop_target", hold_days=30, take_profit=8.0, stop_loss=-4.0))


def test_portfolio_trailing():
    _check({"hold_days": 40, "trail_atr_mult": 2.0, "trail_pct": 6.0},
           Exit(mode="stop_target", hold_days=40, trail_atr_mult=2.0, trail_pct=6.0))


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
