"""Kill switch — 일일 손실 한도 초과 시 자동 청산 + 신규 진입 차단.

사용자가 명시적으로 reset할 때까지 유지된다.
파일 기반 단순 state — 동시 접근 가정 없음 (로컬앱 단일 인스턴스).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from .config import KILLSWITCH_PATH
from .state_store import save_json

log = logging.getLogger("localapp.killswitch")


def load() -> dict:
    """현재 상태 반환. 없으면 {'active': False, ...}."""
    if not KILLSWITCH_PATH.exists():
        return {"active": False, "since": None, "reason": "",
                "day_start_equity": None, "day_start_date": None}
    try:
        return json.loads(KILLSWITCH_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning("kill switch 파일 파싱 실패, 초기화: %s", e)
        return {"active": False, "since": None, "reason": "",
                "day_start_equity": None, "day_start_date": None}


def save(state: dict) -> None:
    """원자적 저장 + owner-only ACL — state_store 단일 경로 위임 (R5).

    이전엔 plain write_text라 원자성·ACL 둘 다 없었다 (A-1 보안 갭): 손실한도·
    day_start_equity는 같은 PC 타 사용자에게 노출되면 안 되고, 쓰는 중 종료 시
    파일이 깨지면 killswitch 상태를 잃어 손실 한도 차단이 무력화될 수 있었다.
    """
    save_json(KILLSWITCH_PATH, state)


def activate(reason: str) -> dict:
    """Kill switch 발동."""
    state = load()
    state["active"] = True
    state["since"] = datetime.now(timezone.utc).isoformat()
    state["reason"] = reason
    save(state)
    log.critical("KILL SWITCH 발동: %s", reason)
    return state


def reset() -> dict:
    """사용자 명령으로 해제. 다음 사이클부터 정상 동작."""
    state = load()
    was_active = state.get("active", False)
    state["active"] = False
    state["since"] = None
    state["reason"] = ""
    # day_start_equity는 그날 자정 직후 새로 잡힘 — 여기선 유지
    save(state)
    if was_active:
        log.info("kill switch reset")
    return state


def is_active() -> bool:
    return bool(load().get("active", False))


def update_day_start(equity: float, today_iso: str) -> dict:
    """오늘 자정 이후 첫 호출이면 day_start_equity를 갱신."""
    state = load()
    if state.get("day_start_date") != today_iso:
        state["day_start_date"] = today_iso
        state["day_start_equity"] = float(equity)
        save(state)
    return state


def check_daily_loss(current_equity: float, limit_pct: float) -> Optional[str]:
    """현재 평가금액과 day_start_equity를 비교. 한도 초과 시 발동 사유 반환."""
    state = load()
    start = state.get("day_start_equity")
    if not start or start <= 0:
        return None
    loss_pct = (current_equity - start) / start * 100
    if loss_pct <= -abs(limit_pct):
        return f"일일 손실 한도 도달 ({loss_pct:.2f}% ≤ −{limit_pct:.2f}%)"
    return None
