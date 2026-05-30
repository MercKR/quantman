"""펀더멘털 공유 계산 — 소스(SEC/OpenDART)와 무관한 raw 분기재무 → fund_df 변환.

소스 어댑터(fundamental_us·fundamental_kr)는 각자 분기 raw 필드를 정규화해 이 함수에 넘긴다.
출력 fund_df는 기존 yfinance 경로와 **동일 컬럼**이라 indicators.add_fundamentals가 그대로 소비
(엔진 수정 0). 인덱스는 as_of(실 공시/제출일) — yfinance의 고정 45일 lag 대신 진짜 PIT.

raw 필드(분기별 dict): end·as_of(date) + 손익(rev·gp·ebit·ebitda·ni·fcf) + 재무상태(ta·tl·ca·cl·
cash·re·td·eq). flow는 TTM 합(가용 분기수로 연율화), stock은 시점값. shares는 현행 발행주식수(스칼라).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# fund_df 출력 컬럼 — add_fundamentals가 소비하는 계약(추가/삭제 시 동기화 필요).
OUTPUT_COLS = [
    "gross_margin", "op_margin", "net_debt_ebitda", "roic",
    "ttm_rev", "ttm_ebit", "ttm_ebitda", "ttm_ni", "ttm_fcf",
    "total_debt", "cash", "total_assets", "total_liabilities",
    "working_capital", "retained_earnings", "stockholders_equity", "shares_outstanding",
    "z_wc_ta", "z_re_ta", "z_ebit_ta", "z_tl", "z_rev_ta",
]


def _sd(a, b):
    """안전 나눗셈 — 0/NaN이면 NaN."""
    if pd.isna(a) or pd.isna(b) or b == 0:
        return np.nan
    return a / b


def compute_fundamentals(periods: list[dict], shares_outstanding: float = float("nan"),
                         quarterly: bool = True) -> pd.DataFrame:
    """raw 행(period_end 오름차순) → as_of 인덱스 fund_df.

    quarterly=True(SEC·yfinance): flow는 직전 ≤4분기 합 × (4/분기수)로 TTM 연율화.
    quarterly=False(OpenDART 연간): flow 입력이 이미 연간(=TTM)이라 그 값을 그대로 사용.
    발행주식수: 행별 p["shares"](PIT 시계열) 우선, 없으면 shares_outstanding(스칼라 폴백).
    """
    rows: list[dict] = []
    idx: list = []
    for i, p in enumerate(periods):
        window = periods[max(0, i - 3): i + 1]      # 최대 4분기 (TTM)

        def ttm(key: str, _p=p, _w=window) -> float:
            if not quarterly:                        # 연간 입력 — 값 자체가 TTM
                v = _p.get(key)
                return v if (v is not None and not pd.isna(v)) else np.nan
            vals = [w[key] for w in _w if w.get(key) is not None and not pd.isna(w.get(key))]
            return sum(vals) * (4.0 / len(vals)) if vals else np.nan

        rev, gp, ebit = p.get("rev"), p.get("gp"), p.get("ebit")
        ta, tl, ca, cl = p.get("ta"), p.get("tl"), p.get("ca"), p.get("cl")
        cash, re, td, eq = p.get("cash"), p.get("re"), p.get("td"), p.get("eq")

        t_rev, t_ebit = ttm("rev"), ttm("ebit")
        t_ebitda, t_ni, t_fcf = ttm("ebitda"), ttm("ni"), ttm("fcf")
        eff_ebitda = t_ebitda if not pd.isna(t_ebitda) else t_ebit

        wc = (ca - cl) if not (pd.isna(ca) or pd.isna(cl)) else np.nan
        net_debt = (td - cash) if not (pd.isna(td) or pd.isna(cash)) else np.nan
        td_safe = 0.0 if pd.isna(td) else td
        cash_safe = 0.0 if pd.isna(cash) else cash
        ic = (eq + td_safe - cash_safe) if not pd.isna(eq) else np.nan
        nopat = t_ebit * 0.80 if not pd.isna(t_ebit) else np.nan

        rows.append({
            "gross_margin": _sd(gp, rev) * 100,
            "op_margin": _sd(ebit, rev) * 100,
            "net_debt_ebitda": _sd(net_debt, eff_ebitda),
            "roic": _sd(nopat, ic) * 100,
            "ttm_rev": t_rev, "ttm_ebit": t_ebit, "ttm_ebitda": eff_ebitda,
            "ttm_ni": t_ni, "ttm_fcf": t_fcf,
            "total_debt": td, "cash": cash, "total_assets": ta, "total_liabilities": tl,
            "working_capital": wc, "retained_earnings": re, "stockholders_equity": eq,
            "shares_outstanding": (p["shares"] if p.get("shares") is not None
                                   and not pd.isna(p.get("shares")) else shares_outstanding),
            "z_wc_ta": _sd(wc, ta), "z_re_ta": _sd(re, ta), "z_ebit_ta": _sd(t_ebit, ta),
            "z_tl": tl, "z_rev_ta": _sd(t_rev, ta),
        })
        idx.append(pd.to_datetime(p["as_of"]))

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, index=pd.DatetimeIndex(idx))
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df = df.sort_index()
    return df[~df.index.duplicated(keep="last")]    # as_of 중복 제거(reindex ffill 호환)
