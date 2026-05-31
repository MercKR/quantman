"""W2(G1) — ts_regression output=r2 + bar_index 시간축 leaf 검증.

추세강도 필터(T4): ts_regression(가격, bar_index)의 beta=일당 기울기, r2=추세 직선성.
신호 대수에 입력 없는 시간 램프 잎(calendar 동형)과 회귀 결정계수 출력만 추가.

    cd platform && pytest tests/test_trend_regression.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))

from quant_core.blocks import EvalContext, Node, evaluate           # noqa: E402
from quant_core.ir_engine import strategy_from_spec                 # noqa: E402


def _data(ref):
    return {"op": "data", "params": {"ref": ref}}


def _ds():
    """LIN=완전 직선 추세(r²≈1), ALT=교번(추세 없음, r²≈0), UP=완만 상승."""
    idx = pd.date_range("2021-01-01", periods=120, freq="B")
    t = np.arange(120, dtype=float)

    def mk(close):
        return pd.DataFrame({"Open": close, "High": close, "Low": close,
                             "Close": close, "Volume": 1e6}, index=idx)
    return {"LIN": mk(100 + 2 * t),
            "ALT": mk(100 + 10 * ((t % 2) * 2 - 1)),
            "UP": mk(100 * (1.001) ** t)}


def _ev(node_dict, ds):
    return evaluate(Node.model_validate(node_dict), EvalContext.from_dataset(ds))


def test_bar_index_ramp():
    panel = _ev({"op": "bar_index", "params": {}}, _ds())
    assert list(panel["LIN"].to_numpy()[:4]) == [0.0, 1.0, 2.0, 3.0]


def _reg(output, window=30):
    return {"op": "ts_regression", "params": {"window": window, "output": output},
            "inputs": {"y": _data("Close"), "x": {"op": "bar_index", "params": {}}}}


def test_r2_linear_is_one():
    r2 = _ev(_reg("r2"), _ds())
    assert r2["LIN"].dropna().iloc[-1] > 0.999      # 완전 직선 → r²≈1
    assert r2["ALT"].dropna().iloc[-1] < 0.2        # 교번(추세 없음) → r²≈0


def test_beta_slope_sign():
    beta = _ev(_reg("beta"), _ds())
    assert beta["LIN"].dropna().iloc[-1] > 0        # 상승 추세 → 기울기 +
    assert abs(beta["ALT"].dropna().iloc[-1]) < 0.5  # 교번 → 기울기 ≈0


def test_t4_trend_strength_strategy_runs():
    """추세강도 = beta × r2 (score) → 상위 종목 매수 전략으로 실행 가능."""
    strength = {"op": "binary", "params": {"op": "*"},
                "inputs": {"a": _reg("beta"), "b": _reg("r2")}}
    spec = {"signal": strength,
            "universe": {"kind": "list", "symbols": ["LIN", "ALT", "UP"]},
            "position": {"direction": "long", "sizing": {"mode": "equal_weight"},
                         "entry": {"mode": "scheduled", "rebalance": "monthly", "top_n": 1}},
            "simulation": {"initial_capital": 1e7}}
    res = strategy_from_spec(spec, _ds())
    assert res["success"], res


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
