"""실행 가능한 머니패스 불변식 단언. ID는 docs/INVARIANTS.md와 1:1 대응."""
from __future__ import annotations


def check_ledger_nonneg(trader) -> None:
    """INV-LEDGER-1: ledger에 남은 포지션의 qty는 양수다(0 이하는 삭제됨)."""
    for sid, lg in trader.ledger.items():
        assert lg["qty"] > 0, f"INV-LEDGER-1 위반: {sid} qty={lg['qty']}"


def check_pending_has_order_no(trader) -> None:
    """INV-CONC-1 보조: 모든 pending 엔트리는 raw order_no를 보유(KIS 라운드트립)."""
    for key, p in trader.pending.items():
        assert p.get("order_no"), f"pending[{key}]에 order_no 없음"


def check_all(trader) -> None:
    check_ledger_nonneg(trader)
    check_pending_has_order_no(trader)
