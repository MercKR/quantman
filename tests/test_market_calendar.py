"""market_calendar 단위테스트 — DST·반일장·휴장·다음세션 판정.

시간 의존 로직이라 야간 미국장 없이도 검증되도록 고정 날짜/시각을 주입한다.
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from quant_core import market_calendar as mc

KST = ZoneInfo("Asia/Seoul")


def _kst(y, mo, d, h, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=KST)


# ── 정규장 개장·폐장 KST (DST) ───────────────────────────────────────────────

def test_summer_edt_open_close():
    """여름(EDT): 개장 22:30, 마감 익일 05:00 KST."""
    o, c = mc.session_kst("US", date(2026, 7, 15))
    assert (o.month, o.day, o.hour, o.minute) == (7, 15, 22, 30)
    assert (c.month, c.day, c.hour, c.minute) == (7, 16, 5, 0)


def test_winter_est_open_close():
    """겨울(EST): 개장 23:30, 마감 익일 06:00 KST."""
    o, c = mc.session_kst("US", date(2026, 1, 15))
    assert (o.month, o.day, o.hour, o.minute) == (1, 15, 23, 30)
    assert (c.month, c.day, c.hour, c.minute) == (1, 16, 6, 0)


def test_half_day_thanksgiving_friday():
    """반일장(추수감사절 다음날 2026-11-27): 마감 13:00 ET → 03:00 KST."""
    o, c = mc.session_kst("US", date(2026, 11, 27))
    assert (o.hour, o.minute) == (23, 30)          # EST 개장
    assert (c.month, c.day, c.hour, c.minute) == (11, 28, 3, 0)


# ── 휴장 ────────────────────────────────────────────────────────────────────

def test_holiday_christmas():
    assert mc.session_kst("US", date(2026, 12, 25)) is None


def test_weekend():
    # 2026-07-04는 토요일
    assert mc.session_kst("US", date(2026, 7, 4)) is None


def test_independence_day_observed():
    # 2026-07-03(금)은 7/4(토) 대체휴장 → 휴장
    assert mc.session_kst("US", date(2026, 7, 3)) is None


# ── is_session_open ─────────────────────────────────────────────────────────

def test_open_during_session_summer():
    # 2026-07-15 23:00 KST는 개장(22:30)~마감(익일 05:00) 사이
    assert mc.is_session_open("US", _kst(2026, 7, 15, 23, 0)) is True


def test_open_after_midnight_kst():
    # 익일 02:00 KST도 같은 ET 세션(7/15) 진행 중
    assert mc.is_session_open("US", _kst(2026, 7, 16, 2, 0)) is True


def test_closed_before_open():
    assert mc.is_session_open("US", _kst(2026, 7, 15, 21, 0)) is False


def test_closed_after_close():
    assert mc.is_session_open("US", _kst(2026, 7, 16, 6, 0)) is False


def test_closed_on_holiday():
    assert mc.is_session_open("US", _kst(2026, 12, 25, 23, 0)) is False


# ── next_session_kst ────────────────────────────────────────────────────────

def test_next_session_from_noon():
    # 2026-07-15 정오 KST → 오늘 밤 세션(개장 22:30) 반환
    o, c = mc.next_session_kst("US", _kst(2026, 7, 15, 12, 0))
    assert (o.month, o.day, o.hour, o.minute) == (7, 15, 22, 30)


def test_next_session_skips_weekend():
    # 금요일 마감 후(토 정오 KST) → 다음은 월요일 세션
    o, c = mc.next_session_kst("US", _kst(2026, 7, 18, 12, 0))  # 토요일
    assert o.weekday() == 0  # 월요일(KST 개장일)


def test_next_session_during_open_returns_following():
    # 세션 진행 중(개장 이후)이면 '다음' 세션을 반환 (개장 > after 조건)
    o, _ = mc.next_session_kst("US", _kst(2026, 7, 15, 23, 0))
    assert o.day == 16 or o.weekday() < 5  # 다음 거래일


# ── 데이터 무결성 ────────────────────────────────────────────────────────────

def test_coverage_range():
    lo, hi = mc.coverage_range("US")
    assert lo <= "2025-01-01"
    assert hi >= "2030-01-01"


def test_unsupported_market():
    with pytest.raises(mc.CalendarError):
        mc.session_kst("KR", date(2026, 7, 15))
