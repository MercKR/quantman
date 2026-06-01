"""WTI 원시 OHLCV 프레임 정제.

입력: 플랫폼 데이터 캐시(get_raw_dataset)의 원시 프레임 — Date 인덱스(또는 date/Date
컬럼) + OHLCV(대/소문자 무관). 출력: 백테스트 엔진이 기대하는 표준 형식
(date 컬럼[datetime, ASC] + open/high/low/close/volume[float]).

정제: 비양수 종가(예: 2020-04-20 CL=F −37.63 음수정산) 제거, 가격 NaN 행 제거.
front-month 롤 점프는 보존(현물 아님 — UI에서 명시). fallback 데이터는 두지 않는다.
"""
from __future__ import annotations

import pandas as pd

REQUIRED = ("open", "high", "low", "close")


def prepare_wti(raw: pd.DataFrame) -> pd.DataFrame:
    if raw is None or len(raw) == 0:
        raise ValueError("WTI 원시 데이터 비어있음")

    df = raw.copy()
    # Date 인덱스를 컬럼으로
    if "date" not in (c.lower() for c in df.columns):
        df = df.reset_index()
    # 컬럼명 소문자 정규화
    df.columns = [str(c).lower() for c in df.columns]
    if "index" in df.columns and "date" not in df.columns:
        df = df.rename(columns={"index": "date"})

    missing = set(REQUIRED) - set(df.columns)
    if missing:
        raise ValueError(f"WTI 필수 컬럼 누락: {missing}")
    if "volume" not in df.columns:
        df["volume"] = float("nan")

    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    for c in REQUIRED:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=list(REQUIRED))
    df = df[df["close"] > 0]                       # 음수·0 정산 제거
    df = df.sort_values("date").reset_index(drop=True)
    return df[["date", "open", "high", "low", "close", "volume"]]
