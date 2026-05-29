"""P0-4 — 횡단/그룹 블록 ↔ ExpressionParser(alpha 수식) 동치.

명세 §3 축3·축4·§4. "통합 IR이 alpha 수식 엔진도 정확히 대체한다"의 게이트.
새 evaluate(블록 트리)가 ExpressionParser.evaluate(수식 문자열)과 패널 단위로
동일함을 고정한다.

    cd platform && pytest tests/test_blocks_cs.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

from quant_core.blocks import EvalContext, Node, data, evaluate  # noqa: E402
from quant_core.expression_parser import ExpressionParser  # noqa: E402


def _panel_data() -> dict[str, pd.DataFrame]:
    idx = pd.date_range("2021-01-01", periods=80, freq="B")
    syms = ["AAA", "BBB", "CCC", "DDD"]
    out = {}
    for i, s in enumerate(syms):
        r = np.random.default_rng(i + 1)
        out[s] = pd.DataFrame({
            "momentum_12_1m": r.uniform(-20, 20, 80),
            "Close": 100 + np.cumsum(r.normal(0, 1, 80)),
            "Volume": r.uniform(1e5, 1e6, 80),
        }, index=idx)
    return out


def _equiv(expr: str, node: Node):
    d = _panel_data()
    old = ExpressionParser(d).evaluate(expr)
    new = evaluate(node, EvalContext.from_dataset(d))
    assert isinstance(new, pd.DataFrame), "횡단 블록은 패널을 반환해야"
    pd.testing.assert_frame_equal(new, old, check_dtype=False)


def test_rank():
    _equiv("rank(momentum_12_1m)",
           Node(op="rank", inputs={"signal": data("momentum_12_1m")}))


def test_zscore():
    _equiv("zscore(momentum_12_1m)",
           Node(op="zscore", inputs={"signal": data("momentum_12_1m")}))


def test_normalize():
    _equiv("normalize(momentum_12_1m)",
           Node(op="normalize", inputs={"signal": data("momentum_12_1m")}))


def test_scale():
    _equiv("scale(momentum_12_1m)",
           Node(op="scale", inputs={"signal": data("momentum_12_1m")}))


def test_group_neutralize():
    _equiv("group_neutralize(momentum_12_1m)",
           Node(op="group_neutralize", inputs={"signal": data("momentum_12_1m")}))


def test_hump():
    _equiv("hump(momentum_12_1m, 0.5)",
           Node(op="hump", params={"threshold": 0.5},
                inputs={"signal": data("momentum_12_1m")}))


def test_nested_rank_of_ts_mean():
    """rank(ts_mean(Close, 10)) — 횡단 블록 가지에 시계열 블록 중첩."""
    _equiv("rank(ts_mean(Close, 10))",
           Node(op="rank", inputs={"signal":
               Node(op="ts_mean", params={"window": 10},
                    inputs={"signal": data("Close")})}))


def test_complex_alpha():
    """rank(ts_delta(Close, 5)) - 0.5*zscore(momentum_12_1m) — 산술 결합 포함."""
    expr = "rank(ts_delta(Close, 5)) - 0.5 * zscore(momentum_12_1m)"
    node = Node(op="binary", params={"op": "-"}, inputs={
        "a": Node(op="rank", inputs={"signal":
            Node(op="ts_delta", params={"window": 5}, inputs={"signal": data("Close")})}),
        "b": Node(op="binary", params={"op": "*"}, inputs={
            "a": Node(op="const", params={"value": 0.5}),
            "b": Node(op="zscore", inputs={"signal": data("momentum_12_1m")})})})
    _equiv(expr, node)


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
