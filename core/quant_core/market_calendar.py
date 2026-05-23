"""시장 정규장 캘린더 — 런타임 (의존성: stdlib zoneinfo만).

미국(NYSE/NASDAQ/AMEX) 정규장 세션을 `calendars/us_sessions.json`에서 읽어
KST 기준 개장·폐장 시각을 돌려준다. JSON은 `gen_market_sessions.py`가
exchange_calendars로 미리 생성한다(개발 전용). DST는 zoneinfo가 처리한다.

서버 preview와 로컬앱 스케줄러가 이 모듈 하나를 공유해 "지금 미국장 열렸나",
"오늘 밤 미국 세션이 몇 시에 열리나"를 동일하게 판정한다.

KST 환산 예:
  - 여름(EDT): 개장 09:30 ET → 22:30 KST, 마감 16:00 ET → 익일 05:00 KST
  - 겨울(EST): 개장 09:30 ET → 23:30 KST, 마감 16:00 ET → 익일 06:00 KST
  - 반일장   : 마감 13:00 ET → 02:00/03:00 KST
"""

from __future__ import annotations

import json
from datetime import date, datetime, time
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")

_CAL_DIR = Path(__file__).parent / "calendars"
_FILES = {
    "US": _CAL_DIR / "us_sessions.json",
    "KR": _CAL_DIR / "krx_sessions.json",
}


class CalendarError(RuntimeError):
    """세션 데이터 누락·만료 등 캘린더 사용 불가 상태."""


@lru_cache(maxsize=4)
def _load(market: str) -> dict:
    """시장 세션 JSON을 로드(메모이즈). market은 'US' 등."""
    path = _FILES.get(market)
    if path is None:
        raise CalendarError(f"지원하지 않는 시장: {market}")
    if not path.exists():
        raise CalendarError(
            f"세션 데이터 없음: {path} — gen_market_sessions.py로 생성하세요.")
    data = json.loads(path.read_text(encoding="utf-8"))
    tz_local = ZoneInfo(data["tz_local"])
    # 정렬된 세션일 + tz_local을 함께 캐시
    return {
        "tz_local": tz_local,
        "sessions": data["sessions"],
        "sorted_days": sorted(data["sessions"].keys()),
        "range": data.get("range", []),
    }


def _to_kst(day: date, hhmm: str, tz_local: ZoneInfo) -> datetime:
    """현지 wall-clock 'HH:MM'을 해당 날짜의 현지 tz로 묶고 KST로 변환.

    datetime.combine + astimezone이 ET→KST의 날짜 넘김(마감이 익일 새벽)과
    DST를 모두 정확히 처리한다.
    """
    h, m = (int(x) for x in hhmm.split(":"))
    local_dt = datetime.combine(day, time(h, m), tz_local)
    return local_dt.astimezone(KST)


def session_kst(market: str, day: date) -> tuple[datetime, datetime] | None:
    """해당 ET 세션일의 (개장, 폐장) KST tz-aware. 휴장이면 None.

    `day`는 미국 현지(ET) 기준 날짜다. 반환되는 폐장 시각은 KST로 익일 새벽이
    될 수 있다(정규장이 자정을 넘김).
    """
    cal = _load(market)
    rec = cal["sessions"].get(day.isoformat())
    if rec is None:
        return None
    o = _to_kst(day, rec[0], cal["tz_local"])
    c = _to_kst(day, rec[1], cal["tz_local"])
    return o, c


def _now_kst(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(KST)
    if now.tzinfo is None:
        return now.replace(tzinfo=KST)
    return now.astimezone(KST)


def is_session_open(market: str, now: datetime | None = None) -> bool:
    """now(기본 현재, KST 가정) 시점에 해당 시장 정규장이 열려 있는가.

    now를 ET 날짜로 환산해 그 세션의 [개장, 폐장] KST 구간에 포함되는지 본다.
    정규장이 자정을 넘기는 경우(KST 새벽)도 ET 날짜가 같으므로 정확하다.
    """
    cal = _load(market)
    now_kst = _now_kst(now)
    et_day = now_kst.astimezone(cal["tz_local"]).date()
    sess = session_kst(market, et_day)
    if sess is None:
        return False
    return sess[0] <= now_kst <= sess[1]


def next_session_kst(market: str,
                     after: datetime | None = None
                     ) -> tuple[datetime, datetime] | None:
    """after(기본 현재, KST 가정) 이후 가장 빠른 세션의 (개장, 폐장) KST.

    개장 시각이 after보다 뒤인 첫 세션을 반환. 데이터가 만료(after가 마지막
    세션일을 지남)됐는데 못 찾으면 CalendarError — 조용히 멈추지 않도록.
    """
    cal = _load(market)
    after_kst = _now_kst(after)
    # ET 날짜 기준으로 후보 범위를 좁힌다(전일부터 — 자정 넘김 세션 포함).
    start_day = (after_kst.astimezone(cal["tz_local"]).date()).isoformat()
    found = None
    for d in cal["sorted_days"]:
        if d < start_day:
            continue
        o, c = session_kst(market, date.fromisoformat(d))
        if o > after_kst:
            found = (o, c)
            break
    if found is None:
        last = cal["sorted_days"][-1] if cal["sorted_days"] else "?"
        raise CalendarError(
            f"{market} 다음 세션을 찾지 못함 — 세션 데이터가 만료됐을 수 있음 "
            f"(마지막 {last}). gen_market_sessions.py로 재생성하세요.")
    return found


def coverage_range(market: str) -> tuple[str, str]:
    """세션 데이터가 커버하는 [시작, 끝] ISO 날짜."""
    cal = _load(market)
    days = cal["sorted_days"]
    return (days[0], days[-1]) if days else ("", "")


def is_session_day(market: str, day: date) -> bool:
    """해당 날짜가 정규장 거래일인가 (휴장이면 False).

    KRX cron 게이트: 평일이라도 한국 공휴일(설/추석/광복절 등)이면 False.
    'today is open'과 다름 — is_session_open은 현재 시각이 정규장 구간인지 본다.
    L-03 수정: cycle/intraday/settlement 진입 전에 호출해 휴장일 매도·발주 차단.
    """
    cal = _load(market)
    return day.isoformat() in cal["sessions"]
