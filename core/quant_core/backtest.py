"""백테스트 공유 헬퍼.

통합 IR 백테스트 엔진(ir_engine/)이 임포트하는 비용 default·빈 결과·성과지표
계산을 단일 출처로 제공한다. operand(레거시 "전략 만들기") 백테스트 엔진은
제거됐고, IR 엔진이 이 모듈의 헬퍼를 재사용한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .exec_defaults import DEFAULT_EXECUTION

TRADING_DAYS = 252

# CM-01 — 백테스트 비용 default는 ExecutionPolicy 단일 출처에서 끌어온다.
_DEFAULT_COMMISSION = DEFAULT_EXECUTION["bt_commission_bps"] / 10_000.0
_DEFAULT_SLIPPAGE = DEFAULT_EXECUTION["bt_slippage_bps"] / 10_000.0
_DEFAULT_SELL_TAX = DEFAULT_EXECUTION["bt_sell_tax_bps"] / 10_000.0

# 동시 보유 전역 한도 (frontend `screener_limit` cap·`max_concurrent` 제거 정책과 정합).
_MAX_POSITIONS_GLOBAL = 30


@dataclass
class _PortPosition:
    """다종목 포지션 상태 — IR 포트폴리오 백테스트 루프(ir_engine.backtest)가 재사용."""
    shares: float
    entry_price: float
    entry_i: int
    peak_high: float
    peak_close: float
    executed_rules: set = field(default_factory=set)


def _empty(error: str) -> dict:
    return {"success": False, "error": error}


def _metrics(equity: pd.Series, benchmark: pd.Series, trades_df: pd.DataFrame) -> dict:
    def _stats(curve: pd.Series):
        first, last = float(curve.iloc[0]), float(curve.iloc[-1])
        total = (last - first) / first * 100
        years = len(curve) / TRADING_DAYS
        cagr = ((last / first) ** (1 / years) - 1) * 100 if years > 0 and last > 0 else np.nan
        peak = curve.cummax()
        mdd = ((curve - peak) / peak).min() * 100
        return total, cagr, mdd

    s_total, s_cagr, s_mdd = _stats(equity)
    b_total, b_cagr, b_mdd = _stats(benchmark)

    daily = equity.pct_change().dropna()
    sharpe = (daily.mean() / daily.std() * np.sqrt(TRADING_DAYS)
              if daily.std() and daily.std() > 0 else np.nan)

    n_trades = len(trades_df)
    if n_trades:
        win_rate = (trades_df["수익률(%)"] > 0).mean() * 100
        avg_hold = trades_df["보유일"].mean()
        avg_ret = trades_df["수익률(%)"].mean()
    else:
        win_rate = avg_hold = avg_ret = np.nan

    return {
        "total_return": s_total, "cagr": s_cagr, "mdd": s_mdd,
        "sharpe": sharpe, "n_trades": n_trades, "win_rate": win_rate,
        "avg_hold": avg_hold, "avg_trade_return": avg_ret,
        "bench_total": b_total, "bench_cagr": b_cagr, "bench_mdd": b_mdd,
        "excess_return": s_total - b_total,
    }
