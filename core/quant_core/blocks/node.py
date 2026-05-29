"""통합 Node 스키마 — 노코드 전략/분석의 단일 표현.

명세 §2.3·2.4.

설계 핵심: **모든 것이 블록(Node)이다.**
  - 가지 빈칸(비전 §1.3) = ``inputs`` 의 슬롯 — 또 다른 Node가 들어감(재귀 중첩).
    복잡한 전략은 전부 이 중첩으로 만든다.
  - 잎 빈칸 = 두 가지로 나뉜다:
      · 데이터/상수 잎 → ``inputs`` 에 들어가는 터미널 Node (op="data"/"const").
      · 기간N·옵션·그룹키·퍼센트 → 그 노드의 ``params`` 항목(드롭다운/입력).

기존 Operand는 스칼라 잎만 가능했다. Node.inputs가 다른 Node를 받는 것이
"높은 자유도"의 정체 — 예: rank(ts_corr(Close, Volume)) 같은 중첩.

출력 타입(ValueType)·형태(Shape)는 저장하지 않고 catalog의 타입규칙으로
평가/검증 시 추론한다(단일 진실 공급원 — 저장 시 불일치 위험 차단).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# 터미널(잎) 블록의 예약 op 이름.
OP_DATA = "data"    # params={"ref": "<데이터 키>"} — 예: "Close", "VIX.Close", "__SELF__.rsi_14"
OP_CONST = "const"  # params={"value": <숫자 | [min,max]>}


class Node(BaseModel):
    """블록 트리의 노드. op·inputs·params로 모든 블록을 표현한다.

    예) RSI(14) < 30:
        Node(op="compare", params={"op": "<"},
             inputs={"left": data("__SELF__.rsi_14"), "right": const(30)})
    """

    op: str
    # 가지 빈칸 — 슬롯명 → 하위 블록(재귀). 비어 있으면 터미널(잎).
    inputs: dict[str, "Node"] = Field(default_factory=dict)
    # 잎 빈칸 — window·option·groupkey·value·ref 등. 블록마다 스키마 다름(catalog 검증).
    params: dict[str, Any] = Field(default_factory=dict)

    # 오타·미정의 필드를 즉시 거부 (잘못된 트리 조립 차단).
    model_config = {"extra": "forbid"}


Node.model_rebuild()  # 자기참조(inputs: dict[str, Node]) 해소


# ── 잎 생성 헬퍼 ──────────────────────────────────────────────────────────────

def data(ref: str) -> Node:
    """데이터 참조 잎. ref 예: "Close"(패널)·"VIX.Close"(시장)·"__SELF__.rsi_14"([이 종목])."""
    return Node(op=OP_DATA, params={"ref": ref})


def const(value: Any) -> Node:
    """상수 잎. value는 숫자 또는 [min, max](between용)."""
    return Node(op=OP_CONST, params={"value": value})
