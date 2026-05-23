"""Q1 — 잔고 스냅샷 push 실패분의 백그라운드 retry thread.

문제: runner._flush_pending은 정시 cron(08:55/15:35) 진입 시점에만 실행되어,
어제 15:35 push 실패가 오늘 08:55까지 약 17시간 정체됨. 사용자가 웹 Dashboard
에서 옛 잔고를 봄.

해법: 로컬앱 기동 시 daemon thread 1개를 띄워, PENDING_PATH가 존재하면
exponential backoff [10, 30, 60, 120, 300, 600]초로 재전송. 성공/없음 시
60초 idle 폴링. 자금 안전성에 직접 영향 없는 UX 개선이라 단순 구조로 충분.

기존 _flush_pending과의 관계: 정시 cron이 첫 시도, 본 thread는 사이클 외
시간대를 커버. PENDING_PATH 존재 여부를 분기로 쓰므로 중복 push 위험 없음.
"""

from __future__ import annotations

import json
import logging
import threading
import time

from .config import PENDING_PATH
from .sync_client import push_snapshot

log = logging.getLogger("localapp.sync_retry")

# Backoff schedule. 첫 실패면 10초 후, 그 다음 30/60/.../600초.
# 최대 10분 간격으로 계속 재시도 (성공 또는 PENDING_PATH 삭제 시 종료).
_BACKOFFS = [10, 30, 60, 120, 300, 600]
_IDLE_POLL_SEC = 60         # PENDING_PATH 없을 때 폴링 주기

_thread: threading.Thread | None = None
_stop_flag = threading.Event()
_lock = threading.Lock()


def _attempt_once() -> bool:
    """PENDING_PATH의 payload 1회 재전송 시도. 성공 시 파일 삭제 + True 반환."""
    try:
        payload = json.loads(PENDING_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning("[retry] PENDING_PATH 읽기 실패 — 다음 주기 재시도: %s", e)
        return False
    try:
        push_snapshot(payload)
    except Exception as e:
        log.warning("[retry] push 실패: %s", e)
        return False
    # 성공 — 파일 제거
    try:
        PENDING_PATH.unlink()
    except FileNotFoundError:
        pass
    except Exception as e:
        # unlink 실패해도 push는 성공한 상태 — 다음 주기에서 다시 보내질 수
        # 있지만 서버 측이 최신 push로 덮어쓰므로 자금 안전에 영향 없음.
        log.warning("[retry] PENDING_PATH 삭제 실패: %s", e)
    return True


def _retry_loop() -> None:
    """thread 본체. stop_flag가 set될 때까지 영구 루프.

    상태 머신:
      - PENDING_PATH 없음 → _IDLE_POLL_SEC(60) 대기 → 다시 확인
      - PENDING_PATH 있음 → _attempt_once() → 성공이면 attempt 리셋
        실패면 backoff[attempt]초 대기 후 다시 시도. attempt는 끝까지 가면 마지막 값 유지.
    """
    attempt = 0
    while not _stop_flag.is_set():
        if not PENDING_PATH.exists():
            attempt = 0
            if _stop_flag.wait(_IDLE_POLL_SEC):
                break
            continue
        ok = _attempt_once()
        if ok:
            log.info("[retry] 보류 스냅샷 재전송 성공")
            attempt = 0
            # 즉시 다시 idle 폴링으로 (혹시 누가 또 PENDING_PATH 쓰는 케이스)
            if _stop_flag.wait(1):
                break
            continue
        # 실패 → backoff
        wait = _BACKOFFS[min(attempt, len(_BACKOFFS) - 1)]
        attempt += 1
        log.warning("[retry] 재전송 시도 %d 실패 — %d초 후 재시도", attempt, wait)
        if _stop_flag.wait(wait):
            break
    log.info("[retry] thread 종료")


def start() -> None:
    """기동 시 1회 호출 (scheduler.start). 이미 실행 중이면 무동작."""
    global _thread
    with _lock:
        if _thread is not None and _thread.is_alive():
            log.info("[retry] 이미 실행 중")
            return
        _stop_flag.clear()
        t = threading.Thread(target=_retry_loop, daemon=True,
                              name="sync-retry")
        _thread = t
        t.start()
        log.info("[retry] thread 시작 (idle %ds, backoff %s)",
                  _IDLE_POLL_SEC, _BACKOFFS)


def stop(timeout: float = 5.0) -> None:
    """종료 시 호출 (단위 테스트 또는 graceful shutdown)."""
    global _thread
    _stop_flag.set()
    with _lock:
        t = _thread
        _thread = None
    if t is not None and t.is_alive():
        t.join(timeout=timeout)
