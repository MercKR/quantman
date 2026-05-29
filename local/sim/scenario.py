"""시나리오 구동 helper — 주어진 (trader, SimBroker)를 하루 흐름으로 움직인다.

production 코드를 그대로 호출한다: _on_exec_event(실 WS 경로), trader._resolve_pending /
reconcile_with_kis(실 settlement 경로). sim은 seam에만 끼며 로직을 재구현하지 않는다.
"""
from __future__ import annotations

from localapp import intraday_loop


def inject_ws_fill(trader, broker, order_no: str, qty: int, price: float,
                    hour: str = "100000") -> None:
    """체결 통보 WS 경로로 체결을 반영(실 _on_exec_event 구동)."""
    evt = broker.exec_event(order_no, qty, price, hour)
    intraday_loop._on_exec_event(trader, broker, evt)


def run_settlement(trader, broker, today_iso: str) -> None:
    """장 마감 후 정산 경로(실 trader 메서드 구동)."""
    decisions: list[dict] = []
    trader._resolve_pending(decisions)
    trader.reconcile_with_kis(today_iso=today_iso)
