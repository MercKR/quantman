"""M2 회귀 — KIS 주문번호(ODNO) 정규화 단일 출처.

축3 결함: 체결 인지 3경로(WS 체결통보·국내 REST·해외 REST)가 ODNO를 제각각
비교했다. 발주응답 ODNO와 일별체결 odno는 zero-padded-10("0001569157")이지만
WS 실시간 ODER_NO의 패딩은 KIS spec에 미보장 — unpadded로 오면 정확일치 lookup이
전량 빗나가 실시간 체결을 통째로 놓친다(killswitch/push 지연).

M2: 단일 canonical_odno()를 3 비교지점에 적용. pending 키는 raw 유지(취소·조회·
GUI 라운드트립은 KIS가 준 형태 그대로), 매칭 비교에서만 canonical화한다.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_LOCAL_DIR = Path(__file__).resolve().parent.parent
if str(_LOCAL_DIR) not in sys.path:
    sys.path.insert(0, str(_LOCAL_DIR))

from localapp.kis_broker import KisBroker, canonical_odno


# ── canonical_odno: 정규화 규칙 ──────────────────────────────────────────────────

def test_canonical_strips_leading_zeros_and_whitespace():
    assert canonical_odno("0001569157") == "1569157"
    assert canonical_odno("1569157") == "1569157"
    assert canonical_odno(" 0000012345 ") == "12345"
    assert canonical_odno("0000012345") == canonical_odno("12345")


def test_canonical_none_and_empty_safe():
    assert canonical_odno(None) == ""
    assert canonical_odno("") == ""
    assert canonical_odno("0") == ""
    assert canonical_odno("000") == ""


# ── WS 체결통보: 패딩이 달라도 pending 매칭 (핵심 회귀) ────────────────────────────

def _trader_with_pending(order_no_key: str):
    """pending에 buy 1건. _apply_fill 호출 기록."""
    trader = MagicMock()
    trader.pending = {
        order_no_key: {
            "order_no": order_no_key, "symbol": "005930", "side": "buy",
            "qty": 10, "filled_so_far": 0, "strategy_name": "T",
        }
    }
    calls = []
    trader._apply_fill.side_effect = lambda *a, **k: calls.append(a)
    return trader, calls


def _exec_evt(order_no: str, qty: int = 10, price: float = 72000.0):
    return {
        "CNTG_YN": "2", "ODER_NO": order_no, "STCK_SHRN_ISCD": "005930",
        "CNTG_QTY": str(qty), "CNTG_UNPR": str(price),
        "STCK_CNTG_HOUR": "100530", "RFUS_YN": "",
    }


def test_ws_recognizes_fill_when_oder_no_unpadded(monkeypatch):
    """pending 키는 zero-padded(발주응답 ODNO), WS ODER_NO는 unpadded로 도착 —
    정확일치라면 빗나가던 체결을 canonical 매칭으로 인지해야 한다."""
    from localapp import intraday_loop
    monkeypatch.setattr(intraday_loop, "push_snapshot", lambda *a, **k: None)
    trader, calls = _trader_with_pending("0000012345")
    broker = MagicMock()
    broker.account_snapshot.return_value = {"balance": {}, "positions": []}

    intraday_loop._on_exec_event(trader, broker, _exec_evt("12345"))

    assert len(calls) == 1, "패딩이 다른 ODER_NO로 온 체결을 인지하지 못함"
    # 전량 체결 → pending에서 회수
    assert "0000012345" not in trader.pending


def test_ws_recognizes_fill_when_oder_no_padded(monkeypatch):
    """역방향: pending 키 unpadded, WS ODER_NO padded도 매칭."""
    from localapp import intraday_loop
    monkeypatch.setattr(intraday_loop, "push_snapshot", lambda *a, **k: None)
    trader, calls = _trader_with_pending("12345")
    broker = MagicMock()
    broker.account_snapshot.return_value = {"balance": {}, "positions": []}

    intraday_loop._on_exec_event(trader, broker, _exec_evt("0000012345"))

    assert len(calls) == 1
    assert "12345" not in trader.pending


def test_ws_apply_fill_uses_stored_raw_order_no(monkeypatch):
    """_apply_fill 로깅은 pending에 저장된 raw order_no를 쓴다(REST 경로와 일관)."""
    from localapp import intraday_loop
    monkeypatch.setattr(intraday_loop, "push_snapshot", lambda *a, **k: None)
    trader, calls = _trader_with_pending("0000012345")
    broker = MagicMock()
    broker.account_snapshot.return_value = {"balance": {}, "positions": []}

    intraday_loop._on_exec_event(trader, broker, _exec_evt("12345"))

    # _apply_fill(order_no, p, ...) — 첫 인자는 raw 저장값
    assert calls[0][0] == "0000012345"


def test_ws_unmatched_still_skips(monkeypatch):
    """진짜 미매칭(다른 주문번호)은 여전히 skip — canonical화가 오매칭을 만들지 않음."""
    from localapp import intraday_loop
    monkeypatch.setattr(intraday_loop, "push_snapshot", lambda *a, **k: None)
    trader, calls = _trader_with_pending("0000012345")
    broker = MagicMock()

    intraday_loop._on_exec_event(trader, broker, _exec_evt("99999"))

    assert calls == []
    assert "0000012345" in trader.pending


# ── 국내 REST order_status: 패딩 차이 매칭 ────────────────────────────────────────

def _kr_broker():
    b = KisBroker.__new__(KisBroker)
    b.virtual = True
    b.cano = "12345678"
    b.acnt_cd = "01"
    return b


def test_kr_order_status_matches_with_padding_diff(monkeypatch):
    """order_status가 daily-ccld odno와 인자 order_no의 패딩이 달라도 매칭."""
    from localapp import market_index
    monkeypatch.setattr(market_index, "is_us", lambda s: False)
    b = _kr_broker()
    b._daily_ccld = lambda: {"output1": [
        {"odno": "0000012345", "ord_qty": "10", "tot_ccld_qty": "10",
         "avg_prvs": "72000", "cncl_yn": "N", "ord_gno_brno": "00950"}
    ]}
    # 인자는 unpadded — 과거 정확일치라면 미매칭(status=unknown)이었다.
    st = b.order_status("12345", "005930")
    assert st["status"] == "filled"
    assert st["filled_qty"] == 10
