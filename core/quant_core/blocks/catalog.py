"""블록 레지스트리 — op → 정의(출력타입·슬롯타입·평가함수·기본값).

명세 §3·§5·§12. 평가기(evaluate.py)·op 모듈(ops_*.py)·메타규칙(validate.py)이
공유하는 단일 등록처. 의존 없음(순수 레지스트리) — 순환 import 방지.

slots/variadic_type가 있어야 메타규칙(타입 호환 §5 규칙1)이 트리를 검증할 수 있고,
param_defaults가 있어야 규칙5(완결성·retail 기본값)가 빈칸을 채울 수 있다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from .types import ValueType


@dataclass(frozen=True)
class BlockDef:
    """한 블록 종류의 정의.

    eval_fn 시그니처: (resolved_inputs: dict[str, Any], params: dict, ctx) -> value

    slots: 고정 입력 슬롯 → 요구 ValueType (메타규칙 타입 검증용).
    variadic: True면 슬롯이 동적("0","1",...) — variadic_type이 각 슬롯 요구 타입.
    param_defaults: 빠진 잎 빈칸을 채울 기본값 (규칙5 완결성).
    """

    op: str
    out_type: ValueType
    eval_fn: Callable
    slots: dict = field(default_factory=dict)          # slot → ValueType
    variadic: bool = False
    variadic_type: Optional[ValueType] = None
    param_defaults: dict = field(default_factory=dict)
    requires_panel: bool = False   # 횡단/그룹 블록 — series 입력이면 무의미(규칙2)
    doc: str = ""


CATALOG: dict[str, BlockDef] = {}


def register(bdef: BlockDef) -> BlockDef:
    if bdef.op in CATALOG:
        raise ValueError(f"중복 블록 등록: {bdef.op}")
    CATALOG[bdef.op] = bdef
    return bdef


def get(op: str) -> BlockDef:
    if op not in CATALOG:
        raise KeyError(f"미등록 블록: {op}")
    return CATALOG[op]


def has(op: str) -> bool:
    return op in CATALOG


def catalog_spec() -> list[dict]:
    """등록된 모든 블록의 명세 — 프론트 빌더가 어떤 블록·슬롯·파라미터를 제공할지 안다.

    자기서술적: 슬롯(타입)·파라미터 스키마·카테고리·라벨을 포함해 프론트가 블록
    지식을 하드코딩하지 않게 한다(NL 컴파일러도 같은 계약을 타겟).
    """
    from .param_specs import meta_for, params_for, phrase_for

    out = []
    for op, b in sorted(CATALOG.items()):
        meta = meta_for(op)
        out.append({
            "op": op,
            "label": meta["label"],
            "category": meta["category"],
            "out_type": b.out_type.value,
            "slots": {k: v.value for k, v in b.slots.items()},
            "variadic": b.variadic,
            "variadic_type": b.variadic_type.value if b.variadic_type else None,
            "params": params_for(op),
            "requires_panel": b.requires_panel,
            "phrase": phrase_for(op),    # 문장형 UI 템플릿({slot}/{param} 토큰; 없으면 None)
            "doc": b.doc,
        })
    return out
