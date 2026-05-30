"""성과 지표 보강 (비전 §3.4 조합 프리셋) — 명명 지표만 추가, 블록 대수는 안 함.

기존 _metrics(total/cagr/mdd/sharpe/winrate/avghold/avgret/bench/excess)에
Sortino·Calmar·VaR·CVaR·Profit Factor·beta를 더한다.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252

# 모든 펼침 버킷이 공유하는 정규 지표 키 — 동질성 보장(한 곳에서만 정의).
PERF_KEYS = ("n", "mean", "std", "sharpe", "sortino", "cum_return", "cagr",
             "mdd", "win_rate", "payoff_ratio", "profit_factor", "var_95", "cvar_95")


def perf_from_returns(returns: pd.Series, *, periods_per_year: int = TRADING_DAYS) -> dict:
    """일별 수익률 한 줄기 → 정규 성과지표. **모든 펼침 버킷의 단일 출처.**

    경로(자산곡선 복원)·분포만으로 산출하므로 벤치마크·거래내역이 필요 없다 —
    파라미터/자산/조건/기간분할 버킷이 전부 동일 키로 비교 가능해진다(갭 A의 근본해결).
    조건 국면처럼 불연속 일자도 주어진 순서대로 복리해 sub-equity를 만들어 MDD/CAGR를
    "그 국면에 있는 동안의 성과"로 정의한다. 백분율 규약은 finalize_metrics와 일치.
    """
    r = returns.dropna() if isinstance(returns, pd.Series) else pd.Series(returns).dropna()
    n = int(len(r))
    if n == 0:
        return {k: (0 if k == "n" else np.nan) for k in PERF_KEYS}
    arr = r.to_numpy(dtype=float)
    mean, std = float(arr.mean()), float(arr.std())
    sharpe = mean / std * np.sqrt(periods_per_year) if std > 0 else np.nan
    downside = arr[arr < 0]
    dstd = float(downside.std()) if len(downside) else 0.0
    sortino = mean / dstd * np.sqrt(periods_per_year) if dstd > 0 else np.nan

    equity = np.cumprod(1.0 + arr)
    cum = float(equity[-1] - 1.0)
    years = n / periods_per_year
    cagr = (float(equity[-1] ** (1.0 / years) - 1.0)
            if years > 0 and equity[-1] > 0 else np.nan)
    peak = np.maximum.accumulate(equity)
    mdd = float(((equity - peak) / peak).min())

    wins, losses = arr[arr > 0], arr[arr < 0]
    win_rate = float((arr > 0).mean())
    payoff = (float(wins.mean()) / abs(float(losses.mean()))
              if len(wins) and len(losses) and losses.mean() != 0 else np.nan)
    pf = (float(wins.sum()) / abs(float(losses.sum()))
          if len(losses) and losses.sum() != 0 else np.nan)
    var = float(np.quantile(arr, 0.05))
    tail = arr[arr <= var]
    cvar = float(tail.mean()) if len(tail) else np.nan
    return {
        "n": n, "mean": mean * 100, "std": std * 100, "sharpe": sharpe,
        "sortino": sortino, "cum_return": cum * 100, "cagr": cagr * 100 if cagr == cagr else np.nan,
        "mdd": mdd * 100, "win_rate": win_rate * 100, "payoff_ratio": payoff,
        "profit_factor": pf, "var_95": var * 100,
        "cvar_95": cvar * 100 if cvar == cvar else np.nan,
    }


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
