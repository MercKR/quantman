"""무결성 게이트 (비전 §6) — 백테스트 신뢰성 강제. 이 시스템의 최대 차별점.

명세 §6. 두 종류:
  데이터 시점 무결성  — 그 시점에 알 수 있던 데이터만 쓰는가 (delay·PIT·생존편향)
  파라미터 시점 무결성 — 기준값을 미래 정보로 정하지 않았나 (causal 연산만 허용)

Phase 0는 골격: 핵심 look-ahead 가드(apply_delay)는 실동작하고, PIT·생존편향은
데이터 레이어(Phase 3)가 채울 DatasetMeta 훅으로 검사한다. 무결성 이슈는
validate의 SEV_INTEGRITY로 최우선 표시된다(편의보다 무결성 우선).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..indicators import FUND_INDICATOR_COLS
from .node import OP_DATA, Node
from .validate import SEV_INTEGRITY, Issue

_FUND_SET = set(FUND_INDICATOR_COLS)

# 미래(당일 이후)를 참조하는 비-causal 블록. 현재 카탈로그는 전부 causal(롤링·shift·
# 당일 횡단)이라 비어 있다. forward-looking 블록 추가 시 여기 등록 → 오용을 게이트가 차단.
NON_CAUSAL_OPS: frozenset[str] = frozenset()


@dataclass
class DatasetMeta:
    """dataset의 무결성 속성. 데이터 레이어(Phase 3)가 실제 값으로 채운다."""

    has_pit: bool = False                  # 펀더멘털·추정치 발표일 기반 PIT 태깅
    has_membership_history: bool = False   # 지수 구성 이력(생존편향 방지)
    delay: int = 1                         # 신호→체결 지연(거래일). 1=익일.


# ── look-ahead 가드 (실동작) ──────────────────────────────────────────────────

def apply_delay(value, delay: int):
    """신호를 delay 거래일 만큼 미뤄 당일 정보로 당일 체결하는 look-ahead를 막는다.

    백테스트가 신호 패널/시리즈를 포지션으로 옮기기 직전에 적용한다.
    """
    if delay and delay > 0 and hasattr(value, "shift"):
        return value.shift(delay)
    return value


# ── 파라미터 시점 무결성 ──────────────────────────────────────────────────────

def param_time_issues(node: Node) -> list[Issue]:
    """비-causal(미래 참조) 블록 사용을 검출."""
    issues: list[Issue] = []

    def walk(n: Node, path: str) -> None:
        if n.op in NON_CAUSAL_OPS:
            issues.append(Issue("R4", SEV_INTEGRITY,
                                f"미래 참조 블록: {n.op} — 롤링/causal 연산만 허용", path))
        for slot, child in n.inputs.items():
            walk(child, f"{path}/{slot}")

    walk(node, "root")
    return issues


# ── 데이터 시점 무결성 ────────────────────────────────────────────────────────

def _referenced_indicators(node: Node) -> set[str]:
    out: set[str] = set()

    def walk(n: Node) -> None:
        if n.op == OP_DATA:
            ref = str(n.params.get("ref", ""))
            out.add(ref.split(".", 1)[1] if "." in ref else ref)
        for child in n.inputs.values():
            walk(child)

    walk(node)
    return out


def data_time_issues(node: Node, meta: DatasetMeta) -> list[Issue]:
    """delay·PIT 무결성. PIT 경고는 펀더멘털을 실제 참조할 때만 발동(노이즈 방지)."""
    issues: list[Issue] = []
    if meta.delay < 1:
        issues.append(Issue("R4", SEV_INTEGRITY,
                            "delay<1 — 당일 종가로 당일 체결은 look-ahead. delay>=1 권장"))
    if not meta.has_pit and (_referenced_indicators(node) & _FUND_SET):
        issues.append(Issue("R4", SEV_INTEGRITY,
                            "펀더멘털 지표 사용 + PIT 미태깅 — 미래 실적 누출 위험(Phase 3)"))
    return issues


def integrity_issues(node: Node, meta: DatasetMeta | None = None) -> list[Issue]:
    """전체 무결성 이슈(파라미터 시점 + 데이터 시점). 전부 SEV_INTEGRITY."""
    out = param_time_issues(node)
    if meta is not None:
        out += data_time_issues(node, meta)
    return out
