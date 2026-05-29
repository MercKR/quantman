"""P1-6(core) — backtest_from_spec 요청 처리 회귀 (헤드리스).

명세 §11. 파싱·메타규칙·무결성·기본값·실행·경고 경로를 고정한다.
서버 라우터는 이 함수를 인증/dataset 주입만 더해 감싼다.

    cd platform && pytest tests/test_engine_service.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

from quant_core.blocks import DatasetMeta, available_refs  # noqa: E402
from quant_core.ir_engine import backtest_from_spec  # noqa: E402

SYM = "005930"


def _data():
    idx = pd.date_range("2020-01-01", periods=250, freq="B")
    r = np.random.default_rng(11)
    close = np.maximum(100 + np.cumsum(r.normal(0.05, 1.2, 250)), 5.0)
    return {SYM: pd.DataFrame({
        "Open": np.concatenate([[close[0]], close[:-1]]),
        "High": close * 1.01, "Low": close * 0.99, "Close": close,
        "Volume": r.uniform(1e5, 1e6, 250),
        "ma_dev_20d": r.uniform(-5, 5, 250),
        "roic": r.uniform(5, 25, 250),  # 펀더멘털 (PIT 경고 테스트용)
    }, index=idx)}


def _buy(indicator, op, value):
    return {"op": "compare", "params": {"op": op},
            "inputs": {"left": {"op": "data", "params": {"ref": f"__SELF__.{indicator}"}},
                       "right": {"op": "const", "params": {"value": value}}}}


def test_valid_spec_runs():
    spec = {"trade_symbol": SYM, "buy": _buy("ma_dev_20d", ">", 0.0),
            "hold_days": 10, "initial_capital": 1e7}
    res = backtest_from_spec(spec, _data())
    assert res["success"]
    assert "metrics" in res and res["metrics"]["n_trades"] >= 1
    assert res["warnings"] == []  # 기술지표만 → 무결성 경고 없음


def test_missing_buy():
    res = backtest_from_spec({"trade_symbol": SYM}, _data())
    assert not res["success"] and "buy" in res["error"]


def test_type_mismatch_rejected():
    """logic 슬롯에 score(data) → 규칙1 위반으로 거부."""
    bad = {"op": "logic", "params": {"logic": "AND"},
           "inputs": {"0": {"op": "data", "params": {"ref": "__SELF__.ma_dev_20d"}}}}
    res = backtest_from_spec({"trade_symbol": SYM, "buy": bad}, _data())
    assert not res["success"]
    assert any(i["rule"] == "R1" for i in res["issues"])


def test_data_availability_rejected():
    """존재하지 않는 지표 → 규칙0 거부."""
    spec = {"trade_symbol": SYM, "buy": _buy("nonexistent_indic", ">", 0.0)}
    d = _data()
    res = backtest_from_spec(spec, d, valid_refs=available_refs(d))
    assert not res["success"]
    assert any(i["rule"] == "R0" for i in res["issues"])


def test_pit_warning_on_fundamental():
    """펀더멘털(roic) 사용 + PIT 미태깅 → 경고(차단 아님)."""
    spec = {"trade_symbol": SYM, "buy": _buy("roic", ">", 10.0), "hold_days": 10}
    res = backtest_from_spec(spec, _data(), meta=DatasetMeta(has_pit=False))
    assert res["success"]  # 경고지 에러 아님
    assert any("PIT" in w["message"] for w in res["warnings"])


def test_defaults_applied():
    """window 미지정 ts_mean도 기본값(20)으로 실행 — 규칙5."""
    buy = {"op": "compare", "params": {"op": ">"},
           "inputs": {"left": {"op": "data", "params": {"ref": "__SELF__.Close"}},
                      "right": {"op": "ts_mean",
                                "inputs": {"signal": {"op": "data", "params": {"ref": "__SELF__.Close"}}}}}}
    res = backtest_from_spec({"trade_symbol": SYM, "buy": buy, "hold_days": 10}, _data())
    assert res["success"]


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
