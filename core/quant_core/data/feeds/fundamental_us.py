"""fundamental.equity (US) 피드 — SEC EDGAR Company Facts (filing-date PIT).

us-gaap XBRL 개념을 분기 raw 필드로 정규화해 compute_fundamentals에 넘긴다. yfinance(45일 고정lag)
대체 — as_of=실 제출일(filed)이라 진짜 point-in-time. ticker→CIK는 company_tickers.json로 매핑.

SEC 손익 항목은 분기(3mo)·누적(6/9mo)·연간(12mo)이 섞여 있어, 누적값 차분으로 순수 분기값을 복원한다
(Q2=YTD2−YTD1 …). 재무상태(instant) 항목은 분기말 시점값 그대로. 무키 — User-Agent 헤더만 필수.

저장: 기존 yfinance 경로와 동일 parquet 포맷(FUNDAMENTALS_DIR/{ticker}.parquet) → load_fund_all 소비.
"""

from __future__ import annotations

import datetime as _dt
import os
from collections import defaultdict
from typing import Optional

import requests

from ..manifest import default_manifest_path
from .fundamentals_common import compute_fundamentals
from ...parquet_io import write_parquet_atomic

_UA = os.environ.get("SEC_USER_AGENT", "quant-platform research eogkrvlfrl@gmail.com")
_HEADERS = {"User-Agent": _UA}
_FORMS = ("10-Q", "10-K", "10-Q/A", "10-K/A")

