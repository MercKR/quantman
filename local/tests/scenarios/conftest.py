"""Workbench 시나리오 공용 픽스처/헬퍼.

isolated_trader: trader 영속 경로를 tmp로 격리 + KST 날짜 고정 + 서버 push 차단 후
SimBroker 위의 실제 Trader를 돌려준다. buy_and_fill: 매수 발주→WS 체결까지 한 번에.
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
from sim import scenario


@pytest.fixture
def isolated_trader(tmp_path, monkeypatch):
    from localapp import trader as tr
    from localapp import intraday_loop, killswitch
    for name in ("LEDGER_PATH", "EQUITY_PATH", "PENDING_ORDERS_PATH",
                 "REBALANCE_PATH", "TRADES_PATH"):
        monkeypatch.setattr(tr, name, tmp_path / f"{name}.json")
    monkeypatch.setattr(killswitch, "KILLSWITCH_PATH", tmp_path / "ks.json")
    monkeypatch.setattr(intraday_loop, "push_snapshot", lambda *a, **k: None)
    monkeypatch.setattr(tr, "kst_today", lambda: datetime.date(2026, 6, 1))

    broker = SimBroker()
    return tr.Trader(broker), broker


def buy_and_fill(trader, broker, sid: str, symbol: str, qty: int, price: float,
                  strat_name: str = "T"):
    """매수 발주(SUBMITTED→PENDING) → WS 전량 체결(PENDING→FILLED). order_no 반환."""
    r = broker.buy_limit(symbol, qty, int(price))
    trader._after_submit(r, sid, strat_name, {}, symbol, "buy", qty, price, int(price),
                          {"use_limit": True, "buy_tolerance_pct": 1.0}, [], reason="매수신호")
    scenario.inject_ws_fill(trader, broker, r["order_no"], qty, price)
    return r["order_no"]
