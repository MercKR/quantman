"""통합 실행 엔진 (engine.py) 회귀 — 명세 §7.6.

Stage 1: 이벤트(on_signal) 경로가 기존 run_strategy_ir(→run_backtest_ir/run_portfolio_ir)와
동치인지 고정한다. 신엔진은 검증된 경로 패리티를 통과한 뒤에만 횡단·청산 overlay로 확장.

    cd platform && pytest tests/test_engine_unified.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

from quant_core.blocks import Node, const, data  # noqa: E402
from quant_core.ir_engine import (  # noqa: E402
    Entry, Exit, Overlays, PositionSpec, SimSpec, Sizing, StrategyIR, Universe,
    run_backtest_ir,
)
from quant_core.ir_engine.backtest import run_portfolio_ir  # noqa: E402
from quant_core.ir_engine.engine import run_unified, _select, _target_weights  # noqa: E402


def _one(seed: int, periods: int = 200):
    idx = pd.date_range("2020-01-01", periods=periods, freq="B")
    r = np.random.default_rng(seed)
    close = np.maximum(100 + np.cumsum(r.normal(0.05, 1.2, periods)), 5.0)
    return pd.DataFrame({
        "Open": np.r_[close[0], close[:-1]], "High": close * 1.01,
        "Low": close * 0.99, "Close": close, "Volume": r.uniform(1e5, 1e6, periods),
        "ma_dev_20d": r.uniform(-5, 5, periods), "atr_14": np.abs(r.normal(2, 0.5, periods)),
    }, index=idx)


def _cond_self():
    return Node(op="compare", params={"op": ">"},
                inputs={"left": data("__SELF__.ma_dev_20d"), "right": const(0.0)})


def _assert_parity(s, d):
    """run_unified == 구 이벤트 엔진(run_backtest_ir/run_portfolio_ir) 직접 대조 — 동치 고정.

    디스패치가 통합 엔진으로 전환된 뒤에도 검증이 자기대조(tautology)가 되지 않도록,
    구 엔진을 직접 호출해 equity 시계열·트레이드 수를 비교한다.
    """
    a = run_unified(s, d)
    ex, sim, u, sz = s.position.exit, s.simulation, s.universe, s.position.sizing
    kw = dict(sell_node=ex.condition, hold_days=ex.hold_days, take_profit=ex.take_profit,
              stop_loss=ex.stop_loss, trail_atr_mult=ex.trail_atr_mult, trail_pct=ex.trail_pct,
              fill=sim.fill, initial_capital=sim.initial_capital, start=sim.start, end=sim.end)
    if u.kind == "single":
        b = run_backtest_ir(d, u.symbols[0], s.signal, currency=sim.currency, **kw)
    else:
        b = run_portfolio_ir(d, u.symbols, s.signal, amount_pct=sz.amount_pct,
                             amount_krw=(sz.amount_krw if sz.mode == "fixed_amount" else None), **kw)
    assert a["success"] and b["success"], (a.get("error"), b.get("error"))
    ea, eb = a["equity"], b["equity"]
    assert list(ea.index) == list(eb.index), "달력 불일치"
    assert np.allclose(ea.to_numpy(), eb.to_numpy(), rtol=1e-9, atol=1e-6), \
        f"equity 불일치: max diff {np.abs(ea.to_numpy() - eb.to_numpy()).max()}"
    assert a["metrics"]["n_trades"] == b["metrics"]["n_trades"]
    assert np.isclose(a["metrics"]["total_return"], b["metrics"]["total_return"])


# ── 단일 종목 (run_backtest_ir 경로) ──────────────────────────────────────────

def test_unified_single_hold_days():
    d = {"005930": _one(5)}
    s = StrategyIR(signal=_cond_self(), universe=Universe(kind="single", symbols=["005930"]),
                   position=PositionSpec(entry=Entry(mode="on_signal"), exit=Exit(hold_days=10)),
                   simulation=SimSpec(initial_capital=1e7))
    _assert_parity(s, d)


def test_unified_single_tp_sl():
    d = {"005930": _one(7)}
    s = StrategyIR(signal=_cond_self(), universe=Universe(kind="single", symbols=["005930"]),
                   position=PositionSpec(entry=Entry(mode="on_signal"),
                                         exit=Exit(take_profit=8.0, stop_loss=-5.0)),
                   simulation=SimSpec(initial_capital=1e7))
    _assert_parity(s, d)


def test_unified_single_sell_condition():
    d = {"005930": _one(11)}
    sell = Node(op="compare", params={"op": "<"},
                inputs={"left": data("__SELF__.ma_dev_20d"), "right": const(0.0)})
    s = StrategyIR(signal=_cond_self(), universe=Universe(kind="single", symbols=["005930"]),
                   position=PositionSpec(entry=Entry(mode="on_signal"), exit=Exit(condition=sell)),
                   simulation=SimSpec(initial_capital=1e7))
    _assert_parity(s, d)


def test_unified_single_close_fill():
    d = {"005930": _one(3)}
    s = StrategyIR(signal=_cond_self(), universe=Universe(kind="single", symbols=["005930"]),
                   position=PositionSpec(entry=Entry(mode="on_signal"), exit=Exit(hold_days=5)),
                   simulation=SimSpec(initial_capital=1e7, fill="close"))
    _assert_parity(s, d)


# ── 다종목 포트폴리오 (run_portfolio_ir 경로) ─────────────────────────────────

def test_unified_portfolio_hold_days():
    d = {"AAA": _one(1), "BBB": _one(2), "CCC": _one(3)}
    s = StrategyIR(signal=_cond_self(), universe=Universe(kind="list", symbols=["AAA", "BBB", "CCC"]),
                   position=PositionSpec(entry=Entry(mode="on_signal"), exit=Exit(hold_days=8),
                                         sizing=Sizing(amount_pct=30.0)),
                   simulation=SimSpec(initial_capital=1e7))
    _assert_parity(s, d)


def test_unified_portfolio_sell_condition():
    d = {"AAA": _one(4), "BBB": _one(6), "CCC": _one(8)}
    sell = Node(op="compare", params={"op": "<"},
                inputs={"left": data("__SELF__.ma_dev_20d"), "right": const(-1.0)})
    s = StrategyIR(signal=_cond_self(), universe=Universe(kind="list", symbols=["AAA", "BBB", "CCC"]),
                   position=PositionSpec(entry=Entry(mode="on_signal"), exit=Exit(condition=sell),
                                         sizing=Sizing(amount_pct=40.0)),
                   simulation=SimSpec(initial_capital=1e7))
    _assert_parity(s, d)


# ── Stage 2: 스케줄 횡단 (정수주 리밸런스) ────────────────────────────────────

def _multi():
    idx = pd.date_range("2020-01-01", periods=252, freq="B")

    def mk(drift, mom):
        close = 100 * (1 + drift) ** np.arange(252)
        return pd.DataFrame({
            "Open": close, "High": close * 1.001, "Low": close * 0.999,
            "Close": close, "Volume": 1e6, "momentum_12_1m": float(mom),
            "ma_dev_20d": np.where(np.arange(252) % 2 == 0, 1.0, -1.0),
        }, index=idx)

    return {"AAA": mk(0.003, 10.0), "BBB": mk(-0.001, -5.0), "CCC": mk(0.0, -3.0)}


def test_unified_scheduled_picks_winner():
    """score top1 롱 월간 → 모멘텀 최상위 AAA 보유 → 벤치 초과, 정수주."""
    s = StrategyIR(
        signal=data("momentum_12_1m"), universe=Universe(kind="all"),
        position=PositionSpec(direction="long", sizing=Sizing(mode="equal_weight"),
                              entry=Entry(mode="scheduled", rebalance="monthly", top_n=1)),
        simulation=SimSpec(initial_capital=1e7))
    res = run_unified(s, _multi())
    assert res["success"], res.get("error")
    assert res["metrics"]["total_return"] > res["metrics"]["bench_total"]
    assert res["equity"].iloc[-1] > 0


def test_unified_scheduled_quarterly():
    """분기 리밸런스 — A-1 핵심 주기. 실행되고 양의 자산곡선."""
    s = StrategyIR(
        signal=data("momentum_12_1m"), universe=Universe(kind="all"),
        position=PositionSpec(direction="long", entry=Entry(mode="scheduled",
                                                            rebalance="quarterly", top_n=2)),
        simulation=SimSpec(initial_capital=1e7))
    res = run_unified(s, _multi())
    assert res["success"] and res["equity"].iloc[-1] > 0


def test_unified_scheduled_top_pct():
    """top_pct(상위 40%) 선택 — 3종목 중 1~2종목 보유."""
    s = StrategyIR(
        signal=data("momentum_12_1m"), universe=Universe(kind="all"),
        position=PositionSpec(direction="long", entry=Entry(mode="scheduled",
                                                            rebalance="monthly", top_pct=40.0)),
        simulation=SimSpec(initial_capital=1e7))
    res = run_unified(s, _multi())
    assert res["success"] and res["equity"].iloc[-1] > 0


def test_unified_scheduled_fixed_weight():
    """fixed_weight 정적 배분 — 3자산 지정 비중 보유(B-5)."""
    s = StrategyIR(
        signal=data("momentum_12_1m"), universe=Universe(kind="all"),
        position=PositionSpec(direction="long",
                              sizing=Sizing(mode="fixed_weight",
                                            weights={"AAA": 0.5, "BBB": 0.3, "CCC": 0.2}),
                              entry=Entry(mode="scheduled", rebalance="monthly")),
        simulation=SimSpec(initial_capital=1e7))
    res = run_unified(s, _multi())
    assert res["success"] and res["equity"].iloc[-1] > 0
    assert res["metrics"]["n_trades"] >= 0


def test_unified_scheduled_integer_shares():
    """정수주 — 자본이 가격에 안 떨어지면 현금드래그 발생(전액 투입 불가)."""
    s = StrategyIR(
        signal=data("momentum_12_1m"), universe=Universe(kind="all"),
        position=PositionSpec(direction="long", entry=Entry(mode="scheduled",
                                                            rebalance="monthly", top_n=1)),
        simulation=SimSpec(initial_capital=123_456.0))   # 비정수배 자본
    res = run_unified(s, _multi())
    assert res["success"] and res["equity"].iloc[-1] > 0


def test_unified_scheduled_condition_holds_true():
    """condition 신호 스케줄 → 참인 종목 동일가중 보유."""
    cond = Node(op="compare", params={"op": ">"},
                inputs={"left": data("ma_dev_20d"), "right": const(0.0)})
    s = StrategyIR(
        signal=cond, universe=Universe(kind="all"),
        position=PositionSpec(direction="long", entry=Entry(mode="scheduled", rebalance="weekly")),
        simulation=SimSpec(initial_capital=1e7))
    res = run_unified(s, _multi())
    assert res["success"] and res["equity"].iloc[-1] > 0


# ── Stage 3: 청산 overlay (스케줄 + 동적 청산) — 재설계의 핵심 ────────────────

def _lt0(ref):
    return Node(op="compare", params={"op": "<"}, inputs={"left": data(ref), "right": const(0.0)})


def test_unified_scheduled_exit_changes_outcome():
    """예시 A-1 패턴 — 스케줄 리밸런스 + 동적 청산조건이 결과를 바꾼다(이전엔 불가).

    동일 전략 ± exit.condition → with-exit가 더 많은 트레이드(중간청산)와 다른 자산곡선.
    """
    d = _multi()
    base = dict(signal=data("momentum_12_1m"), universe=Universe(kind="all"),
                simulation=SimSpec(initial_capital=1e7))
    no_exit = StrategyIR(**base, position=PositionSpec(
        direction="long", entry=Entry(mode="scheduled", rebalance="monthly", top_n=2)))
    with_exit = StrategyIR(**base, position=PositionSpec(
        direction="long", entry=Entry(mode="scheduled", rebalance="monthly", top_n=2),
        exit=Exit(condition=_lt0("ma_dev_20d"))))
    a, b = run_unified(no_exit, d), run_unified(with_exit, d)
    assert a["success"] and b["success"], (a.get("error"), b.get("error"))
    assert b["metrics"]["n_trades"] > a["metrics"]["n_trades"], "청산이 트레이드를 늘려야"
    assert not np.isclose(a["equity"].iloc[-1], b["equity"].iloc[-1]), "청산이 결과를 바꿔야"
    assert (b["trades"]["청산사유"] == "매도신호").any(), "매도신호 청산 기록 존재"


def test_unified_scheduled_stop_loss():
    """스케줄 + 손절 — 하락 종목이 손절로 중간 청산."""
    idx = pd.date_range("2020-01-01", periods=120, freq="B")

    def mk(drift, mom):
        close = 100 * (1 + drift) ** np.arange(120)
        return pd.DataFrame({"Open": close, "High": close * 1.001, "Low": close * 0.999,
                             "Close": close, "Volume": 1e6, "momentum_12_1m": float(mom),
                             "ma_dev_20d": 1.0}, index=idx)
    d = {"UP": mk(0.004, 12.0), "DN": mk(-0.01, 8.0), "FLAT": mk(0.0, 1.0)}
    s = StrategyIR(signal=data("momentum_12_1m"), universe=Universe(kind="all"),
                   position=PositionSpec(direction="long", exit=Exit(stop_loss=-8.0),
                                         entry=Entry(mode="scheduled", rebalance="monthly", top_n=2)),
                   simulation=SimSpec(initial_capital=1e7))
    res = run_unified(s, d)
    assert res["success"], res.get("error")
    assert (res["trades"]["청산사유"] == "손절").any(), "DN이 손절로 청산돼야"


def _multi5():
    idx = pd.date_range("2020-01-01", periods=120, freq="B")

    def mk(drift, mom, dev_flip=None):
        close = 100 * (1 + drift) ** np.arange(120)
        dev = (np.full(120, 1.0) if dev_flip is None
               else np.where(np.arange(120) < dev_flip, 1.0, -1.0))
        return pd.DataFrame({"Open": close, "High": close * 1.001, "Low": close * 0.999,
                             "Close": close, "Volume": 1e6, "momentum_12_1m": float(mom),
                             "ma_dev_20d": dev}, index=idx)
    return {"WIN": mk(0.004, 12.0), "EXIT": mk(0.001, 8.0, dev_flip=30),
            "REFILL": mk(0.002, 5.0), "LOW": mk(0.0, 1.0)}


def test_unified_refill_cash_vs_replace():
    """refill: cash=빈 슬롯 현금 유지 · replace=차순위(REFILL) 즉시 충원."""
    d = _multi5()
    exit_cond = _lt0("ma_dev_20d")
    base = dict(signal=data("momentum_12_1m"), universe=Universe(kind="all"),
                simulation=SimSpec(initial_capital=1e7))

    def _mk(refill):
        return StrategyIR(**base, position=PositionSpec(
            direction="long", exit=Exit(condition=exit_cond),
            entry=Entry(mode="scheduled", rebalance="monthly", top_n=2, refill=refill)))

    cash = run_unified(_mk("cash"), d)
    repl = run_unified(_mk("replace"), d)
    assert cash["success"] and repl["success"], (cash.get("error"), repl.get("error"))
    cash_syms = set(cash["trades"]["종목"]) if len(cash["trades"]) else set()
    repl_syms = set(repl["trades"]["종목"]) if len(repl["trades"]) else set()
    # replace는 청산 후 차순위 REFILL을 사들임 → cash 모드엔 (중간) 없던 종목
    assert "REFILL" in repl_syms, "replace는 차순위 후보를 충원해야"
    assert "REFILL" not in cash_syms, "cash는 빈 슬롯을 현금 유지(REFILL 미보유)"


# ── 선택·사이징 단위 (Selector/Sizer — _weights_row 커버리지 이전) ────────────

def test_engine_select_long_topn_equal():
    pos = PositionSpec(direction="long", sizing=Sizing(mode="equal_weight"),
                       entry=Entry(mode="scheduled", top_n=2))
    alpha = pd.Series({"A": 3.0, "B": 1.0, "C": 2.0, "D": 0.5})
    longs, shorts = _select(alpha, pos, False)
    assert set(longs) == {"A", "C"} and not shorts
    w = _target_weights(longs, shorts, alpha, None, pos.sizing)
    assert np.isclose(w.abs().sum(), 1.0) and (w > 0).all()


def test_engine_select_long_short_dollar_neutral():
    pos = PositionSpec(direction="long_short", entry=Entry(mode="scheduled", top_n=1))
    alpha = pd.Series({"A": 3.0, "B": 1.0, "C": 2.0, "D": 0.5})
    longs, shorts = _select(alpha, pos, False)
    w = _target_weights(longs, shorts, alpha, None, pos.sizing)
    assert np.isclose(w.sum(), 0.0, atol=1e-9)         # 달러 중립
    assert np.isclose(w.abs().sum(), 1.0)              # 풀투자(절대비중)
    assert w["A"] > 0 and w["D"] < 0                    # 최고 롱·최저 숏


def test_engine_size_signal_proportional():
    pos = PositionSpec(direction="long", sizing=Sizing(mode="signal_proportional"),
                       entry=Entry(mode="scheduled", top_n=2))
    alpha = pd.Series({"A": 3.0, "B": 1.0})
    longs, shorts = _select(alpha, pos, False)
    w = _target_weights(longs, shorts, alpha, None, pos.sizing)
    assert np.isclose(w["A"], 0.75) and np.isclose(w["B"], 0.25)   # 3:1 → 0.75:0.25


def test_engine_select_threshold_sign_split():
    """임계 선택(threshold) — 부호 기준 롱숏(TSMOM): score>0 롱·score<0 숏(순위 무관)."""
    pos = PositionSpec(direction="long_short", entry=Entry(mode="scheduled", threshold=0.0))
    alpha = pd.Series({"A": 3.0, "B": -1.0, "C": 2.0, "D": -0.5, "E": 0.0})
    longs, shorts = _select(alpha, pos, False)
    assert set(longs) == {"A", "C"}            # 양수 전부 롱
    assert set(shorts) == {"B", "D"}           # 음수 전부 숏 (정확히 임계값 0은 어느 쪽도 아님)


def test_engine_select_threshold_long_keeps_score():
    """롱 전용 임계 — score>thr 선택하되 score 보존(신호비례 사이징과 결합 가능)."""
    pos = PositionSpec(direction="long", sizing=Sizing(mode="signal_proportional"),
                       entry=Entry(mode="scheduled", threshold=5.0))
    alpha = pd.Series({"A": 10.0, "B": 6.0, "C": 3.0})
    longs, shorts = _select(alpha, pos, False)
    assert set(longs) == {"A", "B"} and not shorts          # >5 만 선택
    w = _target_weights(longs, shorts, alpha, None, pos.sizing)
    assert np.isclose(w["A"], 10 / 16) and np.isclose(w["B"], 6 / 16)   # score 비례 유지


# ── Stage 4: 롱숏 정수주 + 전역 overlay + 비용 ────────────────────────────────

def test_unified_long_short_winner_loser():
    """롱숏 — 승자(AAA) 롱 + 패자(BBB) 숏 둘 다 이익 → 양의 수익."""
    s = StrategyIR(signal=data("momentum_12_1m"), universe=Universe(kind="all"),
                   position=PositionSpec(direction="long_short",
                                         entry=Entry(mode="scheduled", rebalance="monthly", top_n=1)),
                   simulation=SimSpec(initial_capital=1e7))
    res = run_unified(s, _multi())
    assert res["success"], res.get("error")
    assert res["metrics"]["total_return"] > 0


def test_unified_tsmom_sign_split_runs():
    """TSMOM — 자기 추세 부호로 독립 롱/숏(임계 선택). AAA(+) 롱·BBB·CCC(−) 숏 → 추세대로 양수익."""
    s = StrategyIR(signal=data("momentum_12_1m"), universe=Universe(kind="all"),
                   position=PositionSpec(direction="long_short",
                                         entry=Entry(mode="scheduled", rebalance="monthly", threshold=0.0)),
                   simulation=SimSpec(initial_capital=1e7))
    res = run_unified(s, _multi())
    assert res["success"], res.get("error")
    assert res["metrics"]["total_return"] > 0


def test_threshold_requires_score_signal():
    """임계 선택은 score 신호 전용 — condition 신호에 threshold면 S-select 에러."""
    from quant_core.ir_engine import validate_strategy
    cond = Node(op="compare", params={"op": ">"},
                inputs={"left": data("momentum_12_1m"), "right": const(0.0)})
    s = StrategyIR(signal=cond, universe=Universe(kind="all"),
                   position=PositionSpec(direction="long",
                                         entry=Entry(mode="scheduled", rebalance="monthly", threshold=0.0)))
    assert any(i.rule == "S-select" and i.is_error for i in validate_strategy(s))


def test_unified_borrow_cost_reduces_return():
    """숏 차입비용(5%)이 롱숏 수익을 깎는다."""
    base = dict(signal=data("momentum_12_1m"), universe=Universe(kind="all"))

    def _run(bp):
        return run_unified(StrategyIR(
            **base, position=PositionSpec(direction="long_short",
                                          entry=Entry(mode="scheduled", rebalance="monthly", top_n=1)),
            simulation=SimSpec(initial_capital=1e7, short_borrow_pct=bp)), _multi())
    r0, r5 = _run(0.0), _run(5.0)
    assert r0["success"] and r5["success"]
    assert r5["metrics"]["total_return"] < r0["metrics"]["total_return"]


def test_unified_target_vol_runs():
    """target_vol 사이저 + 레버리지 — 실행·양의 자산곡선(B-1 형태)."""
    s = StrategyIR(signal=data("momentum_12_1m"), universe=Universe(kind="all"),
                   position=PositionSpec(direction="long",
                                         sizing=Sizing(mode="target_vol", target_vol_pct=20.0),
                                         entry=Entry(mode="scheduled", rebalance="monthly", top_n=2)),
                   simulation=SimSpec(initial_capital=1e7, leverage=2.0))
    res = run_unified(s, _multi())
    assert res["success"] and res["equity"].iloc[-1] > 0


def test_unified_rfr_cash_accrues():
    """현금 무위험수익 — 미보유(현금) 전략이 rfr로 적립."""
    never = Node(op="compare", params={"op": ">"},
                 inputs={"left": data("ma_dev_20d"), "right": const(100.0)})
    base = dict(signal=never, universe=Universe(kind="all"),
                position=PositionSpec(direction="long", entry=Entry(mode="scheduled", rebalance="monthly")))
    r0 = run_unified(StrategyIR(**base, simulation=SimSpec(initial_capital=1e7, rfr_pct=0.0)), _multi())
    r5 = run_unified(StrategyIR(**base, simulation=SimSpec(initial_capital=1e7, rfr_pct=5.0)), _multi())
    assert r0["success"] and r5["success"]
    assert r5["equity"].iloc[-1] > r0["equity"].iloc[-1]


def test_unified_drawdown_overlay_caps_mdd():
    """낙폭 정지 overlay — 하락 전략의 MDD 완화."""
    idx = pd.date_range("2020-01-01", periods=120, freq="B")

    def mk(drift, mom):
        close = 100 * (1 + drift) ** np.arange(120)
        return pd.DataFrame({"Open": close, "High": close * 1.001, "Low": close * 0.999,
                             "Close": close, "Volume": 1e6, "momentum_12_1m": float(mom),
                             "ma_dev_20d": 1.0}, index=idx)
    d = {"DN": mk(-0.005, 5.0), "DN2": mk(-0.004, 4.0)}
    base = dict(signal=data("momentum_12_1m"), universe=Universe(kind="all"),
                simulation=SimSpec(initial_capital=1e7))
    plain = run_unified(StrategyIR(**base, position=PositionSpec(
        direction="long", entry=Entry(mode="scheduled", rebalance="monthly", top_n=1))), d)
    dd = run_unified(StrategyIR(**base, position=PositionSpec(
        direction="long", entry=Entry(mode="scheduled", rebalance="monthly", top_n=1),
        overlays=Overlays(max_drawdown_stop=10.0))), d)
    assert plain["success"] and dd["success"]
    assert dd["metrics"]["mdd"] >= plain["metrics"]["mdd"]   # mdd<0 — 완화 시 0에 가까움


# ── 예시 매핑: A-1 형태 (스크리너 + 분기 + 동적 청산) — 재설계 동기 ───────────

def test_unified_a1_shape_screener_quarterly_exit():
    """A-1 형태 — 스크리너 유니버스 + score 신호 + 분기 리밸런스 + 적자전환류 청산.

    이전 엔진에선 '분기 횡단 리밸런스 + 동적 청산'이 표현 불가했다. 통합 엔진에서
    한 전략으로 조립·실행되고, 청산이 결과에 효과를 내는지 고정한다.
    """
    d = _multi()
    filt = Node(op="compare", params={"op": ">"},
                inputs={"left": data("momentum_12_1m"), "right": const(-100.0)})  # 전부 통과(경로 가동)
    screener = {"filter": filt.model_dump(),
                "rank": {"ref": "momentum_12_1m", "top_n": 3, "direction": "top"}}
    base = dict(signal=data("momentum_12_1m"),
                universe=Universe(kind="screener", screener=screener),
                simulation=SimSpec(initial_capital=1e7))
    no_exit = StrategyIR(**base, position=PositionSpec(
        direction="long", entry=Entry(mode="scheduled", rebalance="quarterly", top_n=2)))
    with_exit = StrategyIR(**base, position=PositionSpec(
        direction="long", entry=Entry(mode="scheduled", rebalance="quarterly", top_n=2),
        exit=Exit(condition=_lt0("ma_dev_20d"))))
    a, b = run_unified(no_exit, d), run_unified(with_exit, d)
    assert a["success"] and b["success"], (a.get("error"), b.get("error"))
    assert not np.isclose(a["equity"].iloc[-1], b["equity"].iloc[-1]), "동적 청산이 결과를 바꿔야"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
