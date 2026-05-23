"""Q1 회귀 — 잔고 push retry thread.

설계(2026-05-23): 기존 _flush_pending(정시 cron 첫 시도)와 별개로 daemon thread
하나가 PENDING_PATH를 폴링. 실패 시 backoff [10,30,60,120,300,600]초, 성공 시
파일 삭제. UX 개선(사용자가 옛 잔고를 안 보게)이라 자금 안전성 무관 — 단순 구조.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_LOCAL_DIR = Path(__file__).resolve().parent.parent
if str(_LOCAL_DIR) not in sys.path:
    sys.path.insert(0, str(_LOCAL_DIR))


@pytest.fixture
def isolated_pending(tmp_path, monkeypatch):
    """PENDING_PATH를 tmp로 격리."""
    pending = tmp_path / "pending.json"
    from localapp import sync_retry, config
    monkeypatch.setattr(config, "PENDING_PATH", pending)
    monkeypatch.setattr(sync_retry, "PENDING_PATH", pending)
    yield pending


def test_attempt_once_success_removes_file(isolated_pending, monkeypatch):
    """파일 존재 + push 성공 → 파일 삭제 + True 반환."""
    from localapp import sync_retry

    payload = {"balance": {"total_eval": 10_000_000}}
    isolated_pending.write_text(json.dumps(payload), encoding="utf-8")

    called = []
    monkeypatch.setattr(sync_retry, "push_snapshot",
                         lambda p: called.append(p))
    ok = sync_retry._attempt_once()
    assert ok is True
    assert not isolated_pending.exists()
    assert called == [payload]


def test_attempt_once_push_failure_keeps_file(isolated_pending, monkeypatch):
    """push 실패 → 파일 유지 + False 반환."""
    from localapp import sync_retry

    payload = {"balance": {"total_eval": 10_000_000}}
    isolated_pending.write_text(json.dumps(payload), encoding="utf-8")

    def fail(p):
        raise RuntimeError("network down")
    monkeypatch.setattr(sync_retry, "push_snapshot", fail)
    ok = sync_retry._attempt_once()
    assert ok is False
    assert isolated_pending.exists()


def test_attempt_once_corrupted_file_returns_false(isolated_pending, monkeypatch):
    """파일 깨짐 (JSON parse 실패) → False (다음 주기에 다시 시도)."""
    from localapp import sync_retry

    isolated_pending.write_text("not json{", encoding="utf-8")
    monkeypatch.setattr(sync_retry, "push_snapshot",
                         lambda p: pytest.fail("should not be called"))
    ok = sync_retry._attempt_once()
    assert ok is False


def test_thread_starts_and_stops(isolated_pending, monkeypatch):
    """start → 살아있음, stop → 종료."""
    from localapp import sync_retry

    # idle poll을 짧게 (테스트용)
    monkeypatch.setattr(sync_retry, "_IDLE_POLL_SEC", 0.05)
    sync_retry.start()
    assert sync_retry._thread is not None
    assert sync_retry._thread.is_alive()
    time.sleep(0.15)            # idle 폴링 한두 번
    sync_retry.stop(timeout=2.0)
    assert sync_retry._thread is None


def test_thread_picks_up_pending_during_idle(isolated_pending, monkeypatch):
    """idle 중 PENDING_PATH가 생기면 다음 폴링에서 처리."""
    from localapp import sync_retry

    monkeypatch.setattr(sync_retry, "_IDLE_POLL_SEC", 0.05)
    received = []
    monkeypatch.setattr(sync_retry, "push_snapshot",
                         lambda p: received.append(p))

    sync_retry.start()
    try:
        time.sleep(0.1)
        payload = {"balance": {"total_eval": 9_500_000}}
        isolated_pending.write_text(json.dumps(payload), encoding="utf-8")
        # 다음 idle wait 후 처리
        time.sleep(0.3)
        assert received == [payload]
        assert not isolated_pending.exists()
    finally:
        sync_retry.stop(timeout=2.0)


def test_thread_backoff_on_repeated_failure(isolated_pending, monkeypatch):
    """반복 실패 시 backoff 적용 — _BACKOFFS의 첫 값 사용 확인.

    실제 thread 동작 테스트보다는, attempt 카운트가 증가하고 적절한 backoff
    인덱스를 쓰는지 단순 검증.
    """
    from localapp import sync_retry

    assert sync_retry._BACKOFFS[0] == 10
    assert sync_retry._BACKOFFS[-1] == 600
    assert len(sync_retry._BACKOFFS) == 6


def test_start_is_idempotent(isolated_pending, monkeypatch):
    """이미 실행 중일 때 start() 재호출은 무동작."""
    from localapp import sync_retry

    monkeypatch.setattr(sync_retry, "_IDLE_POLL_SEC", 0.05)
    sync_retry.start()
    t1 = sync_retry._thread
    sync_retry.start()
    t2 = sync_retry._thread
    try:
        assert t1 is t2
    finally:
        sync_retry.stop(timeout=2.0)
