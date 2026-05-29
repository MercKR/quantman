"""평가 컨텍스트 + 데이터 참조 해석 — (dates × symbols) 패널 모델.

명세 §2.2·§4. 의존: types만(순환 방지). op 모듈들이 여기서 resolve_data를 끌어 쓴다.

데이터 참조 의미론 (panel 모델, 비전 §1.1 데이터 격자):
  - "X"            (점 없음)  → 각 종목 자신의 X 패널 (예: "Close", "rsi_14")
  - "__SELF__.X"              → "X"와 동일 (각 종목 자신). UI [이 종목] 라벨용.
  - "SYM.X"        (SYM∈데이터) → SYM의 X를 전 종목에 브로드캐스트 (예: "S&P500.pct_change_1d")

이 의미론이 기존 build_signal_mask의 current_symbol 치환과 일치한다:
한 종목 마스크가 필요하면 패널을 평가한 뒤 그 종목 컬럼을 select_symbol로 뽑는다.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

SELF = "__SELF__"


@dataclass
class EvalContext:
    """평가 1회의 환경. dataset + 마스터 타임라인 + 무결성 파라미터."""

    data: dict[str, pd.DataFrame]
    master_idx: pd.DatetimeIndex
    symbols: list[str]
    # 무결성(P0-6에서 채움) — delay: 신호 평가 후 며칠 뒤 체결 가정.
    delay: int = 0

    @classmethod
    def from_dataset(cls, data: dict[str, pd.DataFrame], delay: int = 0) -> "EvalContext":
        dates: set = set()
        for df in data.values():
            if df is not None and not df.empty:
                dates.update(df.index)
        idx = pd.DatetimeIndex(sorted(dates))
        return cls(data=data, master_idx=idx, symbols=list(data.keys()), delay=delay)


def _col(df: pd.DataFrame, name: str) -> str | None:
    """대소문자 미구분 컬럼 조회."""
    if name in df.columns:
        return name
    low = {c.lower(): c for c in df.columns}
    return low.get(name.lower())


def _matrix(indic: str, ctx: EvalContext) -> pd.DataFrame:
    """지표 indic을 (dates × symbols) 패널로 — 각 종목 자신의 값."""
    out: dict = {}
    for s in ctx.symbols:
        df = ctx.data[s]
        col = _col(df, indic) if (df is not None and not df.empty) else None
        out[s] = (df[col].reindex(ctx.master_idx) if col is not None
                  else pd.Series(np.nan, index=ctx.master_idx))
    return pd.DataFrame(out, index=ctx.master_idx)


def resolve_data(ref: str, ctx: EvalContext) -> pd.DataFrame:
    """데이터 참조 문자열을 패널로 해석."""
    if "." in ref:
        sym, indic = ref.split(".", 1)
        if sym == SELF:
            return _matrix(indic, ctx)
        if sym in ctx.data:
            df = ctx.data[sym]
            col = _col(df, indic) if (df is not None and not df.empty) else None
            series = (df[col].reindex(ctx.master_idx) if col is not None
                      else pd.Series(np.nan, index=ctx.master_idx))
            return pd.DataFrame({s: series for s in ctx.symbols}, index=ctx.master_idx)
    return _matrix(ref, ctx)


def select_symbol(panel, sym: str):
    """패널에서 한 종목 컬럼(Series)을 뽑는다. 스칼라/시리즈면 그대로."""
    if isinstance(panel, pd.DataFrame):
        return panel[sym]
    return panel


def as_bool_panel(x):
    """조건 출력 정규화 — NaN→False, bool dtype."""
    if isinstance(x, pd.DataFrame):
        return x.fillna(False).astype(bool)
    if isinstance(x, pd.Series):
        return x.fillna(False).astype(bool)
    return x
