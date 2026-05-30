"""Stage 3 — 백테스트 스크리너 유니버스(PIT) 검증.

screener = filter(조건 Node, 임계) + rank(순위컷)의 시점별 AND 자격 마스크. 각 리밸런스 시점에
그 날의 값으로 자격 판정(PIT). 기존엔 validate가 차단하던 stub — 데이터 연동(market_cap) 후 해제.

    cd platform && pytest tests/test_screener.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))

from quant_core.blocks import EvalContext            # noqa: E402
from quant_core.ir_engine import strategy_from_spec  # noqa: E402
from quant_core.ir_engine.engine import _screener_mask  # noqa: E402


def _ds():
    """A·B는 초기 대형(시총↓ 추세), C·D는 후기 대형(시총↑) — 시점별 자격이 뒤집히게."""
    idx = pd.date_range("2021-01-01", periods=300, freq="B")
    t = np.arange(300)

    def mk(mc, mom):
        return pd.DataFrame({"Open": 100., "High": 101., "Low": 99., "Close": 100., "Volume": 1e6,
                             "momentum_12_1m": float(mom), "market_cap": mc}, index=idx)
    return {"A": mk(100 - 0.1 * t, 5), "B": mk(95 - 0.1 * t, 4),
            "C": mk(10 + 0.3 * t, 3), "D": mk(8 + 0.3 * t, 2)}


def _spec(screener: dict) -> dict:
    return {"signal": {"op": "data", "params": {"ref": "momentum_12_1m"}},
            "universe": {"kind": "screener", "screener": screener},
            "position": {"direction": "long", "sizing": {"mode": "equal_weight"},
                         "entry": {"mode": "scheduled", "rebalance": "monthly", "top_n": 2}},
            "simulation": {"initial_capital": 1e7}}


def test_screener_rank_topn_runs():
    res = strategy_from_spec(_spec({"rank": {"ref": "market_cap", "top_n": 2, "direction": "top"}}), _ds())
    assert res["success"], res
    assert len(res["equity"]) > 0


def test_screener_filter_threshold_runs():
    flt = {"filter": {"op": "compare", "params": {"op": ">"},
                      "inputs": {"left": {"op": "data", "params": {"ref": "market_cap"}},
                                 "right": {"op": "const", "params": {"value": 50.0}}}}}
    res = strategy_from_spec(_spec(flt), _ds())
    assert res["success"], res


def test_screener_pit_eligibility_flips():
    """리밸런스 시점값으로 자격 판정(PIT) — 정적 스냅샷이 아님."""
    ctx = EvalContext.from_dataset(_ds())
    elig = _screener_mask({"rank": {"ref": "market_cap", "top_n": 2, "direction": "top"}},
                          ctx, ["A", "B", "C", "D"])
    assert [c for c in elig.columns if elig.iloc[0][c]] == ["A", "B"]    # 초기 대형
    assert [c for c in elig.columns if elig.iloc[-1][c]] == ["C", "D"]   # 후기 대형


def test_screener_requires_filter_or_rank():
    res = strategy_from_spec(_spec({}), _ds())
    assert not res["success"]
    assert any(i["rule"] == "S-univ" for i in res["issues"])


def test_screener_rejects_on_signal():
    spec = _spec({"rank": {"ref": "market_cap", "top_n": 2}})
    spec["position"]["entry"] = {"mode": "on_signal"}
    spec["signal"] = {"op": "compare", "params": {"op": ">"},
                      "inputs": {"left": {"op": "data", "params": {"ref": "market_cap"}},
                                 "right": {"op": "const", "params": {"value": 50.0}}}}
    res = strategy_from_spec(spec, _ds())
    assert not res["success"]
    assert any(i["rule"] == "S-univ" for i in res["issues"])


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
