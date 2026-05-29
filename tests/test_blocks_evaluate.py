"""P0-2 — 새 평가기 ↔ 기존 build_signal_mask 마스크 동치 검증.

명세 §4. "통합 IR이 기존 조건 엔진을 정확히 대체한다"의 핵심 게이트.
합성 데이터(결정론적)로 golden 5전략의 매수 조건을 새 evaluate로 평가한 마스크가
기존 build_signal_mask와 비트 동일함을 고정한다. 실데이터 의존 없음(CI 안전).

    cd platform && pytest tests/test_blocks_evaluate.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

from quant_core.analysis import build_signal_mask  # noqa: E402
from quant_core.blocks import (  # noqa: E402
    EvalContext, Node, const, data, evaluate, select_symbol,
)


# ── 합성 데이터 ────────────────────────────────────────────────────────────────

def _make_data() -> dict[str, pd.DataFrame]:
    idx = pd.date_range("2021-01-01", periods=150, freq="B")
    rng = np.random.default_rng(42)

    def mk(seed):
        r = np.random.default_rng(seed)
        return pd.DataFrame({
            "price_level": r.uniform(50, 150, 150),
            "ma_dev_20d": r.uniform(-5, 5, 150),
            "ma_gap_20_60": r.uniform(-3, 3, 150),
            "bb_pct": r.uniform(0, 1, 150),
            "pct_change_20d": r.uniform(-10, 10, 150),
            "pct_change_252d": r.uniform(-20, 20, 150),
            "Close": r.uniform(50, 150, 150),
        }, index=idx)

    return {"AAA": mk(1), "BBB": mk(2)}


def _assert_equiv(old_conditions, logic, node, sym, data_dict):
    """기존 build_signal_mask(sym) == 새 evaluate(node)[sym] (NaN→False 정규화 후)."""
    old = build_signal_mask(data_dict, old_conditions, logic, current_symbol=sym)
    ctx = EvalContext.from_dataset(data_dict)
    new_panel = evaluate(node, ctx)
    new = select_symbol(new_panel, sym).reindex(old.index).fillna(False).astype(bool)
    pd.testing.assert_series_equal(new, old, check_names=False)
    # 빈 마스크(전부 False)면 새 평가기가 NaN→False로 무너졌을 수 있어 비공허 확인.
    # (전부 True는 golden 01 "항상 참"처럼 정상이므로 허용)
    assert int(old.sum()) > 0, "마스크가 전부 False — 평가기 무너짐 의심"


# ── golden 5전략 매수조건 동치 ────────────────────────────────────────────────

def _cmp(indicator, op, value):
    """기존 조건 dict 1개 (self-ref 좌변 vs 상수 우변)."""
    return {"left": {"kind": "indicator", "symbol": "__SELF__", "indicator": indicator},
            "op": op, "right": {"kind": "constant", "value": value}}


def _node_cmp(indicator, op, value):
    return Node(op="compare", params={"op": op},
                inputs={"left": data(f"__SELF__.{indicator}"), "right": const(value)})


def test_g01_price_level_gt0():
    _assert_equiv([_cmp("price_level", ">", 0.0)], "AND",
                  _node_cmp("price_level", ">", 0.0), "AAA", _make_data())


def test_g02_above_ma20():
    _assert_equiv([_cmp("ma_dev_20d", ">", 0.0)], "AND",
                  _node_cmp("ma_dev_20d", ">", 0.0), "AAA", _make_data())


def test_g03_uptrend():
    _assert_equiv([_cmp("ma_gap_20_60", ">", 0.0)], "AND",
                  _node_cmp("ma_gap_20_60", ">", 0.0), "AAA", _make_data())


def test_g04_oversold_bb():
    _assert_equiv([_cmp("bb_pct", "<", 0.2)], "AND",
                  _node_cmp("bb_pct", "<", 0.2), "AAA", _make_data())


def test_g05_dual_momentum_AND():
    old = [_cmp("pct_change_20d", ">", 0.0), _cmp("pct_change_252d", ">", 0.0)]
    node = Node(op="logic", params={"logic": "AND"}, inputs={
        "0": _node_cmp("pct_change_20d", ">", 0.0),
        "1": _node_cmp("pct_change_252d", ">", 0.0)})
    _assert_equiv(old, "AND", node, "AAA", _make_data())


# ── 추가 변별: OR 결합, between, 종목 간 비교 ─────────────────────────────────

def test_or_logic():
    old = [_cmp("ma_dev_20d", ">", 2.0), _cmp("bb_pct", ">", 0.8)]
    node = Node(op="logic", params={"logic": "OR"}, inputs={
        "0": _node_cmp("ma_dev_20d", ">", 2.0),
        "1": _node_cmp("bb_pct", ">", 0.8)})
    _assert_equiv(old, "OR", node, "AAA", _make_data())


def test_between():
    old = [{"left": {"kind": "indicator", "symbol": "__SELF__", "indicator": "bb_pct"},
            "op": "between", "right": {"kind": "constant", "value": [0.3, 0.7]}}]
    node = Node(op="compare", params={"op": "between"},
                inputs={"left": data("__SELF__.bb_pct"), "right": const([0.3, 0.7])})
    _assert_equiv(old, "AND", node, "AAA", _make_data())


def test_cross_symbol_reference():
    """[이 종목] pct_change_20d >= BBB.pct_change_20d — 종목 간 비교(브로드캐스트)."""
    old = [{"left": {"kind": "indicator", "symbol": "__SELF__", "indicator": "pct_change_20d"},
            "op": ">=",
            "right": {"kind": "indicator", "symbol": "BBB", "indicator": "pct_change_20d"}}]
    node = Node(op="compare", params={"op": ">="},
                inputs={"left": data("__SELF__.pct_change_20d"),
                        "right": data("BBB.pct_change_20d")})
    _assert_equiv(old, "AND", node, "AAA", _make_data())


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
