"""StrategyIR 실행 — 디스패치 + 팩터/리밸런스 백테스트.

명세 §7·§3.3. entry.mode × signal 타입으로 디스패치:
  - on_signal + condition (단일종목) → run_backtest_ir (이벤트 드리븐 룰)
  - scheduled/always               → _run_rebalance (팩터/포트폴리오)

리밸런스 경로: 신호(score 또는 condition) → 포지션 4부품(방향·사이징·top_n·
오버레이)으로 목표 가중치 행렬 → delay 적용 → 일별 P&L. 횡단·롱숏·포트폴리오를
실제 백테스트로 실행 — 데이터가 얇아도 구조는 임의 전략을 표현·실행한다.
"""

from __future__ import annotations

import copy

import numpy as np
import pandas as pd

from ..backtest import (
    _DEFAULT_COMMISSION, _DEFAULT_SELL_TAX, _DEFAULT_SLIPPAGE, _empty, _metrics,
)
from ..blocks import EvalContext, evaluate
from ..blocks.catalog import get, has
from .backtest import run_backtest_ir, run_portfolio_ir
from .spec import StrategyIR
from .sweep import daily_returns, summarize_returns, sweep_condition

TRADING_DAYS = 252


# ── 디스패치 ──────────────────────────────────────────────────────────────────

def run_strategy_ir(strategy: StrategyIR, dataset: dict[str, pd.DataFrame]) -> dict:
    """StrategyIR을 백테스트. entry.mode × signal 타입으로 경로 선택."""
    ent = strategy.position.entry.mode
    sim = strategy.simulation
    if ent == "on_signal":
        u = strategy.universe
        ex = strategy.position.exit
        sz = strategy.position.sizing
        if u.kind == "single" and len(u.symbols) == 1:
            return run_backtest_ir(
                dataset, u.symbols[0], strategy.signal,
                sell_node=ex.condition, hold_days=ex.hold_days,
                take_profit=ex.take_profit, stop_loss=ex.stop_loss,
                trail_atr_mult=ex.trail_atr_mult, trail_pct=ex.trail_pct,
                fill=sim.fill, initial_capital=sim.initial_capital,
                **_cost_kw(sim), start=sim.start, end=sim.end,
            )
        # 리스트 유니버스 → 이벤트 드리븐 포트폴리오 (S3)
        return run_portfolio_ir(
            dataset, u.symbols, strategy.signal,
            sell_node=ex.condition, hold_days=ex.hold_days,
            take_profit=ex.take_profit, stop_loss=ex.stop_loss,
            trail_atr_mult=ex.trail_atr_mult, trail_pct=ex.trail_pct,
            fill=sim.fill, initial_capital=sim.initial_capital,
            amount_pct=sz.amount_pct,
            amount_krw=(sz.amount_krw if sz.mode == "fixed_amount" else None),
            **_cost_kw_nocur(sim), start=sim.start, end=sim.end,
        )
    return _run_rebalance(strategy, dataset)


def _cost_kw_nocur(sim) -> dict:
    out = {}
    if sim.commission is not None:
        out["commission"] = sim.commission
    if sim.slippage is not None:
        out["slippage"] = sim.slippage
    if sim.sell_tax is not None:
        out["sell_tax"] = sim.sell_tax
    return out


def _cost_kw(sim) -> dict:
    out = _cost_kw_nocur(sim)
    out["currency"] = sim.currency
    return out


# ── 유니버스 ──────────────────────────────────────────────────────────────────

def _universe_symbols(strategy: StrategyIR, dataset: dict) -> list[str]:
    u = strategy.universe
    if u.kind in ("single", "list"):
        return [s for s in u.symbols if s in dataset and not dataset[s].empty]
    # all — 매크로/자산 지수 제외, OHLC 보유 종목
    macro: set = set()
    if u.exclude_macro:
        try:
            from ..data_fetcher import MACRO_SYMBOLS
            macro = set(MACRO_SYMBOLS)
        except Exception:
            macro = set()
    out = []
    for s, df in dataset.items():
        if s in macro or df is None or df.empty:
            continue
        if {"Open", "Close"}.issubset(df.columns):
            out.append(s)
    return out


# ── 리밸런스 일자 ─────────────────────────────────────────────────────────────

def _is_rebalance(i: int, last: int | None, idx: pd.DatetimeIndex,
                  period: str, every_n: int | None) -> bool:
    if last is None:
        return True
    if period == "daily":
        return True
    d, p = idx[i], idx[last]
    if period == "weekly":
        return d.isocalendar()[:2] != p.isocalendar()[:2]
    if period == "monthly":
        return (d.year, d.month) != (p.year, p.month)
    if period == "every_n_days":
        return bool(every_n) and (i - last) >= int(every_n)
    return False


# ── 가중치 산정 (포지션 4부품) ────────────────────────────────────────────────

