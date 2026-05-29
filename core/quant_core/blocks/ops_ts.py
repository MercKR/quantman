"""축2a — 단일 시계열 블록. expression_parser 순수함수를 재사용(재사용 우선 원칙).

명세 §3 축2a. 기존 history 피연산자(mean/max/min/lag/percentile)는 이 ts_* 블록으로
완전히 포섭된다(history mean→ts_mean, lag→ts_delay, percentile→ts_percentile).
"""

from __future__ import annotations

from ..expression_parser import (
    ts_arg_max, ts_arg_min, ts_decay_linear, ts_delay, ts_delta, ts_max,
    ts_mean, ts_min, ts_rank, ts_std_dev, ts_sum, ts_zscore,
)
from .catalog import BlockDef, register
from .types import ValueType


def _ts(op: str, fn, doc: str) -> None:
    """(panel, window) 시그니처 시계열 함수를 블록으로 등록. window 기본 20(규칙5)."""
    def ev(resolved, params, ctx):
        return fn(resolved["signal"], int(params.get("window", 20)))
    register(BlockDef(op, ValueType.SCORE, ev, slots={"signal": ValueType.SCORE},
                      param_defaults={"window": 20}, doc=doc))


_ts("ts_mean", ts_mean, "최근 N일 평균")
_ts("ts_sum", ts_sum, "최근 N일 합")
_ts("ts_std", ts_std_dev, "최근 N일 표준편차(산포)")
_ts("ts_delta", ts_delta, "N일 전 대비 변화량")
_ts("ts_delay", ts_delay, "N일 전 값")
_ts("ts_rank", ts_rank, "윈도우 내 위치(롤링 백분위)")
_ts("ts_zscore", ts_zscore, "롤링 z-score")
_ts("ts_decay", ts_decay_linear, "시간가중 평활(최근일 가중↑)")
_ts("ts_max", ts_max, "최근 N일 최댓값")
_ts("ts_min", ts_min, "최근 N일 최솟값")
_ts("ts_argmax", ts_arg_max, "최고치 발생 후 경과일")
_ts("ts_argmin", ts_arg_min, "최저치 발생 후 경과일")


def _ev_ts_percentile(resolved, params, ctx):
    """최근 N일 롤링 백분위값 (기존 history percentile 포섭)."""
    x = resolved["signal"]
    d = int(params.get("window", 20))
    q = float(params.get("percentile", 50)) / 100.0
    return x.rolling(d).quantile(min(max(q, 0.0), 1.0))


register(BlockDef("ts_percentile", ValueType.SCORE, _ev_ts_percentile,
                  slots={"signal": ValueType.SCORE},
                  param_defaults={"window": 20, "percentile": 50},
                  doc="최근 N일 롤링 백분위값"))
