"""평가기 — 블록 트리를 순회하며 타입드 값을 산출.

명세 §4. 매수조건(type:condition)·알파가중치(type:score) 모두 이 한 함수로 평가.

블록 구현(eval_fn)은 ops_*.py에 등록되고 여기 walker가 호출한다.
"""

from __future__ import annotations

from .catalog import get
from .node import Node


def evaluate(node: Node, ctx):
    """블록 트리를 재귀 평가. 하위 블록(inputs)을 먼저 평가 후 op의 eval_fn 호출."""
    bdef = get(node.op)
    resolved = {slot: evaluate(child, ctx) for slot, child in node.inputs.items()}
    return bdef.eval_fn(resolved, node.params, ctx)
