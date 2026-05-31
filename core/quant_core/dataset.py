"""
데이터셋 로딩 헬퍼.

저장된 parquet → 지표 계산까지 끝낸 dict[symbol, DataFrame]를 반환한다.
백테스트 엔진과 분석 엔진이 곧바로 받을 수 있는 형태.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from .data_fetcher import _parquet_path, load_all, load_fund_all
from .parquet_io import read_parquet_safe
from .indicators import compute_all


def load_dataset(with_indicators: bool = True) -> dict[str, pd.DataFrame]:
    """전체 심볼을 로드한다. with_indicators=True면 지표 컬럼까지 계산해 반환.

    server 백테스트·preview용 — full universe(~4468) 필요. 로컬 실행 경로는
    load_dataset_for(부분집합)을 쓴다.
    """
    raw = load_all()
    if not with_indicators:
        return raw
    funds = load_fund_all()
    return {sym: compute_all(df, funds.get(sym)) for sym, df in raw.items()}


def load_dataset_for(symbols: Iterable[str],
                     with_indicators: bool = True) -> dict[str, pd.DataFrame]:
    """주어진 심볼만 로드 — 로컬 cycle/intraday loop처럼 소수 종목만 필요할 때.

    디스크엔 server bundle로 받은 전체 parquet(~4468)이 있으나, 로컬 실행 경로는
    실제 쓰는 종목(macro ∪ 전략타겟/후보 ∪ 보유 ∪ 조건참조, ~수십개)만 읽고
    지표 계산한다. 전체 load_dataset은 4468종목 지표 계산에 실측 5분+ 걸려 cycle
    시작을 지연시켰다(2026-05-29 미장·국장 catch-up 모두 관측). 부분집합 로드로
    수초로 단축.

    load_dataset과 동일하게 with_indicators=True면 compute_all로 지표 계산 —
    결과 DataFrame은 full universe 로드 때와 종목별로 byte 단위 동일(같은 parquet·
    같은 compute_all). 디스크에 없는 심볼은 조용히 skip(load_all과 동일 동작).
    """
    wanted = set(symbols)
    raw: dict[str, pd.DataFrame] = {}
    for sym in wanted:
        p = _parquet_path(sym)
        if not p.exists():
            continue
        df = read_parquet_safe(p)      # 손상 파일은 격리·skip(load_all과 동일 동작)
        if df is not None:
            raw[sym] = df
    if not with_indicators:
        return raw
    # funds: 사용자 종목 펀더멘털만(소량). load_dataset과 동일하게 .get(sym) 매칭.
    funds = load_fund_all()
    return {sym: compute_all(df, funds.get(sym)) for sym, df in raw.items()}
