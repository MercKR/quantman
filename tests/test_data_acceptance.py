"""Phase 4 — 데이터 수급 정합 인수(acceptance).

전략이 요구하는 데이터(deps) ↔ 수급된 데이터(build_dataset_manifest) ↔ 무결성 게이트가
한 계약(매니페스트) 위에서 end-to-end로 맞물리는지 고정한다. 실데이터 없이 합성으로 검증.

    cd platform && pytest tests/test_data_acceptance.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT / "server"))

pytest.importorskip("app.data_manifest")
from app.data_manifest import build_dataset_manifest  # noqa: E402
from quant_core.ir_engine import strategy_from_spec  # noqa: E402


def _dataset(include_vix=True):
    idx = pd.date_range("2020-01-01", periods=252, freq="B")

    def mk(mom):
        c = 100 * (1.001) ** np.arange(252)
        return pd.DataFrame({"Open": c, "High": c * 1.01, "Low": c * 0.99, "Close": c,
                             "Volume": 1e6, "momentum_12_1m": float(mom),
                             "pct_change_252d": float(mom), "rsi_14": 25.0}, index=idx)
    ds = {"005930": mk(9), "000660": mk(4), "035420": mk(-3)}
    if include_vix:
        ds["VIX"] = mk(0)
    return ds


def _factor_all():
    return {"signal": {"op": "rank", "inputs": {"signal": {"op": "data", "params": {"ref": "momentum_12_1m"}}}},
            "universe": {"kind": "all"},
            "position": {"direction": "long", "sizing": {"mode": "equal_weight"},
                         "entry": {"mode": "scheduled", "rebalance": "monthly", "top_n": 2}}}


def test_acceptance_factor_all_flags_survivorship():
    ds = _dataset()
    m = build_dataset_manifest(ds)
    res = strategy_from_spec(_factor_all(), ds, manifest=m, strict=False)
    assert res["success"]                                  # 경고지 차단 아님(연구 모드)
    rules = {w["rule"] for w in res.get("warnings", [])}
    assert "D-surv" in rules                               # 멤버십 이력 없음 → 생존편향 경고
    # D-adj 미발생: ohlcv.kr은 split_adjusted(FDR 실측 검증)로 DataSpec 요구와 일치(Stage 4 정정).
    assert "D-adj" not in rules


def test_acceptance_strict_blocks_survivorship():
    ds = _dataset()
    m = build_dataset_manifest(ds)
    res = strategy_from_spec(_factor_all(), ds, manifest=m, strict=True)
    assert not res["success"]                              # 실전 strict → 거부
    assert any(i["rule"] == "D-surv" for i in res["issues"])


def test_acceptance_macro_ref_present_vs_absent():
    spec = {"signal": {"op": "compare", "params": {"op": ">"},
                       "inputs": {"left": {"op": "data", "params": {"ref": "__SELF__.Close"}},
                                  "right": {"op": "data", "params": {"ref": "VIX.Close"}}}},
            "universe": {"kind": "single", "symbols": ["005930"]},
            "position": {"entry": {"mode": "on_signal"}}}
    # VIX 수급됨 → D-ref 없음
    ds = _dataset(include_vix=True)
    res = strategy_from_spec(spec, ds, manifest=build_dataset_manifest(ds))
    assert res["success"] and not any(w["rule"] == "D-ref" for w in res.get("warnings", []))
    # VIX 미수급 → D-ref 거부
    ds2 = _dataset(include_vix=False)
    res2 = strategy_from_spec(spec, ds2, manifest=build_dataset_manifest(ds2))
    assert not res2["success"] and any(i["rule"] == "D-ref" for i in res2["issues"])


def test_acceptance_no_manifest_keeps_legacy_behavior():
    ds = _dataset()
    res = strategy_from_spec(_factor_all(), ds)            # manifest 미전달 → 게이트 skip
    assert res["success"]
    assert not any(w["rule"].startswith("D-") for w in res.get("warnings", []))


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
