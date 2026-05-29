"""S4 — 펼침 축 확장(parameter·asset·condition) 회귀.

명세 §4. 전략을 축 위에서 반복/분할해 resultset을 내는지 고정한다.

    cd platform && pytest tests/test_engine_sweep_axes.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

from quant_core.blocks import Node, const, data  # noqa: E402
from quant_core.ir_engine import (  # noqa: E402
    Entry, PositionSpec, Sizing, SimSpec, StrategyIR, SweepSpec, Universe, run_sweep,
)


def _multi():
    idx = pd.date_range("2020-01-01", periods=252, freq="B")

    def mk(drift, mom):
        close = 100 * (1 + drift) ** np.arange(252)
        return pd.DataFrame({
            "Open": close, "High": close * 1.001, "Low": close * 0.999,
            "Close": close, "Volume": 1e6, "momentum_12_1m": float(mom),
        }, index=idx)
    d = {"AAA": mk(0.003, 10.0), "BBB": mk(-0.001, -5.0), "CCC": mk(0.001, 2.0)}
    # 국면 라벨용 시장 시리즈
    vix = pd.DataFrame({"Close": np.where(np.arange(252) < 126, 15.0, 35.0)},
                       index=idx)
    d["VIX"] = vix
    return d


def _factor(top_n=1):
    return StrategyIR(
        signal=data("momentum_12_1m"), universe=Universe(kind="all"),
        position=PositionSpec(direction="long", sizing=Sizing(mode="equal_weight"),
                              entry=Entry(mode="scheduled", rebalance="monthly", top_n=top_n)),
        simulation=SimSpec(initial_capital=1e7))


def test_parameter_axis():
    s = _factor()
    s.sweep = SweepSpec(axis="parameter", param_path="position.entry.top_n",
                        param_values=[1, 2, 3])
    res = run_sweep(s, _multi())
    assert res["success"] and res["axis"] == "parameter"
    assert set(res["buckets"].keys()) == {"1", "2", "3"}
    assert all("mean" in b for b in res["buckets"].values())


def test_asset_axis():
    s = _factor()
    s.sweep = SweepSpec(axis="asset", assets=["AAA", "BBB", "CCC"])
    res = run_sweep(s, _multi())
    assert res["success"] and res["axis"] == "asset"
    assert set(res["buckets"].keys()) == {"AAA", "BBB", "CCC"}
    # AAA(상승) 누적수익 > BBB(하락)
    assert res["buckets"]["AAA"]["cum_return"] > res["buckets"]["BBB"]["cum_return"]


def test_condition_axis_regime():
    s = _factor()
    # VIX 국면(저/고)별 분할
    s.sweep = SweepSpec(axis="condition",
                        label=Node(op="bucket", params={"edges": [25.0]},
                                   inputs={"signal": data("VIX.Close")}))
    res = run_sweep(s, _multi())
    assert res["success"] and res["axis"] == "condition"
    assert len(res["buckets"]) >= 2          # 저변동성(0)·고변동성(1)
    assert "overall" in res


def test_axis_none_runs_single():
    s = _factor()
    res = run_sweep(s, _multi())   # sweep.axis 기본 none
    assert res["success"]
    assert "equity" in res


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
