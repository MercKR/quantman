"""W4(G3) — 전략 조합(compositional closure) 검증.

전략의 자산곡선을 strat:<id> 합성 심볼로 dataset에 주입 → 자산 원자(universe·rank·sizing·
분석)가 전략에도 들어올림. F3 팩터모멘텀 = 합성 심볼 로테이션. resolver는 테스트용 dict 주입
(server Postgres 불필요). 순환참조·resolver 부재·인과성 검증.

    cd platform && pytest tests/test_compose_strategies.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))

from quant_core.ir_engine import (                       # noqa: E402
    materialize_strategy_assets, strategy_from_spec,
)
from quant_core.ir_engine.spec import StrategyIR          # noqa: E402


def _data(ref):
    return {"op": "data", "params": {"ref": ref}}


def _const(v):
    return {"op": "const", "params": {"value": v}}


def _ds():
    """A 강세·D 약세, 시총고정 momentum_12_1m로 자식 전략이 결정적으로 종목 선택."""
    idx = pd.date_range("2021-01-01", periods=300, freq="B")
    t = np.arange(300, dtype=float)

    def mk(close, mom):
        return pd.DataFrame({"Open": close, "High": close * 1.01, "Low": close * 0.99,
                             "Close": close, "Volume": 1e6, "momentum_12_1m": float(mom)},
                            index=idx)
    return {"A": mk(100 * (1.002) ** t, 10), "B": mk(100 * (1.001) ** t, 5),
            "C": mk(100 * np.ones_like(t), 0), "D": mk(100 * (0.999) ** t, -5)}


def _child(score_node):
    return {"signal": score_node,
            "universe": {"kind": "list", "symbols": ["A", "B", "C", "D"]},
            "position": {"direction": "long", "sizing": {"mode": "equal_weight"},
                         "entry": {"mode": "scheduled", "rebalance": "monthly", "top_n": 1}},
            "simulation": {"initial_capital": 1e7}}


# childWin: 모멘텀 상위(→A, 상승) · childLose: 모멘텀 하위(→D, 하락)
_CHILD_WIN = _child(_data("momentum_12_1m"))
_CHILD_LOSE = _child({"op": "binary", "params": {"op": "*"},
                      "inputs": {"a": _data("momentum_12_1m"), "b": _const(-1)}})


def _resolver(mapping):
    return lambda token: mapping.get(token)


_RESOLVER = _resolver({"win": _CHILD_WIN, "lose": _CHILD_LOSE})


def _parent():
    """두 전략을 60일 추세로 로테이션(top_n=1) — 전략을 자산처럼 다룸(F3)."""
    return {"signal": {"op": "ts_delta", "params": {"window": 60},
                       "inputs": {"signal": _data("Close")}},
            "universe": {"kind": "list", "symbols": ["strat:win", "strat:lose"]},
            "position": {"direction": "long", "sizing": {"mode": "equal_weight"},
                         "entry": {"mode": "scheduled", "rebalance": "monthly", "top_n": 1}},
            "simulation": {"initial_capital": 1e7}}


# ── 물질화 ─────────────────────────────────────────────────────────────────────

def test_materialize_injects_synthetic_equity():
    ir = StrategyIR.model_validate(_parent())
    ds = materialize_strategy_assets(ir, dict(_ds()), _RESOLVER)
    assert "strat:win" in ds and "strat:lose" in ds
    assert "Close" in ds["strat:win"].columns
    # win은 A(상승) 추종 → 마지막 equity > 초기; lose는 D(하락) 추종 → 마지막 < 초기
    win, lose = ds["strat:win"]["Close"].dropna(), ds["strat:lose"]["Close"].dropna()
    assert win.iloc[-1] > win.iloc[0]
    assert lose.iloc[-1] < lose.iloc[0]


def test_materialize_does_not_mutate_shared_dataset():
    base = _ds()
    materialize_strategy_assets(StrategyIR.model_validate(_parent()), dict(base), _RESOLVER)
    assert not any(k.startswith("strat:") for k in base)   # 원본 캐시 오염 없음


# ── F3 로테이션 실행 ───────────────────────────────────────────────────────────

def test_f3_rotation_runs():
    res = strategy_from_spec(_parent(), _ds(), strategy_resolver=_RESOLVER)
    assert res["success"], res
    assert len(res["equity"]) > 0


def test_strategy_as_data_ref_cross_asset():
    """data ref로도 전략 참조 — strat:win.Close를 신호에 직접 쓸 수 있다."""
    spec = {"signal": {"op": "compare", "params": {"op": ">"},
                       "inputs": {"left": _data("strat:win.Close"),
                                  "right": {"op": "ts_mean", "params": {"window": 60},
                                            "inputs": {"signal": _data("strat:win.Close")}}}},
            "universe": {"kind": "list", "symbols": ["A", "B"]},
            "position": {"direction": "long", "sizing": {"mode": "equal_weight"},
                         "entry": {"mode": "on_signal"}, "exit": {"hold_days": 5}},
            "simulation": {"initial_capital": 1e7}}
    res = strategy_from_spec(spec, _ds(), strategy_resolver=_RESOLVER)
    assert res["success"], res


# ── 안전 게이트 ────────────────────────────────────────────────────────────────

def test_missing_resolver_errors():
    res = strategy_from_spec(_parent(), _ds())     # resolver 없음
    assert not res["success"]
    assert "resolver" in res["error"] or "조합" in res["error"]


def test_cycle_detection():
    self_spec = {"signal": _data("Close"),
                 "universe": {"kind": "list", "symbols": ["strat:selfx"]},
                 "position": {"direction": "long", "sizing": {"mode": "equal_weight"},
                              "entry": {"mode": "scheduled", "rebalance": "monthly", "top_n": 1}},
                 "simulation": {"initial_capital": 1e7}}
    ir = StrategyIR.model_validate(self_spec)
    with pytest.raises(ValueError, match="순환"):
        materialize_strategy_assets(ir, dict(_ds()), _resolver({"selfx": self_spec}))


def test_unknown_strategy_errors():
    res = strategy_from_spec(_parent(), _ds(), strategy_resolver=_resolver({}))
    assert not res["success"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
