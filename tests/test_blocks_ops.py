"""P0-3 — 축1/축2a 블록 ↔ 기존 문법 동치.

명세 §3. 기존 history(mean/lag/percentile)·cross·modifier·affine(mul/add)을
새 블록 트리로 표현했을 때 build_signal_mask와 비트 동일함을 고정한다.

    cd platform && pytest tests/test_blocks_ops.py -v
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


def _make_data() -> dict[str, pd.DataFrame]:
    idx = pd.date_range("2021-01-01", periods=200, freq="B")

    def mk(seed):
        r = np.random.default_rng(seed)
        # 누적합으로 추세 있는 시계열 — cross/modifier 변별력 확보
        close = 100 + np.cumsum(r.normal(0, 1, 200))
        return pd.DataFrame({
            "Close": close,
            "price_level": close,
            "ma_dev_20d": r.uniform(-5, 5, 200),
            "pct_change_20d": r.uniform(-10, 10, 200),
            "rsi_14": r.uniform(10, 90, 200),
        }, index=idx)

    return {"AAA": mk(1), "BBB": mk(2)}


def _equiv(old_conditions, node, sym="AAA", logic="AND"):
    data_dict = _make_data()
    old = build_signal_mask(data_dict, old_conditions, logic, current_symbol=sym)
    ctx = EvalContext.from_dataset(data_dict)
    new = select_symbol(evaluate(node, ctx), sym).reindex(old.index).fillna(False).astype(bool)
    pd.testing.assert_series_equal(new, old, check_names=False)
    return int(old.sum())


# ── history (ts_*로 포섭) ─────────────────────────────────────────────────────

def test_history_mean():
    old = [{"left": {"kind": "indicator", "symbol": "__SELF__", "indicator": "Close"},
            "op": ">",
            "right": {"kind": "history", "symbol": "__SELF__", "indicator": "Close",
                      "stat": "mean", "window": 20}}]
    node = Node(op="compare", params={"op": ">"}, inputs={
        "left": data("__SELF__.Close"),
        "right": Node(op="ts_mean", params={"window": 20},
                      inputs={"signal": data("__SELF__.Close")})})
    assert _equiv(old, node) > 0


def test_history_lag():
    old = [{"left": {"kind": "indicator", "symbol": "__SELF__", "indicator": "Close"},
            "op": ">",
            "right": {"kind": "history", "symbol": "__SELF__", "indicator": "Close",
                      "stat": "lag", "window": 5}}]
    node = Node(op="compare", params={"op": ">"}, inputs={
        "left": data("__SELF__.Close"),
        "right": Node(op="ts_delay", params={"window": 5},
                      inputs={"signal": data("__SELF__.Close")})})
    assert _equiv(old, node) > 0


def test_history_percentile():
    old = [{"left": {"kind": "indicator", "symbol": "__SELF__", "indicator": "rsi_14"},
            "op": ">",
            "right": {"kind": "history", "symbol": "__SELF__", "indicator": "rsi_14",
                      "stat": "percentile", "window": 20, "percentile": 80}}]
    node = Node(op="compare", params={"op": ">"}, inputs={
        "left": data("__SELF__.rsi_14"),
        "right": Node(op="ts_percentile", params={"window": 20, "percentile": 80},
                      inputs={"signal": data("__SELF__.rsi_14")})})
    assert _equiv(old, node) > 0


# ── cross ─────────────────────────────────────────────────────────────────────

def test_cross_up_const():
    old = [{"left": {"kind": "indicator", "symbol": "__SELF__", "indicator": "pct_change_20d"},
            "op": "cross_up",
            "right": {"kind": "constant", "value": 0.0}}]
    node = Node(op="cross", params={"direction": "up"}, inputs={
        "left": data("__SELF__.pct_change_20d"), "right": const(0.0)})
    assert _equiv(old, node) > 0


def test_cross_down_series():
    old = [{"left": {"kind": "indicator", "symbol": "__SELF__", "indicator": "Close"},
            "op": "cross_down",
            "right": {"kind": "history", "symbol": "__SELF__", "indicator": "Close",
                      "stat": "mean", "window": 20}}]
    node = Node(op="cross", params={"direction": "down"}, inputs={
        "left": data("__SELF__.Close"),
        "right": Node(op="ts_mean", params={"window": 20},
                      inputs={"signal": data("__SELF__.Close")})})
    assert _equiv(old, node) > 0


# ── modifier ──────────────────────────────────────────────────────────────────

def test_modifier_streak():
    old = [{"left": {"kind": "indicator", "symbol": "__SELF__", "indicator": "ma_dev_20d"},
            "op": ">", "right": {"kind": "constant", "value": 0.0},
            "modifier": {"kind": "streak", "days": 3}}]
    node = Node(op="modifier", params={"kind": "streak", "days": 3}, inputs={
        "signal": Node(op="compare", params={"op": ">"}, inputs={
            "left": data("__SELF__.ma_dev_20d"), "right": const(0.0)})})
    assert _equiv(old, node) > 0


def test_modifier_within():
    old = [{"left": {"kind": "indicator", "symbol": "__SELF__", "indicator": "ma_dev_20d"},
            "op": ">", "right": {"kind": "constant", "value": 2.0},
            "modifier": {"kind": "within", "days": 5}}]
    node = Node(op="modifier", params={"kind": "within", "days": 5}, inputs={
        "signal": Node(op="compare", params={"op": ">"}, inputs={
            "left": data("__SELF__.ma_dev_20d"), "right": const(2.0)})})
    assert _equiv(old, node) > 0


# ── affine (mul/add → binary) ─────────────────────────────────────────────────

def test_affine_mul():
    old = [{"left": {"kind": "indicator", "symbol": "__SELF__", "indicator": "Close"},
            "op": ">=",
            "right": {"kind": "indicator", "symbol": "__SELF__", "indicator": "price_level",
                      "mul": 0.95}}]
    node = Node(op="compare", params={"op": ">="}, inputs={
        "left": data("__SELF__.Close"),
        "right": Node(op="binary", params={"op": "*"}, inputs={
            "a": data("__SELF__.price_level"), "b": const(0.95)})})
    assert _equiv(old, node) > 0


def test_affine_mul_add():
    # close > 0.5*close + 50  ⇔  close > 100 → 합성 데이터에서 참/거짓 혼재
    old = [{"left": {"kind": "indicator", "symbol": "__SELF__", "indicator": "Close"},
            "op": ">",
            "right": {"kind": "indicator", "symbol": "__SELF__", "indicator": "price_level",
                      "mul": 0.5, "add": 50.0}}]
    node = Node(op="compare", params={"op": ">"}, inputs={
        "left": data("__SELF__.Close"),
        "right": Node(op="binary", params={"op": "+"}, inputs={
            "a": Node(op="binary", params={"op": "*"}, inputs={
                "a": data("__SELF__.price_level"), "b": const(0.5)}),
            "b": const(50.0)})})
    assert _equiv(old, node) > 0


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
