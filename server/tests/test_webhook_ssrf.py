"""S-04 회귀 — webhook URL SSRF 방어.

버그: 사용자가 임의 URL(localhost·169.254.169.254·사설 IP)을 alert_webhook_url로
저장하면 서버가 그 주소로 POST → SSRF. 수정: 저장 시 https + Discord/Slack 도메인
allowlist 검증. 허용 외 URL은 400.

네트워크 없이 인메모리 SQLite + 최소 앱(settings 라우터)으로 양·음성 검증.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

_SERVER_DIR = Path(__file__).resolve().parent.parent
if str(_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(_SERVER_DIR))

from app.db import get_session
from app.models import User
from app.routers import settings as settings_router
from app.security import create_access_token

_FULL = {
    "alert_webhook_url": "",
    "alert_on_killswitch": True,
    "alert_on_daily_loss_pct": 2.0,
    "alert_on_unfilled_count": 5,
    "kill_switch_daily_loss_pct": None,
    "max_drawdown_pct": None,
    "preview_missing_alert_threshold": 3,
    "alert_on_reconcile_drift": True,
    "us_buying_power_mode": "integrated",
}


def _build():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        user = User(email="t@example.com")
        s.add(user); s.commit(); s.refresh(user)
        user_id = user.id

    app = FastAPI()
    app.include_router(settings_router.router)

    def _override():
        with Session(engine) as s:
            yield s
    app.dependency_overrides[get_session] = _override
    return TestClient(app), create_access_token(user_id)


def _put(client, tok, url):
    body = dict(_FULL, alert_webhook_url=url)
    return client.put("/settings", json=body,
                      headers={"Authorization": f"Bearer {tok}"})


# ── 양성: Discord/Slack/빈값 허용 ─────────────────────────────────────────────

@pytest.mark.parametrize("url", [
    "",                                                # 빈 값 = 알림 비활성
    "https://discord.com/api/webhooks/123/abc",
    "https://discordapp.com/api/webhooks/123/abc",
    "https://ptb.discord.com/api/webhooks/123/abc",
    "https://hooks.slack.com/services/T/B/x",
])
def test_allows_known_webhooks(url):
    client, tok = _build()
    assert _put(client, tok, url).status_code == 200


# ── 음성: SSRF·비-allowlist URL 거부 ──────────────────────────────────────────

@pytest.mark.parametrize("url", [
    "http://discord.com/api/webhooks/123/abc",         # http 거부
    "http://localhost:8000/admin",                     # 내부망
    "http://127.0.0.1/x",                              # loopback
    "http://169.254.169.254/latest/meta-data/",        # 클라우드 메타데이터
    "https://evil.example.com/webhook",                # 임의 도메인
    "https://discord.com.evil.com/webhook",            # 도메인 위장
    "https://notdiscord.com/webhook",
])
def test_rejects_ssrf_and_unknown(url):
    client, tok = _build()
    assert _put(client, tok, url).status_code == 400
