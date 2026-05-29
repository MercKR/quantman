"""S5 — /ir/strategy 핸들러 헤드리스 검증 (StrategyIR 전체 구조 수용).

명세 P1-6·S5. 팩터·펼침·거부 경로를 HTTP 핸들러 직접 호출로 고정.

    cd platform && pytest tests/test_server_ir_strategy.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT / "server"))

ir = pytest.importorskip("app.routers.ir")
from app.routers.ir import ir_strategy  # noqa: E402


def _multi():
    idx = pd.date_range("2020-01-01", periods=252, freq="B")

    def mk(drift, mom):
        close = 100 * (1 + drift) ** np.arange(252)
        return pd.DataFrame({
            "Open": close, "High": close * 1.001, "Low": close * 0.999,
            "Close": close, "Volume": 1e6, "momentum_12_1m": float(mom),
            "ma_dev_20d": np.where(np.arange(252) % 2 == 0, 1.0, -1.0),
        }, index=idx)
    return {"AAA": mk(0.003, 10.0), "BBB": mk(-0.001, -5.0), "CCC": mk(0.0, -2.0)}


@pytest.fixture(autouse=True)
def _patch(monkeypatch):
    monkeypatch.setattr(ir, "get_dataset", _multi)


def _factor_body(top_n=1, direction="long", sweep=None):
    b = {
        "signal": {"op": "data", "params": {"ref": "momentum_12_1m"}},
        "universe": {"kind": "all"},
        "position": {"direction": direction, "sizing": {"mode": "equal_weight"},
                     "entry": {"mode": "scheduled", "rebalance": "monthly", "top_n": top_n}},
        "simulation": {"initial_capital": 1e7},
    }
    if sweep:
        b["sweep"] = sweep
    return b


def test_factor_strategy():
    res = ir_strategy(_factor_body(), user=None)
    assert res["success"], res
    assert "metrics" in res and res["metrics"]["n_trades"] == 0  # 리밸런스 path(trades 미집계)
    assert isinstance(res["equity"], list) and len(res["equity"]) > 0


def test_long_short_strategy():
    res = ir_strategy(_factor_body(direction="long_short"), user=None)
    assert res["success"]
    assert res["metrics"]["total_return"] is not None


def test_parameter_sweep():
    body = _factor_body(sweep={"axis": "parameter",
                               "param_path": "position.entry.top_n",
                               "param_values": [1, 2]})
    res = ir_strategy(body, user=None)
    assert res["success"] and res["axis"] == "parameter"
    assert set(res["buckets"].keys()) == {"1", "2"}


def test_rejects_on_signal_score():
    """on_signal 진입 + score 신호 → 구조 규칙 위반 거부."""
    body = {
        "signal": {"op": "data", "params": {"ref": "momentum_12_1m"}},  # score
        "universe": {"kind": "single", "symbols": ["AAA"]},
        "position": {"entry": {"mode": "on_signal"}},
    }
    res = ir_strategy(body, user=None)
    assert res["success"] is False
    assert any(i["rule"] == "S-entry" for i in res["issues"])


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
