"""축1 나머지 — 단항·이항 산술, 조건선택, 돌파/교차, 수식어.

명세 §3 축1. 기존 affine(mul/add)은 binary(×,＋)로, cross_up/down·modifier는
전용 블록으로 포섭한다.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .catalog import BlockDef, register
from .context import as_bool_panel
from .types import ValueType


# ── 단항 변환 ─────────────────────────────────────────────────────────────────

def _ev_unary(resolved, params, ctx):
    x = resolved["signal"]
    f = params["func"]
    if f == "log":
        return np.log(x.clip(lower=1e-9))
    if f == "exp":
        return np.exp(x)
    if f == "abs":
        return x.abs()
    if f == "sign":
        return np.sign(x)
    if f == "sqrt":
        return np.sqrt(x.clip(lower=0))
    raise ValueError(f"미지원 단항 함수: {f}")


# ── 이항 산술 (affine = binary 조합) ──────────────────────────────────────────

def _ev_binary(resolved, params, ctx):
    a = resolved["a"]
    b = resolved["b"]
    op = params["op"]
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        return a / b
    raise ValueError(f"미지원 이항 연산자: {op}")


# ── 조건 선택 (if_else / 조건부제어) ──────────────────────────────────────────

def _ev_select(resolved, params, ctx):
    cond = as_bool_panel(resolved["cond"])
    a = resolved["a"]
    b = resolved["b"]
    if isinstance(a, (int, float)):
        a = pd.DataFrame(a, index=cond.index, columns=cond.columns)
    if isinstance(b, (int, float)):
        b = pd.DataFrame(b, index=cond.index, columns=cond.columns)
    return a.where(cond, b)


# ── 돌파/교차 → condition ─────────────────────────────────────────────────────

def _ev_cross(resolved, params, ctx):
    left = resolved["left"]
    right = resolved["right"]
    direction = params["direction"]
    left_prev = left.shift(1) if isinstance(left, pd.DataFrame) else left
    right_prev = right.shift(1) if isinstance(right, pd.DataFrame) else right
    if direction == "up":
        out = (left_prev <= right_prev) & (left > right)
    elif direction == "down":
        out = (left_prev >= right_prev) & (left < right)
    else:
        raise ValueError(f"미지원 교차 방향: {direction}")
    return as_bool_panel(out)


# ── 수식어 (지속성·최근성) ────────────────────────────────────────────────────

def _ev_modifier(resolved, params, ctx):
    """기존 analysis._apply_modifier와 동일 의미.

    streak: N일 연속 참 / within: 최근 N일 내 1회 이상 참. days<=1이면 무변환.
    """
    mask = as_bool_panel(resolved["signal"])
    kind = params.get("kind")
    days = int(params.get("days") or 1)
    if days <= 1 or not kind:
        return mask
    m = mask.astype(float)
    if kind == "streak":
        return (m.rolling(days).sum() >= days).fillna(False)
    if kind == "within":
        return (m.rolling(days).sum() >= 1).fillna(False)
    return mask


register(BlockDef("unary", ValueType.SCORE, _ev_unary,
                  slots={"signal": ValueType.SCORE}, doc="log·exp·abs·sign·sqrt"))
register(BlockDef("binary", ValueType.SCORE, _ev_binary,
                  slots={"a": ValueType.SCORE, "b": ValueType.SCORE},
                  doc="＋−×÷ (affine 포함)"))
register(BlockDef("select", ValueType.SCORE, _ev_select,
                  slots={"cond": ValueType.CONDITION, "a": ValueType.SCORE,
                         "b": ValueType.SCORE}, doc="조건 참→A 아니면 B (조건부제어)"))
register(BlockDef("cross", ValueType.CONDITION, _ev_cross,
                  slots={"left": ValueType.SCORE, "right": ValueType.SCORE},
                  doc="상향/하향 돌파"))
register(BlockDef("modifier", ValueType.CONDITION, _ev_modifier,
                  slots={"signal": ValueType.CONDITION},
                  doc="streak(N일 연속)·within(최근 N일 내)"))
