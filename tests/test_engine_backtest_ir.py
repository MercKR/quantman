"""P1-3 — IR 백테스트(run_backtest_ir) ↔ 기존 run_backtest metric 동치.

명세 §7·§14 Phase 1. 새 평가기로 구동한 백테스트가 검증된 기존 엔진과 metric이
비트 동일함을 고정한다. 기존 run_backtest는 golden_baseline 검증을 이미 통과하므로,
이 동치가 성립하면 IR 백테스트도 golden을 전이적으로 재현한다.

    cd platform && pytest tests/test_engine_backtest_ir.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

from quant_core.backtest import run_backtest  # noqa: E402  (기존 엔진)
from quant_core.blocks import Node, const, data  # noqa: E402
from quant_core.ir_engine import run_backtest_ir  # noqa: E402

SYM = "005930"


def _make_data() -> dict[str, pd.DataFrame]:
    idx = pd.date_range("2020-01-01", periods=400, freq="B")
    r = np.random.default_rng(11)
    close = 100 + np.cumsum(r.normal(0.05, 1.5, 400))
    close = np.maximum(close, 5.0)
    high = close * (1 + np.abs(r.normal(0, 0.01, 400)))
    low = close * (1 - np.abs(r.normal(0, 0.01, 400)))
    open_ = np.concatenate([[close[0]], close[:-1]])
    atr = pd.Series(high - low).rolling(14).mean().bfill().to_numpy()
    return {SYM: pd.DataFrame({
        "Open": open_, "High": high, "Low": low, "Close": close,
        "Volume": r.uniform(1e5, 1e6, 400),
        "price_level": close,
        "ma_dev_20d": r.uniform(-5, 5, 400),
        "ma_gap_20_60": r.uniform(-3, 3, 400),
        "bb_pct": r.uniform(0, 1, 400),
        "pct_change_20d": r.uniform(-10, 10, 400),
        "pct_change_252d": r.uniform(-20, 20, 400),
        "atr_14": atr,
    }, index=idx)}


def _cmp(indicator, op, value):
    return {"left": {"kind": "indicator", "symbol": "__SELF__", "indicator": indicator},
            "op": op, "right": {"kind": "constant", "value": value}}


def _node(indicator, op, value):
    return Node(op="compare", params={"op": op},
                inputs={"left": data(f"__SELF__.{indicator}"), "right": const(value)})


def _metrics_equal(a: dict, b: dict) -> bool:
    keys = ["total_return", "cagr", "mdd", "sharpe", "n_trades",
            "win_rate", "avg_hold", "avg_trade_return",
            "bench_total", "bench_cagr", "bench_mdd", "excess_return"]
    for k in keys:
        va, vb = a.get(k), b.get(k)
        if va is None or vb is None or (isinstance(va, float) and np.isnan(va)):
            if not ((va is None and vb is None)
                    or (isinstance(va, float) and isinstance(vb, float)
                        and np.isnan(va) and np.isnan(vb))):
                return False
            continue
        if not np.isclose(float(va), float(vb), rtol=1e-9, atol=1e-9):
            return False
    return True


def _check(buy_conditions, buy_logic, buy_node, **exit_kw):
    d = _make_data()
    old = run_backtest(data=d, trade_symbol=SYM, buy_conditions=buy_conditions,
                       buy_logic=buy_logic, initial_capital=1e7, **exit_kw)
    new = run_backtest_ir(d, SYM, buy_node, initial_capital=1e7, **exit_kw)
    assert old["success"] and new["success"], (old.get("error"), new.get("error"))
    assert _metrics_equal(old["metrics"], new["metrics"]), (
        f"metric 불일치\n old={old['metrics']}\n new={new['metrics']}")
    return old["metrics"]


# ── golden 단일종목 전략 ──────────────────────────────────────────────────────

def test_g01_buy_and_hold():
    m = _check([_cmp("price_level", ">", 0.0)], "AND",
               _node("price_level", ">", 0.0), hold_days=252)
    assert m["n_trades"] >= 1


def test_g02_above_ma20():
    _check([_cmp("ma_dev_20d", ">", 0.0)], "AND",
           _node("ma_dev_20d", ">", 0.0), hold_days=20)


def test_g03_uptrend_tp_sl():
    _check([_cmp("ma_gap_20_60", ">", 0.0)], "AND",
           _node("ma_gap_20_60", ">", 0.0),
           hold_days=60, take_profit=10.0, stop_loss=-5.0)


def test_g04_oversold_tp_sl():
    _check([_cmp("bb_pct", "<", 0.2)], "AND",
           _node("bb_pct", "<", 0.2),
           hold_days=10, take_profit=5.0, stop_loss=-3.0)


def test_g05_dual_momentum_AND():
    old_conds = [_cmp("pct_change_20d", ">", 0.0), _cmp("pct_change_252d", ">", 0.0)]
    node = Node(op="logic", params={"logic": "AND"}, inputs={
        "0": _node("pct_change_20d", ">", 0.0),
        "1": _node("pct_change_252d", ">", 0.0)})
    _check(old_conds, "AND", node, hold_days=60, stop_loss=-10.0)


# ── 청산 유형 망라 (TP·SL·트레일링) ──────────────────────────────────────────

def test_trailing_atr_and_pct():
    m = _check([_cmp("ma_dev_20d", ">", -1.0)], "AND",
               _node("ma_dev_20d", ">", -1.0),
               hold_days=30, take_profit=8.0, stop_loss=-4.0,
               trail_atr_mult=2.0, trail_pct=5.0)
    assert m["n_trades"] >= 1


def test_close_fill_model():
    """fill=close 경로도 동치."""
    d = _make_data()
    old = run_backtest(data=d, trade_symbol=SYM,
                       buy_conditions=[_cmp("ma_dev_20d", ">", 0.0)], buy_logic="AND",
                       hold_days=15, fill="close", initial_capital=1e7)
    new = run_backtest_ir(d, SYM, _node("ma_dev_20d", ">", 0.0),
                          hold_days=15, fill="close", initial_capital=1e7)
    assert _metrics_equal(old["metrics"], new["metrics"])


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
