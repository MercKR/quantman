"""1회 백테스트 — 블록 IR 신호로 구동 (단일 종목).

명세 §7. 매수/매도 신호를 새 평가기(blocks.evaluate)로 만들고, 검증된 시뮬레이션
부품(_metrics·round_to_tick)을 재사용한다. 기존 run_backtest의 단일종목 path와
비트 동일한 결과를 내도록 루프를 이식했다 — test_engine_backtest_ir로 고정.

포트폴리오/스크리너/팩터 path의 IR 통합은 후속 증분(P1-3b~).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..backtest import (
    _DEFAULT_COMMISSION, _DEFAULT_SELL_TAX, _DEFAULT_SLIPPAGE, _empty, _metrics,
)
from ..blocks import EvalContext, Node, evaluate, select_symbol
from ..exec_defaults import round_to_tick

_REASON_KEYS = (
    ("익절", "tp"), ("손절", "sl"), ("ATR트레일링", "atr"),
    ("트레일링", "trail"), ("보유기간", "hold"),
)


def _ir_mask(node: Node | None, ctx: EvalContext, sym: str, index) -> np.ndarray | None:
    """조건 Node를 평가해 sym 종목의 boolean 배열로. node None이면 None."""
    if node is None:
        return None
    panel = evaluate(node, ctx)
    series = select_symbol(panel, sym)
    return series.reindex(index, fill_value=False).fillna(False).to_numpy(dtype=bool)


def run_backtest_ir(
    dataset: dict[str, pd.DataFrame],
    trade_symbol: str,
    buy_node: Node,
    *,
    sell_node: Node | None = None,
    hold_days: int | None = None,
    take_profit: float | None = None,
    stop_loss: float | None = None,
    trail_atr_mult: float | None = None,
    trail_pct: float | None = None,
    sell_amount_pct: float = 100.0,
    rule_sell_pcts: dict | None = None,
    fill: str = "next_open",
    commission: float = _DEFAULT_COMMISSION,
    slippage: float = _DEFAULT_SLIPPAGE,
    sell_tax: float = _DEFAULT_SELL_TAX,
    currency: str = "KRW",
    initial_capital: float = 10_000_000.0,
    start=None,
    end=None,
) -> dict:
    """단일 종목 백테스트 — 매수/매도 신호를 블록 IR로 평가.

    buy_node/sell_node는 type:condition Node. 기존 run_backtest 단일 path와
    동일한 체결·청산·성과 로직을 쓴다.
    """
    if trade_symbol not in dataset or dataset[trade_symbol].empty:
        return _empty(f"'{trade_symbol}' 데이터 없음")
    trade_df = dataset[trade_symbol]
    if not {"Open", "Close"}.issubset(trade_df.columns):
        return _empty(f"'{trade_symbol}'에 시가·종가 데이터가 없습니다.")

    trade_df = trade_df.sort_index()
    if start is not None:
        trade_df = trade_df[trade_df.index >= pd.Timestamp(start)]
    if end is not None:
        trade_df = trade_df[trade_df.index <= pd.Timestamp(end)]
    trade_df = trade_df.dropna(subset=["Open", "Close"])
    if len(trade_df) < 2:
        return _empty("백테스트 기간의 가격 데이터가 부족합니다.")

    ctx = EvalContext.from_dataset(dataset)
    buy_arr = _ir_mask(buy_node, ctx, trade_symbol, trade_df.index)
    if buy_arr is None:
        return _empty("매수 신호가 비었습니다.")
    sell_arr = _ir_mask(sell_node, ctx, trade_symbol, trade_df.index)

    dates = trade_df.index
    opens = trade_df["Open"].to_numpy(dtype=float)
    closes = trade_df["Close"].to_numpy(dtype=float)
    highs = (trade_df["High"].to_numpy(dtype=float)
             if "High" in trade_df.columns else closes)
    atr_arr = (trade_df["atr_14"].to_numpy(dtype=float)
               if "atr_14" in trade_df.columns else None)
    if trail_atr_mult is not None and atr_arr is None:
        return _empty(f"'{trade_symbol}'에 ATR 지표가 없어 ATR 트레일링을 쓸 수 없습니다.")
    n = len(trade_df)
    next_open = (fill == "next_open")

    cash = float(initial_capital)
    shares = 0.0
    position = False
    entry_price = 0.0
    entry_i = -1
    peak_high = 0.0
    peak_close = 0.0
    pending_buy = False
    pending_sell = False
    pending_reason = ""
    executed_rules: set[str] = set()
    rule_pcts = rule_sell_pcts or {}

    def _sell_pct_of(reason: str) -> float:
        if not reason:
            return float(sell_amount_pct)
        for needle, key in _REASON_KEYS:
            if needle in reason:
                v = rule_pcts.get(key)
                return float(v) if v is not None else float(sell_amount_pct)
        return float(sell_amount_pct)

    def _reason_key(reason: str) -> str | None:
        for needle, key in _REASON_KEYS:
            if needle in reason:
                return key
        return None

    trades: list[dict] = []
    equity = np.empty(n, dtype=float)

    def _open(i: int, raw_price: float):
        nonlocal cash, shares, position, entry_price, entry_i, peak_high, peak_close
        slipped = raw_price * (1 + slippage)
        price = round_to_tick(slipped, direction="up", currency=currency)
        if price <= 0:
            return
        per_share_cost = price * (1 + commission)
        new_shares = int(cash // per_share_cost)
        if new_shares <= 0:
            return
        shares = float(new_shares)
        cash -= shares * per_share_cost
        entry_price = price
        entry_i = i
        peak_high = highs[i]
        peak_close = closes[i]
        position = True
        executed_rules.clear()

    def _close(i: int, raw_price: float, reason: str, sell_pct: float = 100.0):
        nonlocal cash, shares, position
        if shares <= 0:
            return
        sell_pct = max(0.0, min(100.0, float(sell_pct)))
        if sell_pct <= 0:
            return
        slipped = raw_price * (1 - slippage)
        price = round_to_tick(slipped, direction="down", currency=currency)
        if price <= 0:
            shares = 0.0
            position = False
            return
        sell_shares = float(int(shares * sell_pct / 100.0))
        if sell_shares <= 0:
            return
        sell_shares = min(sell_shares, shares)
        proceeds = sell_shares * price * (1 - commission - sell_tax)
        cost = sell_shares * entry_price * (1 + commission)
        is_partial = sell_shares < shares - 1e-9
        trades.append({
            "진입일": dates[entry_i], "청산일": dates[i], "보유일": i - entry_i,
            "진입가": entry_price, "청산가": price,
            "수익률(%)": (proceeds - cost) / cost * 100,
            "청산사유": reason + (f"({sell_pct:.0f}%)" if is_partial else ""),
        })
        cash += proceeds
        shares -= sell_shares
        if shares <= 1e-9:
            shares = 0.0
            position = False
            executed_rules.clear()

    for i in range(n):
        if next_open:
            if pending_buy and not position:
                _open(i, opens[i])
                pending_buy = False
            if pending_sell and position:
                sell_pct = _sell_pct_of(pending_reason)
                _close(i, opens[i], pending_reason, sell_pct)
                key = _reason_key(pending_reason)
                if key is not None and position:
                    executed_rules.add(key)
                pending_sell = False

        if not position and not pending_buy:
            if buy_arr[i]:
                if next_open:
                    pending_buy = True
                else:
                    _open(i, closes[i])
        elif position and not pending_sell:
            if highs[i] > peak_high:
                peak_high = highs[i]
            if closes[i] > peak_close:
                peak_close = closes[i]
            cur_ret = (closes[i] - entry_price) / entry_price * 100
            held = i - entry_i
            reason = ""
            if take_profit is not None and cur_ret >= take_profit and "tp" not in executed_rules:
                reason = "익절"
            elif stop_loss is not None and cur_ret <= stop_loss and "sl" not in executed_rules:
                reason = "손절"
            elif (trail_atr_mult is not None and atr_arr is not None
                  and not np.isnan(atr_arr[i])
                  and closes[i] <= peak_high - trail_atr_mult * atr_arr[i]
                  and "atr" not in executed_rules):
                reason = "ATR트레일링"
            elif (trail_pct is not None
                  and closes[i] <= peak_close * (1 - trail_pct / 100)
                  and "trail" not in executed_rules):
                reason = "트레일링스톱"
            elif hold_days is not None and held >= hold_days and "hold" not in executed_rules:
                reason = "보유기간"
            elif sell_arr is not None and sell_arr[i]:
                reason = "매도신호"
            if reason:
                if next_open:
                    pending_sell = True
                    pending_reason = reason
                else:
                    sell_pct = _sell_pct_of(reason)
                    _close(i, closes[i], reason, sell_pct)
                    key = _reason_key(reason)
                    if key is not None and position:
                        executed_rules.add(key)

        equity[i] = cash + shares * closes[i]

    if position:
        _close(n - 1, closes[n - 1], "기간종료")
        equity[n - 1] = cash

    equity_s = pd.Series(equity, index=dates, name="전략")
    benchmark_s = pd.Series(closes / closes[0] * initial_capital, index=dates, name="Buy&Hold")
    trades_df = pd.DataFrame(trades)

    return {
        "success": True, "error": None,
        "equity": equity_s, "benchmark": benchmark_s, "trades": trades_df,
        "metrics": _metrics(equity_s, benchmark_s, trades_df),
    }
