"""사용자별 모니터링 설정 — 알림 webhook URL 등."""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from ..db import get_session
from ..deps import get_current_user
from ..models import User, UserSettings
from ..schemas import UserSettingsIO

router = APIRouter(prefix="/settings", tags=["settings"])

# 알림 webhook 허용 호스트 — UI가 안내하는 Discord/Slack 두 곳만.
# 임의 URL을 저장하면 서버가 그 주소로 POST하므로 SSRF(내부망·메타데이터 IP)에
# 노출된다. 도메인 allowlist로 egress 대상을 고정해 근본 차단한다.
_ALLOWED_WEBHOOK_HOSTS = ("discord.com", "discordapp.com", "hooks.slack.com")


def _validate_webhook_url(url: str) -> None:
    """webhook URL을 https + Discord/Slack 도메인으로 제한 (SSRF 방어)."""
    if not url:
        return  # 빈 값 = 알림 비활성, 허용
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "webhook URL은 https만 허용됩니다.")
    host = (parsed.hostname or "").lower()
    allowed = host in _ALLOWED_WEBHOOK_HOSTS or host.endswith(".discord.com")
    if not allowed:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Discord(discord.com) 또는 Slack(hooks.slack.com) webhook URL만 허용됩니다.")


def _get_or_create(session: Session, user_id: int) -> UserSettings:
    s = session.get(UserSettings, user_id)
    if s is None:
        s = UserSettings(user_id=user_id)
        session.add(s)
        session.commit()
        session.refresh(s)
    return s


@router.get("", response_model=UserSettingsIO)
def get_settings(user: User = Depends(get_current_user),
                  session: Session = Depends(get_session)):
    s = _get_or_create(session, user.id)
    return UserSettingsIO(
        alert_webhook_url=s.alert_webhook_url,
        alert_on_killswitch=s.alert_on_killswitch,
        alert_on_daily_loss_pct=s.alert_on_daily_loss_pct,
        alert_on_unfilled_count=s.alert_on_unfilled_count,
        kill_switch_daily_loss_pct=s.kill_switch_daily_loss_pct,
        max_drawdown_pct=s.max_drawdown_pct,
        preview_missing_alert_threshold=s.preview_missing_alert_threshold,
        alert_on_reconcile_drift=s.alert_on_reconcile_drift,
        us_buying_power_mode=s.us_buying_power_mode,
    )


@router.put("", response_model=UserSettingsIO)
def put_settings(body: UserSettingsIO,
                  user: User = Depends(get_current_user),
                  session: Session = Depends(get_session)):
    s = _get_or_create(session, user.id)
    _validate_webhook_url(body.alert_webhook_url)
    s.alert_webhook_url = body.alert_webhook_url
    s.alert_on_killswitch = body.alert_on_killswitch
    s.alert_on_daily_loss_pct = body.alert_on_daily_loss_pct
    s.alert_on_unfilled_count = body.alert_on_unfilled_count
    # Phase 38.7/38.10 — null이면 기존 값 유지 안 하고 null 그대로 저장 (default로 fallback)
    # 사용자 입력 1~10/1~50% 범위 검증
    if body.kill_switch_daily_loss_pct is not None:
        if not (0.5 <= body.kill_switch_daily_loss_pct <= 20.0):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "kill_switch_daily_loss_pct는 0.5~20.0 범위여야 합니다.")
    if body.max_drawdown_pct is not None:
        if not (1.0 <= body.max_drawdown_pct <= 80.0):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "max_drawdown_pct는 1.0~80.0 범위여야 합니다.")
    s.kill_switch_daily_loss_pct = body.kill_switch_daily_loss_pct
    s.max_drawdown_pct = body.max_drawdown_pct
    s.preview_missing_alert_threshold = max(1, int(body.preview_missing_alert_threshold))
    s.alert_on_reconcile_drift = body.alert_on_reconcile_drift
    if body.us_buying_power_mode not in ("integrated", "usd_cash"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "us_buying_power_mode는 'integrated' 또는 'usd_cash'여야 합니다.")
    s.us_buying_power_mode = body.us_buying_power_mode
    s.updated_at = datetime.now(timezone.utc)
    session.add(s)
    session.commit()
    return body
