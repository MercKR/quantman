"""P0-1 — 블록 IR 타입 시스템 + Node 스키마 회귀.

명세 §2.2·2.3. 통합 Node가 재귀 중첩·직렬화 round-trip을 정확히 보존하고,
잘못된 필드를 거부하는지 고정한다.

    cd platform && pytest tests/test_blocks_node.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

from quant_core.blocks.node import OP_CONST, OP_DATA, Node, const, data  # noqa: E402
from quant_core.blocks.types import Shape, ValueType  # noqa: E402


# ── 타입 enum ─────────────────────────────────────────────────────────────────

def test_value_types_complete():
    """비전 §1.2 값 타입 6종이 빠짐없이 정의."""
    assert {v.value for v in ValueType} == {
        "score", "condition", "scalar", "label", "distribution", "resultset"}
    # str enum이라 문자열 비교 가능 (직렬화·UI 호환)
    assert ValueType.SCORE == "score"


def test_shapes_complete():
    """비전 §3.1 형태축 5종."""
    assert {s.value for s in Shape} == {
        "panel", "series", "vector", "grouplabel", "static"}
    assert Shape.PANEL == "panel"


# ── 잎 헬퍼 ───────────────────────────────────────────────────────────────────

def test_data_leaf():
    d = data("Close")
    assert d.op == OP_DATA
    assert d.params["ref"] == "Close"
    assert d.inputs == {}


def test_const_leaf():
    c = const(30)
    assert c.op == OP_CONST
    assert c.params["value"] == 30
    # between용 리스트 상수
    rng = const([10, 90])
    assert rng.params["value"] == [10, 90]


# ── 재귀 중첩 (가지 빈칸) ──────────────────────────────────────────────────────

def test_nested_branch_blank():
    """rank(ts_corr(Close, Volume, window=10)) — 가지 빈칸에 블록 중첩.

    기존 Operand로는 불가능했던 신호-in-신호. 자유도의 핵심.
    """
    tree = Node(op="rank", inputs={"signal":
        Node(op="ts_corr", params={"window": 10},
             inputs={"a": data("Close"), "b": data("Volume")})})
    assert tree.op == "rank"
    inner = tree.inputs["signal"]
    assert inner.op == "ts_corr"
    assert inner.params["window"] == 10
    assert inner.inputs["a"].params["ref"] == "Close"
    assert inner.inputs["b"].params["ref"] == "Volume"


def test_condition_tree():
    """RSI(14) < 30 — 명세 §2.5 예시."""
    cond = Node(op="compare", params={"op": "<"},
                inputs={"left": data("__SELF__.rsi_14"), "right": const(30)})
    assert cond.op == "compare"
    assert cond.params["op"] == "<"
    assert cond.inputs["left"].params["ref"] == "__SELF__.rsi_14"
    assert cond.inputs["right"].params["value"] == 30


# ── 직렬화 round-trip ─────────────────────────────────────────────────────────

def test_roundtrip_preserves_tree():
    """model_dump → model_validate가 트리를 비트 보존 (서버 JSON 저장·전송)."""
    tree = Node(op="logic", params={"logic": "AND"}, inputs={
        "0": Node(op="compare", params={"op": "<"},
                  inputs={"left": data("__SELF__.rsi_14"), "right": const(30)}),
        "1": Node(op="compare", params={"op": ">"},
                  inputs={"left": data("__SELF__.pct_change_20d"), "right": const(0.0)}),
    })
    restored = Node.model_validate(tree.model_dump())
    assert restored == tree


# ── 무결한 조립 가드 ──────────────────────────────────────────────────────────

def test_extra_field_forbidden():
    """오타·미정의 필드는 즉시 거부 (잘못된 트리 차단)."""
    with pytest.raises(Exception):
        Node(op="compare", bogus=1)


def test_defaults_empty():
    n = Node(op="data")
    assert n.inputs == {}
    assert n.params == {}


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