# us-gaap 개념 별칭(첫 존재 항목 사용). EBITDA는 직접 태그 없음 → compute가 EBIT로 대체.
_FLOW = {
    "rev": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"],
    "gp": ["GrossProfit"],
    "ebit": ["OperatingIncomeLoss"],
    "ni": ["NetIncomeLoss"],
    "ocf": ["NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
}
_STOCK = {
    "ta": ["Assets"], "tl": ["Liabilities"], "ca": ["AssetsCurrent"], "cl": ["LiabilitiesCurrent"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue",
             "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
    "re": ["RetainedEarningsAccumulatedDeficit"],
    "td": ["LongTermDebtNoncurrent", "LongTermDebt", "DebtLongtermAndShorttermCombinedAmount"],
    "eq": ["StockholdersEquity"],
}

_ticker_cik: Optional[dict] = None


def _cik_map() -> dict:
    global _ticker_cik
    if _ticker_cik is None:
        r = requests.get("https://www.sec.gov/files/company_tickers.json",
                         headers=_HEADERS, timeout=30)
        r.raise_for_status()
        _ticker_cik = {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in r.json().values()}
    return _ticker_cik


def _usd(gaap: dict, aliases: list[str]) -> list[dict]:
    for a in aliases:
        u = gaap.get(a, {}).get("units", {}).get("USD")
        if u:
            return u
    return []


def _quarterly(points: list[dict]) -> dict:
    """누적·분기 손익 포인트 → 순수 분기값. 반환 {end(YYYY-MM-DD): {"val", "filed"}}.

    SEC는 같은 분기를 직접 3개월값과 누적(YTD)값으로 동시 제공하고, 후속 공시에 직전 분기를
    비교표시로 재게시한다. 그래서:
      1) (start,end) 기간으로 중복제거 — 재게시는 최신 filed 채택.
      2) 직접 3개월 포인트(기간≈1분기)는 분기값 그대로 사용(차분오차 없음·우선).
      3) 남는 분기는 **같은 회계연도(=동일 start) 누적 차분**으로 복원(Qk=YTDk−YTD(k-1), Q4=연간−9M).
    회계연도를 SEC `fy` 태그가 아니라 실제 기간 start로 식별 — fy 태그 오류로 같은 end가 여러
    (fy,분기)로 덮어써져 분기가 누락되던 결함(대형주 비교재게시)을 근본 차단한다.
    """
    DAYS_Q = 91.3
    by_period: dict = {}                         # (start,end) → point. 재게시는 최신 filed.
    for p in points:
        if not (p.get("start") and p.get("end") and p.get("filed")) or p.get("form") not in _FORMS:
            continue                             # filed 없으면 PIT 불가 → 제외
        key = (p["start"][:10], p["end"][:10])
        cur = by_period.get(key)
        if cur is None or p["filed"] > cur["filed"]:
            by_period[key] = p

    def _qn(s: str, e: str) -> int:
        return round((_dt.date.fromisoformat(e) - _dt.date.fromisoformat(s)).days / DAYS_Q)

    out: dict = {}
    # (2) 직접 3개월 포인트 — 분기값 그대로(우선).
    for (s, e), p in by_period.items():
        if _qn(s, e) == 1:
            out[e] = {"val": float(p["val"]), "filed": p["filed"][:10]}

    # (3) 회계연도(동일 start)별 누적 차분으로 미충족 분기(Q2~Q4) 복원.
    by_start: dict = defaultdict(dict)           # start → {누적분기번호 1..4: point}
    for (s, e), p in by_period.items():
        qn = _qn(s, e)
        if qn in (1, 2, 3, 4):
            by_start[s][qn] = p
    for by_qn in by_start.values():
        for qn, p in by_qn.items():
            e = p["end"][:10]
            if qn < 2 or e in out:               # 직접값 우선
                continue
            prev = by_qn.get(qn - 1)
            if prev is None:
                continue                         # 직전 누적 없음 → 복원 불가
            out[e] = {"val": float(p["val"] - prev["val"]), "filed": p["filed"][:10]}
    return out


def _instant(points: list[dict]) -> dict:
    """시점(instant) 재무상태 포인트 → {end: {"val","filed"}}. start 있는 flow는 제외."""
    out: dict = {}
    for p in points:
        if p.get("start") or not p.get("end") or not p.get("filed"):
            continue                             # filed 없으면 PIT 불가 → 제외
        e = p["end"][:10]
        cur = out.get(e)
        if cur is None or p["filed"] > cur["filed"]:
            out[e] = {"val": float(p["val"]), "filed": p["filed"][:10]}
    return out


def fetch_one(ticker: str) -> "object":
    """단일 US 티커의 SEC 펀더멘털 → fund_df(as_of 인덱스). 데이터 없으면 빈 DataFrame."""
    import pandas as pd

    cik = _cik_map().get(ticker.upper())
    if not cik:
        return pd.DataFrame()
    r = requests.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
                     headers=_HEADERS, timeout=30)
    if r.status_code != 200:
        return pd.DataFrame()
    facts = r.json().get("facts", {})
    gaap = facts.get("us-gaap", {})

    flow_q = {k: _quarterly(_usd(gaap, al)) for k, al in _FLOW.items()}
    stock_q = {k: _instant(_usd(gaap, al)) for k, al in _STOCK.items()}

    # shares — dei 발행주식수 최신값(스칼라)
    shares = float("nan")
    dei = facts.get("dei", {}).get("EntityCommonStockSharesOutstanding", {}).get("units", {}).get("shares", [])
    if dei:
        shares = float(max(dei, key=lambda p: p.get("filed", ""))["val"])

    ends = sorted(flow_q["rev"].keys() | flow_q["ni"].keys())   # 손익이 있는 분기말
    periods: list[dict] = []
    for e in ends:
        def fv(k):
            d = flow_q[k].get(e)
            return d["val"] if d else None

        def sv(k):
            d = stock_q[k].get(e)
            return d["val"] if d else None

        ocf, capex = fv("ocf"), fv("capex")
        fcf = (ocf - capex) if (ocf is not None and capex is not None) else None
        fileds = [flow_q["rev"].get(e, {}).get("filed"), flow_q["ni"].get(e, {}).get("filed")]
        as_of = max([f for f in fileds if f] or [e])      # 보수적 — 가장 늦은 제출일
        periods.append({
            "end": e, "as_of": as_of,
            "rev": fv("rev"), "gp": fv("gp"), "ebit": fv("ebit"), "ebitda": None,
            "ni": fv("ni"), "fcf": fcf,
            "ta": sv("ta"), "tl": sv("tl"), "ca": sv("ca"), "cl": sv("cl"),
            "cash": sv("cash"), "re": sv("re"), "td": sv("td"), "eq": sv("eq"),
        })
    return compute_fundamentals(periods, shares)


def _fund_path(code: str):
    return default_manifest_path().parent / "fundamentals" / f"{code.replace('/', '_')}.parquet"


def fetch(tickers: list[str], throttle: float = 0.12) -> dict:
    """US 티커들의 SEC 펀더멘털 수급 → parquet 저장. SEC ~10req/s 준수(throttle)."""
    import time
    n_ok = n_empty = n_fail = 0
    for t in tickers:
        try:
            df = fetch_one(t)
        except Exception:
            n_fail += 1
            if throttle:
                time.sleep(throttle)
            continue
        if df is None or df.empty:
            n_empty += 1
        else:
            p = _fund_path(t)
            write_parquet_atomic(df, p)        # 원자적 — 중단 시 잘린 파일 안 남김
            n_ok += 1
        if throttle:
            time.sleep(throttle)
    return {"ok": n_ok, "empty": n_empty, "fail": n_fail}
