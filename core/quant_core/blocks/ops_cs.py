"""축3 횡단 + 축4 그룹 + 변환 — expression_parser 순수함수 재사용.

명세 §3 축3·축4. 기존 조건 문법엔 없던 연산. alpha 수식 엔진(ExpressionParser)에만
있던 것을 타입드 블록으로 승격해 문장으로 노출한다.
"""

from __future__ import annotations

from ..expression_parser import (
    cs_normalize, cs_scale, cs_zscore, group_neutralize, hump,
)
from .catalog import BlockDef, register
from .types import ValueType


def _cs(op: str, fn, doc: str) -> None:
    """(panel) → panel 횡단 함수를 블록으로 등록. PANEL 형태 입력 필요(규칙2)."""
    def ev(resolved, params, ctx):
        return fn(resolved["signal"])
    register(BlockDef(op, ValueType.SCORE, ev, slots={"signal": ValueType.SCORE},
                      requires_panel=True, doc=doc))


def _ev_rank(resolved, params, ctx):
    """횡단 순위 — unit·descending로 일반화한 단일 프리미티브.

    unit="pct"(0~1 분위) | "count"(1·2·3… 개수). descending=큰 값이 1위(상위).
    동순위는 method="first"로 결정적 분해. 기본(pct·오름차순)은 cs_rank와 수치 동일
    → 기존 팩터 알파 무영향. 선별은 compare로: 상위 50개=rank(…,count,desc)≤50,
    상위 10%=rank(…,pct,desc)≤0.1 (큰 값이 1위→낮은 분위가 상위)."""
    x = resolved["signal"]
    pct = params.get("unit", "pct") != "count"
    ascending = not bool(params.get("descending", False))
    return x.rank(axis=1, pct=pct, ascending=ascending, method="first")


register(BlockDef("rank", ValueType.SCORE, _ev_rank, slots={"signal": ValueType.SCORE},
                  param_defaults={"unit": "pct", "descending": False},
                  requires_panel=True,
                  doc="횡단 순위 — 분위(0~1) 또는 개수(1·2·3), 큰/작은 값 기준 선택"))
_cs("zscore", cs_zscore, "횡단 표준화(평균0·표준편차1)")
_cs("normalize", cs_normalize, "횡단 평균 차감(평균0)")
_cs("scale", cs_scale, "절대 비중합=1 스케일")


def _ev_winsorize(resolved, params, ctx):
    """횡단 이상치 클립 — 매 날짜 [lower%, upper%] 분위로 극단값 절단(목적태그)."""
    x = resolved["signal"]
    lo = float(params.get("lower", 5)) / 100.0
    hi = float(params.get("upper", 95)) / 100.0
    ql = x.quantile(lo, axis=1)
    qh = x.quantile(hi, axis=1)
    return x.clip(lower=ql, upper=qh, axis=0)


def _ev_group_neutralize(resolved, params, ctx):
    return group_neutralize(resolved["signal"], params.get("group_type", "Industry"))


def _ev_hump(resolved, params, ctx):
    return hump(resolved["signal"], float(params.get("threshold", 0.0)))


register(BlockDef("group_neutralize", ValueType.SCORE, _ev_group_neutralize,
                  slots={"signal": ValueType.SCORE},
                  param_defaults={"group_type": "Industry"}, requires_panel=True,
                  doc="동일 그룹 평균 차감(그룹 효과 제거)"))
register(BlockDef("hump", ValueType.SCORE, _ev_hump,
                  slots={"signal": ValueType.SCORE},
                  param_defaults={"threshold": 0.0}, doc="가중치 변동폭 억제(턴오버↓)"))
register(BlockDef("winsorize", ValueType.SCORE, _ev_winsorize,
                  slots={"signal": ValueType.SCORE},
                  param_defaults={"lower": 5, "upper": 95}, requires_panel=True,
                  doc="횡단 이상치 클립(분위 절단)"))
