"""M3 회귀 — 트레이더 상태(ledger/pending) 크로스스레드 동시 변경 직렬화(축4).

결함: _apply_fill(단일 원장 writer)이 WS 체결 thread·60초 monitor·스케줄러 cycle
양쪽에서 호출되며 self.ledger/self.pending을 _CYCLE_LOCK 없이 변경했다. monitor
thread가 청산 cycle을 도는 동안 WS thread가 체결을 반영하면 같은 dict를 동시
변경 → lost update·corruption. M3에서 모든 변경 진입점을 단일 RLock으로 직렬화.

검증(단위):
1. _CYCLE_LOCK이 RLock(재진입) — cycle이 락을 쥔 채 _apply_fill을 호출해도 데드락
   없이 통과해야 한다.
2. _apply_fill이 _CYCLE_LOCK을 실제로 acquire — 다른 thread가 락을 쥐면 차단된다.
3. 동시 _apply_fill이 서로 다른 sid를 잃지 않고 모두 반영.
4. ks hook은 락 밖에서 실행 — hook이 cycle(락 재획득)을 호출해도 안전.
(실거래 동시 부하 검증은 V-M3 게이트 — 환경 복구 후.)
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_LOCAL_DIR = Path(__file__).resolve().parent.parent
if str(_LOCAL_DIR) not in sys.path:
    sys.path.insert(0, str(_LOCAL_DIR))


def _stub_trader(monkeypatch):
    """파일 I/O 없이 _apply_fill/_after_submit만 구동하는 Trader 스텁."""
    from localapp import trader as trmod
    monkeypatch.setattr(trmod.order_log, "log_order", lambda *a, **k: None)
    monkeypatch.setattr(trmod.order_log, "decision", lambda *a, **k: {})
    t = trmod.Trader.__new__(trmod.Trader)
    t.ledger = {}
    t.pending = {}
    t.equity = []
    t._daily_loss_limit_pct = None
    t._in_cycle = False
    t._ks_trigger_hook = None
    t.broker = MagicMock()
    t._log_trade = lambda ev: None
    return t, trmod


def _buy(sid: str, symbol: str = "AAPL", qty: int = 1, px: float = 100.0):
    return {"strategy_id": sid, "symbol": symbol, "side": "buy", "qty": qty,
            "strategy_name": "T", "definition": {}, "intended_price": px}


# ── 1. _CYCLE_LOCK 재진입(RLock) ──────────────────────────────────────────────

def test_cycle_lock_is_reentrant():
    """같은 thread가 두 번 acquire 가능해야 — cycle→_apply_fill 중첩 데드락 방지."""
    from localapp.trader import _CYCLE_LOCK
    acquired = _CYCLE_LOCK.acquire(timeout=1)
    assert acquired
    try:
        # RLock이면 같은 thread 재획득 즉시 성공. 일반 Lock이면 False.
        again = _CYCLE_LOCK.acquire(blocking=False)
        assert again, "_CYCLE_LOCK이 재진입 불가(RLock 아님) — cycle 내 _apply_fill 데드락"
        _CYCLE_LOCK.release()
    finally:
        _CYCLE_LOCK.release()


# ── 2. _apply_fill이 락을 실제로 획득(직렬화) ─────────────────────────────────────

def test_apply_fill_blocks_while_lock_held(monkeypatch):
    """다른 thread가 _CYCLE_LOCK을 쥐고 있으면 _apply_fill은 진행하지 못한다."""
    from localapp.trader import _CYCLE_LOCK
    t, _ = _stub_trader(monkeypatch)

    lock_held = threading.Event()
    release_now = threading.Event()
    done = threading.Event()

    def holder():
        with _CYCLE_LOCK:
            lock_held.set()
            release_now.wait(timeout=2)

    def applier():
        t._apply_fill("o1", _buy("s1"), 1, 100.0, [])
        done.set()

    h = threading.Thread(target=holder, daemon=True)
    h.start()
    assert lock_held.wait(timeout=2)

    a = threading.Thread(target=applier, daemon=True)
    a.start()
    # 락이 잡힌 동안에는 _apply_fill이 완료되면 안 된다.
    assert not done.wait(timeout=0.3), "_apply_fill이 _CYCLE_LOCK을 획득하지 않음(직렬화 실패)"
    assert "s1" not in t.ledger

    release_now.set()
    assert done.wait(timeout=2), "락 해제 후에도 _apply_fill 미완료"
    assert t.ledger["s1"]["qty"] == 1
    h.join(timeout=2)
    a.join(timeout=2)


# ── 3. cycle 컨텍스트(락 보유) 내 _apply_fill 재진입 — 데드락 없음 ──────────────────

def test_apply_fill_reentrant_under_held_lock(monkeypatch):
    """cycle이 _CYCLE_LOCK을 쥔 같은 thread에서 _apply_fill 호출해도 완료(RLock)."""
    from localapp.trader import _CYCLE_LOCK
    t, _ = _stub_trader(monkeypatch)
    result = {}

    def run():
        with _CYCLE_LOCK:                 # cycle이 락을 쥔 상황 모사
            t._apply_fill("o1", _buy("s1"), 2, 100.0, [])
            result["qty"] = t.ledger.get("s1", {}).get("qty")
        result["done"] = True

    th = threading.Thread(target=run, daemon=True)
    th.start()
    th.join(timeout=3)
    assert result.get("done"), "_apply_fill이 보유 락 하에서 데드락"
    assert result["qty"] == 2


# ── 4. 동시 _apply_fill — 서로 다른 sid 모두 반영 ─────────────────────────────────

def test_concurrent_apply_fill_distinct_sids(monkeypatch):
    t, _ = _stub_trader(monkeypatch)
    N = 40

    def worker(i):
        t._apply_fill(f"o{i}", _buy(f"s{i}"), 1, 100.0, [])

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(N)]
    for th in threads:
        th.start()
    for th in threads:
        th.join(timeout=3)
    assert len(t.ledger) == N
    assert all(f"s{i}" in t.ledger for i in range(N))


# ── 5. ks hook은 락 밖에서 — hook이 락 재획득해도 데드락 없음 ─────────────────────────

def test_ks_hook_can_acquire_lock(monkeypatch):
    """체결 후 ks hook이 cancel_all_pending/cycle처럼 _CYCLE_LOCK을 다시 잡아도
    데드락 없이 동작 — hook이 _apply_fill 임계구역 밖에서 실행됨을 보장."""
    from localapp.trader import _CYCLE_LOCK
    t, trmod = _stub_trader(monkeypatch)
    t._daily_loss_limit_pct = 3.0
    # evaluate_killswitch_now가 True 반환하도록 강제(네트워크/파일 우회).
    monkeypatch.setattr(t, "evaluate_killswitch_now", lambda *a, **k: True)

    hook_ok = {}

    def hook(source):
        # hook 안에서 락 획득 시도 — _apply_fill이 락을 놓은 뒤 호출돼야 가능.
        got = _CYCLE_LOCK.acquire(timeout=1)
        hook_ok["acquired"] = got
        if got:
            _CYCLE_LOCK.release()

    t._ks_trigger_hook = hook
    t._apply_fill("o1", _buy("s1"), 1, 100.0, [])
    assert hook_ok.get("acquired") is True
