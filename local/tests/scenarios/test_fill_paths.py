"""Workbench 시나리오 — 체결 인지 경로(A3). 경로 독립 + ODNO 패딩 내성.

happy-path E2E는 padded ODER_NO만 썼다. 여기서 M2의 핵심(unpadded WS도 canonical
매칭)과 REST 폴링 경로(WS 없이 체결 인지)를 실제 코드로 검증한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

_LOCAL = Path(__file__).resolve().parent.parent.parent
if str(_LOCAL) not in sys.path:
    sys.path.insert(0, str(_LOCAL))

from sim import invariants


def test_unpadded_ws_oder_no_is_recognized(isolated_trader):
    """INV-FILL-2: WS ODER_NO가 unpadded여도 canonical 매칭으로 체결 인지된다.

    pending 키는 발주응답 ODNO(raw, zero-padded-10). KIS 실시간 ODER_NO 패딩은
    미보장 — unpadded로 와도 _match_pending_key의 canonical 비교로 매칭돼야 한다.
    (정확일치였다면 실시간 체결을 전량 놓쳤을 결함 = M2가 고친 것.)
    """
    from localapp import intraday_loop
    t, broker = isolated_trader
    r = broker.buy_limit("005930", 10, 70000)
    t._after_submit(r, "s1", "T", {}, "005930", "buy", 10, 70000, 70000,
                    {"use_limit": True, "buy_tolerance_pct": 1.0}, [], reason="매수신호")
    assert r["order_no"] == "0000000001"                  # pending 키 = raw padded

    evt = broker.exec_event(r["order_no"], 10, 70000.0)
    evt["ODER_NO"] = r["order_no"].lstrip("0")            # "1" — unpadded WS 시뮬
    assert evt["ODER_NO"] == "1"

    intraday_loop._on_exec_event(t, broker, evt)
    assert t.ledger["s1"]["qty"] == 10, "INV-FILL-2 위반: unpadded ODER_NO 체결 미인지"
    assert not t.pending                                  # 전량 체결 → 회수
    invariants.check_all(t)


def test_rest_polling_recognizes_fill(isolated_trader):
    """INV-FILL-3: WS 없이 REST 폴링(_resolve_pending)으로도 체결 인지(경로 독립).

    WS 끊김 fallback(Q3) 경로. _resolve_pending이 broker.order_status로 filled를
    인지해 같은 _apply_fill로 수렴한다.
    """
    t, broker = isolated_trader
    r = broker.buy_limit("005930", 5, 68000)
    t._after_submit(r, "s1", "T", {}, "005930", "buy", 5, 68000, 68000,
                    {"use_limit": True, "buy_tolerance_pct": 1.0}, [], reason="매수신호")
    assert t.pending                                      # 아직 미체결

    broker.mark_filled(r["order_no"], 5, 68000.0)         # KIS측 체결(REST 조회=filled)
    t._resolve_pending([])

    assert t.ledger["s1"]["qty"] == 5, "INV-FILL-3 위반: REST 폴링 체결 미인지"
    assert not t.pending                                  # 인지 후 회수
    invariants.check_all(t)
