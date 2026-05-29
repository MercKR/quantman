"""코어 블록 — 잎(data/const) + 축1 일부(compare/logic).

명세 §3 축1. 기존 analysis._apply_op·_combine_nodes 의미론을 패널 위로 옮긴 것.
import 시 catalog에 등록된다(blocks/__init__가 로드).
"""

from __future__ import annotations

from .catalog import BlockDef, register
from .context import as_bool_panel, resolve_data
from .node import OP_CONST, OP_DATA
from .types import ValueType


# ── 잎 ────────────────────────────────────────────────────────────────────────

def _ev_data(resolved, params, ctx):
    return resolve_data(params["ref"], ctx)


def _ev_const(resolved, params, ctx):
    return params["value"]


# ── 축1: 비교 → condition ─────────────────────────────────────────────────────

def _ev_compare(resolved, params, ctx):
    left = resolved["left"]
    right = resolved["right"]
    op = params["op"]
    if op == "between":
        if not isinstance(right, (list, tuple)) or len(right) < 2:
            raise ValueError("between은 우변에 [min, max] 상수가 필요합니다.")
        lo, hi = right[0], right[1]
        out = (left >= lo) & (left <= hi)
    elif op == ">":
        out = left > right
    elif op == ">=":
        out = left >= right
    elif op == "<":
        out = left < right
    elif op == "<=":
        out = left <= right
    elif op in ("==", "eq"):
        out = left == right
    else:
        raise ValueError(f"미지원 비교 연산자: {op}")
    return as_bool_panel(out)


# ── 축1: 논리 결합 → condition ────────────────────────────────────────────────

def _ev_logic(resolved, params, ctx):
    logic = (params.get("logic") or "AND").upper()
    # 가변 슬롯("0","1",...) 자연 정렬 — "10"이 "9" 뒤로
    keys = sorted(resolved.keys(), key=lambda k: (len(k), k))
    masks = [as_bool_panel(resolved[k]) for k in keys]
    if not masks:
        raise ValueError("logic 블록에 조건이 1개 이상 필요합니다.")
    out = masks[0]
    for m in masks[1:]:
        out = (out & m) if logic == "AND" else (out | m)
    return as_bool_panel(out)


register(BlockDef(OP_DATA, ValueType.SCORE, _ev_data, doc="데이터 참조 잎"))
register(BlockDef(OP_CONST, ValueType.SCORE, _ev_const, doc="상수 잎"))
register(BlockDef("compare", ValueType.CONDITION, _ev_compare,
                  slots={"left": ValueType.SCORE, "right": ValueType.SCORE},
                  doc="수준 비교 (>,>=,<,<=,between,==)"))
register(BlockDef("logic", ValueType.CONDITION, _ev_logic,
                  variadic=True, variadic_type=ValueType.CONDITION, doc="AND/OR 결합"))
