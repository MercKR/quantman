"""Workbench 시나리오 — KRX 하루 happy path (매수→체결→dedup→매도→정산).

sim은 production 복사본이 아니다: Trader(broker) 생성자 + intraday_loop._on_exec_event
라는 기존 주입 seam에 SimBroker를 끼워 실제 trader 로직을 결정론적으로 구동하고,
전이 후 불변식(INVARIANTS.md)을 단언한다.
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path

import pytest

_LOCAL = Path(__file__).resolve().parent.parent.parent
if str(_LOCAL) not in sys.path:
    sys.path.insert(0, str(_LOCAL))

from sim.broker import SimBroker


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
