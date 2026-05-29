"""블록 IR — 통합 타입드 노코드 전략/분석 표현.

설계 명세: docs/REDESIGN/block_ir_spec.md
비전: atomic_block_spec_v2.md

이 패키지는 기존 analysis.py(조건 문법)·expression_parser.py(alpha 수식)·
screener spec 셋을 하나의 재귀 트리(Node)로 통합한다. 평가기·UI·LLM이 단일
스키마를 공유한다.
"""

from . import ops_advanced, ops_arith, ops_core, ops_cs, ops_ts  # noqa: F401  (import 시 블록 등록)
from .context import EvalContext, resolve_data, select_symbol  # noqa: F401
from .evaluate import evaluate  # noqa: F401
from .node import Node, const, data  # noqa: F401
from .types import Shape, ValueType  # noqa: F401
from .integrity import (  # noqa: F401
    DatasetMeta, apply_delay, data_time_issues, integrity_issues, param_time_issues,
)
from .validate import (  # noqa: F401
    Issue, apply_defaults, available_refs, infer_shape, is_valid, validate,
)

__all__ = [
    "Node", "data", "const", "ValueType", "Shape",
    "EvalContext", "evaluate", "select_symbol", "resolve_data",
    "validate", "is_valid", "apply_defaults", "available_refs", "infer_shape", "Issue",
    "DatasetMeta", "apply_delay", "integrity_issues", "data_time_issues", "param_time_issues",
]