def _size(sel: pd.Series, sizing, vol_row, sign: float) -> pd.Series:
    """선택된 종목에 사이징 적용 → 가중치(부호 포함, 합=sign 방향)."""
    idx = sel.index
    mode = sizing.mode
    if mode == "signal_proportional":
        base = sel.clip(lower=0)
        if base.sum() <= 0:
            base = pd.Series(1.0, index=idx)
    elif mode == "vol_inverse" and vol_row is not None:
        v = vol_row.reindex(idx)
        inv = (1.0 / v).replace([np.inf, -np.inf], np.nan)
        base = inv.fillna(inv[inv.notna()].mean() if inv.notna().any() else 1.0)
        if base.sum() <= 0:
            base = pd.Series(1.0, index=idx)
    else:  # equal_weight / fixed_risk / kelly / fixed_amount / pct_cash → 동일가중
        base = pd.Series(1.0, index=idx)
    return base / base.sum() * sign


def _weights_row(alpha_row: pd.Series, pos, vol_row) -> pd.Series:
    a = alpha_row.dropna()
    if a.empty:
        return pd.Series(dtype=float)
    sizing, top_n, direction = pos.sizing, pos.entry.top_n, pos.direction

    if direction == "long_short":
        n = top_n or max(1, len(a) // 5)
        longs = a.nlargest(min(n, len(a)))
        shorts = a.nsmallest(min(n, len(a)))
        w = _size(longs, sizing, vol_row, +1.0).mul(0.5).add(
            _size(shorts, sizing, vol_row, -1.0).mul(0.5), fill_value=0.0)
    else:
        sign = 1.0 if direction == "long" else -1.0
        if top_n:
            sel = a.nlargest(min(top_n, len(a)))
        else:
            sel = a[a > 0] if (a > 0).any() else a.nlargest(1)
        w = _size(sel, sizing, vol_row, sign)

    cap = sizing.max_position_pct / 100.0
    w = w.clip(lower=-cap, upper=cap)
    s = w.abs().sum()
    return w / s if s > 0 else w


def _apply_dd_stop(net: pd.Series, dd_pct: float) -> pd.Series:
    eq = (1 + net).cumprod()
    dd = (eq - eq.cummax()) / eq.cummax() * 100
    breached = dd <= -abs(dd_pct)
    if breached.any():
        first = breached.idxmax()
        net = net.copy()
        net.loc[net.index > first] = 0.0
    return net


# ── 리밸런스/팩터 백테스트 ────────────────────────────────────────────────────

def _run_rebalance(strategy: StrategyIR, dataset: dict) -> dict:
    syms = _universe_symbols(strategy, dataset)
    if not syms:
        return _empty("유니버스에 종목이 없습니다.")

    ctx = EvalContext.from_dataset(dataset)
    try:
        alpha = evaluate(strategy.signal, ctx)
    except Exception as e:  # noqa: BLE001
        return _empty(f"신호 평가 오류: {e}")
    if not isinstance(alpha, pd.DataFrame):
        return _empty("신호가 패널(종목×날짜)을 산출하지 않습니다.")

    # condition 신호 → 1.0(True)/NaN(False): True 종목만 선택 대상
    st = get(strategy.signal.op).out_type.value if has(strategy.signal.op) else "score"
    if st == "condition":
        b = alpha.astype(bool)
        alpha = b.astype(float)
        alpha = alpha.where(b, np.nan)

    cols = [s for s in syms if s in alpha.columns]
    if not cols:
        return _empty("신호가 유니버스 종목을 포함하지 않습니다.")
    alpha = alpha[cols]

    sim = strategy.simulation
    if sim.start is not None:
        alpha = alpha[alpha.index >= pd.Timestamp(sim.start)]
    if sim.end is not None:
        alpha = alpha[alpha.index <= pd.Timestamp(sim.end)]
    master = alpha.index
    if len(master) < 2:
        return _empty("백테스트 기간의 데이터가 부족합니다.")

    # 일별 수익률 + 변동성 패널
    rets = pd.DataFrame({
        s: dataset[s]["Close"].reindex(master).ffill().pct_change().fillna(0.0)
        for s in cols}, index=master)
    vol = rets.rolling(strategy.position.sizing.vol_window).std()

    # 목표 가중치 — 리밸런스 일자에만 갱신, 사이 보유(ffill)
    pos = strategy.position
    period = "daily" if pos.entry.mode == "always" else pos.entry.rebalance
    W = pd.DataFrame(0.0, index=master, columns=cols)
    last = None
    cur = pd.Series(0.0, index=cols)
    for i, d in enumerate(master):
        if _is_rebalance(i, last, master, period, pos.entry.every_n_days):
            cur = _weights_row(alpha.loc[d], pos,
                               vol.loc[d] if d in vol.index else None
                               ).reindex(cols).fillna(0.0)
            last = i
        W.iloc[i] = cur.to_numpy()

    # 오버레이: 턴오버 억제
    if pos.overlays.turnover_damp:
        from ..expression_parser import hump
        W = hump(W, float(pos.overlays.turnover_damp))

    W = W * float(sim.leverage)
    Wexec = W.shift(sim.delay if sim.delay else 0).fillna(0.0)  # look-ahead 방지

    commission = sim.commission if sim.commission is not None else _DEFAULT_COMMISSION
    slippage = sim.slippage if sim.slippage is not None else _DEFAULT_SLIPPAGE
    sell_tax = sim.sell_tax if sim.sell_tax is not None else _DEFAULT_SELL_TAX
    fee = commission + slippage + sell_tax * 0.5

    turnover = Wexec.diff().abs().sum(axis=1).fillna(0.0)
    gross = (Wexec * rets).sum(axis=1)

    # 오버레이: 변동성 타겟 (trailing — look-ahead 없음)
    if pos.overlays.vol_target:
        real = gross.rolling(63).std() * np.sqrt(TRADING_DAYS)
        scale = ((pos.overlays.vol_target / 100.0) / real.replace(0, np.nan)
                 ).shift(1).clip(upper=3.0).fillna(1.0)
        gross = gross * scale
        turnover = turnover * scale

    net = (gross - turnover * fee)
    if pos.overlays.max_drawdown_stop:
        net = _apply_dd_stop(net, pos.overlays.max_drawdown_stop)
    net = net.clip(lower=-1.0)

    equity = pd.Series((1 + net).cumprod() * sim.initial_capital, index=master, name="전략")

    # 벤치마크 — 유니버스 동일가중 buy&hold
    bench = np.zeros(len(master))
    w0 = sim.initial_capital / len(cols)
    for s in cols:
        bench += ((1 + rets[s]).cumprod() * w0).to_numpy()
    benchmark = pd.Series(bench, index=master, name="Buy&Hold")

    met = _metrics(equity, benchmark, pd.DataFrame())
    met["turnover"] = float(turnover.mean() * 100)
    return {"success": True, "error": None, "equity": equity,
            "benchmark": benchmark, "trades": pd.DataFrame(), "metrics": met}


# ── 펼침 (비전 §4) — 조건·파라미터·자산 축 ────────────────────────────────────

def _set_path(d: dict, path: str, value) -> None:
    cur = d
    keys = path.split(".")
    for k in keys[:-1]:
        cur = cur[k]
    cur[keys[-1]] = value


def run_sweep(strategy: StrategyIR, dataset: dict) -> dict:
    """펼침 — 전략을 한 축으로 반복/분할해 resultset 산출.

    axis: none(단일 실행) · condition(사후 라벨 분할) · parameter(설정 그리드 재실행)
          · asset(종목별 재실행).
    """
    sw = strategy.sweep
    if sw.axis == "none":
        return run_strategy_ir(strategy, dataset)

    if sw.axis == "parameter":
        if not sw.param_path or not sw.param_values:
            return _empty("파라미터 축은 param_path·param_values가 필요합니다.")
        base = strategy.model_dump()
        buckets = {}
        for v in sw.param_values:
            d = copy.deepcopy(base)
            d["sweep"] = {"axis": "none"}
            _set_path(d, sw.param_path, v)
            res = run_strategy_ir(StrategyIR.model_validate(d), dataset)
            buckets[str(v)] = (summarize_returns(daily_returns(res["equity"]))
                               if res.get("success") else {"error": res.get("error")})
        return {"success": True, "axis": "parameter", "param": sw.param_path, "buckets": buckets}

    if sw.axis == "asset":
        if not sw.assets:
            return _empty("자산 축은 assets가 필요합니다.")
        base = strategy.model_dump()
        buckets = {}
        for a in sw.assets:
            d = copy.deepcopy(base)
            d["sweep"] = {"axis": "none"}
            d["universe"] = {"kind": "single", "symbols": [a],
                             "screener": None, "exclude_macro": True}
            res = run_strategy_ir(StrategyIR.model_validate(d), dataset)
            buckets[a] = (summarize_returns(daily_returns(res["equity"]))
                          if res.get("success") else {"error": res.get("error")})
        return {"success": True, "axis": "asset", "buckets": buckets}

    if sw.axis == "condition":
        if sw.label is None:
            return _empty("조건 축은 라벨 블록이 필요합니다.")
        res = run_strategy_ir(strategy, dataset)
        if not res.get("success"):
            return res
        lab = evaluate(sw.label, EvalContext.from_dataset(dataset))
        if isinstance(lab, pd.DataFrame):
            u = strategy.universe
            col = (u.symbols[0] if u.symbols and u.symbols[0] in lab.columns
                   else lab.columns[0])
            label_series = lab[col]
        else:
            label_series = lab
        return {"success": True, "axis": "condition",
                "overall": summarize_returns(daily_returns(res["equity"])),
                "buckets": sweep_condition(res["equity"], label_series),
                "metrics": res["metrics"], "equity": res["equity"]}

    return _empty(f"미지원 펼침 축: {sw.axis}")
