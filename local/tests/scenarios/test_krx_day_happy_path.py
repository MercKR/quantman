"""Workbench 시나리오 — KRX 하루 happy path (매수→체결→dedup→매도→정산).

sim은 production 복사본이 아니다: Trader(broker) 생성자 + intraday_loop._on_exec_event
라는 기존 주입 seam에 SimBroker를 끼워 실제 trader 로직을 결정론적으로 구동하고,
전이 후 불변식(INVARIANTS.md)을 단언한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_LOCAL = Path(__file__).resolve().parent.parent.parent
if str(_LOCAL) not in sys.path:
    sys.path.insert(0, str(_LOCAL))

from sim.broker import SimBroker
from sim import invariants, scenario


# ── SimBroker 기본 ────────────────────────────────────────────────────────────

def test_simbroker_records_and_pads_odno():
    b = SimBroker(balance={"cash": 10_000_000, "total_eval": 10_000_000,
                            "foreign_eval_krw": 0, "cash_usd": 0, "fx_usdkrw": 0})
    r = b.buy_limit("005930", 10, 70000)
    assert r["success"] is True
    assert r["order_no"] == "0000000001"          # zero-padded-10 (KIS 형식)
    assert b.submitted[0]["symbol"] == "005930"
    st = b.order_status(r["order_no"], "005930")
    assert st["status"] == "submitted"


# ── 불변식 단언 ───────────────────────────────────────────────────────────────

def test_invariants_catch_negative_qty():
    from sim.invariants import check_ledger_nonneg

    class _T:
        ledger = {"s1": {"qty": -1}}
        pending: dict = {}
    with pytest.raises(AssertionError, match="INV-LEDGER-1"):
        check_ledger_nonneg(_T())


# ── KRX 하루 E2E ──────────────────────────────────────────────────────────────
# isolated_trader 픽스처는 conftest.py에 공용 정의.

def test_krx_day_buy_fill_sell_settlement(isolated_trader):
    t, broker = isolated_trader
    sid = "strat1"

    # 1) 매수 발주 → pending 등록 (실 _after_submit: SUBMITTED→PENDING)
    r = broker.buy_limit("005930", 10, 70000)
    t._after_submit(r, sid, "삼성", {}, "005930", "buy", 10, 70000, 70000,
                    {"use_limit": True, "buy_tolerance_pct": 1.0}, [], reason="매수신호")
    assert any(p["order_no"] == "0000000001" for p in t.pending.values())
    invariants.check_all(t)

    # 2) WS 체결 통보 → 원장 반영 (실 _on_exec_event: PENDING→FILLED)
    scenario.inject_ws_fill(t, broker, "0000000001", 10, 70000.0)
    assert t.ledger[sid]["qty"] == 10
    assert not t.pending          # 전량 체결 → pending 회수
    invariants.check_all(t)

    # 3) 중복 체결 통보 → INV-FILL-1: qty 불변
    scenario.inject_ws_fill(t, broker, "0000000001", 10, 70000.0)
    assert t.ledger[sid]["qty"] == 10, "INV-FILL-1: 중복 체결이 이중 반영됨"

    # 4) 매도 발주 + 체결 → 포지션 청산 (OPEN→FLAT)
    r2 = broker.sell_limit("005930", 10, 71000)
    t._after_submit(r2, sid, "삼성", {}, "005930", "sell", 10, 71000, 71000,
                    {"use_limit": True, "sell_tolerance_pct": 1.0}, [], reason="청산")
    scenario.inject_ws_fill(t, broker, r2["order_no"], 10, 71000.0)
    assert sid not in t.ledger    # FLAT
    invariants.check_all(t)

    # 5) settlement — 미체결 정리 + reconcile(외부 매도 없음 → drift 없음)
    scenario.run_settlement(t, broker, "2026-06-01")
    invariants.check_all(t)
