"""시장 세션 캘린더 생성기 (개발 전용).

`exchange_calendars`로 미국(XNYS) 및 한국(XKRX) 정규장 세션을 수년치 뽑아
`quant_core/calendars/{us,krx}_sessions.json`에 저장한다. 런타임(서버·로컬앱)은
이 JSON + zoneinfo만 사용하므로 exchange_calendars를 번들할 필요가 없다.

US: NYSE/NASDAQ/AMEX 공통(XNYS). 개장 09:30 ET, 정규 마감 16:00 ET, 반일장 13:00 ET.
KRX: 09:00 ~ 15:30 KST. 한국 공휴일(설/추석/광복절 등) 자동 반영.
DST는 런타임 zoneinfo가 처리하므로 여기선 현지 wall-clock("HH:MM")만 저장한다.

사용:
    python gen_market_sessions.py [--market US|KR|all]
        [--start 2024-01-01] [--end 2030-12-31]

세션 데이터는 만료 전(마지막 세션일 도래 전) 재실행해 갱신한다.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

_OUT_DIR = Path(__file__).parent / "quant_core" / "calendars"

# (시장키, 캘린더코드, tz, 파일명, 비고)
_MARKETS = {
    "US": {
        "calendar": "XNYS",
        "tz_local": "America/New_York",
        "path": _OUT_DIR / "us_sessions.json",
        "note": "NYSE/NASDAQ/AMEX 공통 정규장. 값은 ET 현지 시각[open, close]. "
                "DST는 런타임 zoneinfo가 처리. 반일장은 close=13:00.",
    },
    "KR": {
        "calendar": "XKRX",
        "tz_local": "Asia/Seoul",
        "path": _OUT_DIR / "krx_sessions.json",
        "note": "KRX(KOSPI/KOSDAQ) 정규장. 값은 KST 현지 시각[open, close]. "
                "한국 공휴일(설/추석/광복절 등)·임시휴장 반영.",
    },
}


def generate(market: str, start: str, end: str) -> dict:
    import exchange_calendars as ec

    cfg = _MARKETS[market]
    tz_local = ZoneInfo(cfg["tz_local"])
    cal = ec.get_calendar(cfg["calendar"], start=start, end=end)
    sessions: dict[str, list[str]] = {}
    for ts in cal.sessions:
        day = ts.date()
        if day.isoformat() < start or day.isoformat() > end:
            continue
        open_utc = cal.session_open(ts)
        close_utc = cal.session_close(ts)
        # UTC tz-aware → 현지 wall-clock "HH:MM"
        o_local = open_utc.tz_convert(tz_local)
        c_local = close_utc.tz_convert(tz_local)
        sessions[day.isoformat()] = [o_local.strftime("%H:%M"),
                                     c_local.strftime("%H:%M")]

    return {
        "market": market,
        "calendar": cfg["calendar"],
        "tz_local": cfg["tz_local"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "range": [start, end],
        "note": cfg["note"],
        "sessions": sessions,
    }


def _write(market: str, data: dict) -> None:
    path = _MARKETS[market]["path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=0),
                    encoding="utf-8")
    n = len(data["sessions"])
    days = sorted(data["sessions"])
    print(f"[{market}] 생성 완료: {path}")
    print(f"  세션 {n}개, 범위 {days[0]} ~ {days[-1]}")
    # 반일장(US close != 16:00, KR close != 15:30) 표본
    expected = "16:00" if market == "US" else "15:30"
    half = [(d, v) for d, v in data["sessions"].items() if v[1] != expected]
    print(f"  비표준 마감 {len(half)}개 (예: {half[:3]})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", default="all", choices=["US", "KR", "all"])
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default="2030-12-31")
    args = ap.parse_args()

    markets = [args.market] if args.market != "all" else ["US", "KR"]
    for m in markets:
        data = generate(m, args.start, args.end)
        _write(m, data)


if __name__ == "__main__":
    main()
