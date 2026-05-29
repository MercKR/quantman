"""성과 지표 보강 (비전 §3.4 조합 프리셋) — 명명 지표만 추가, 블록 대수는 안 함.

기존 _metrics(total/cagr/mdd/sharpe/winrate/avghold/avgret/bench/excess)에
Sortino·Calmar·VaR·CVaR·Profit Factor·beta를 더한다.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def extra_metrics(equity: pd.Series, benchmark: pd.Series, trades_df: pd.DataFrame) -> dict:
    out: dict = {"sortino": np.nan, "var_95": np.nan, "cvar_95": np.nan,
                 "beta": np.nan, "profit_factor": np.nan}
    daily = equity.pct_change().dropna()
    if len(daily) > 1 and daily.std() and daily.std() > 0:
        downside = daily[daily < 0]
        dstd = downside.std()
        out["sortino"] = (float(daily.mean() / dstd * np.sqrt(TRADING_DAYS))
                          if dstd and dstd > 0 else np.nan)
        var = float(np.quantile(daily, 0.05))
        out["var_95"] = var * 100
        tail = daily[daily <= var]
        out["cvar_95"] = float(tail.mean() * 100) if len(tail) else np.nan
        bd = benchmark.pct_change().dropna()
        idx = daily.index.intersection(bd.index)
        if len(idx) > 2:
            bv = bd.reindex(idx)
            if bv.var() and bv.var() > 0:
                cov = float(np.cov(daily.reindex(idx), bv)[0, 1])
                out["beta"] = cov / float(bv.var())
    if trades_df is not None and len(trades_df) and "수익률(%)" in trades_df.columns:
        r = trades_df["수익률(%)"]
        wins = float(r[r > 0].sum())
        losses = float(r[r < 0].sum())
        out["profit_factor"] = wins / abs(losses) if losses < 0 else np.nan
    return out


def finalize_metrics(base: dict, equity: pd.Series, benchmark: pd.Series,
                     trades_df: pd.DataFrame) -> dict:
    """기존 metric + 보강 지표(+Calmar)를 합친 최종 metric dict."""
    m = dict(base)
    m.update(extra_metrics(equity, benchmark, trades_df))
    mdd, cagr = m.get("mdd"), m.get("cagr")
    m["calmar"] = (float(cagr / abs(mdd))
                   if (mdd and not np.isnan(mdd) and mdd != 0
                       and cagr is not None and not np.isnan(cagr)) else np.nan)
    return m
