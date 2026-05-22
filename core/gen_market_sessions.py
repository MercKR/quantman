"""미국 시장 세션 캘린더 생성기 (개발 전용).

`exchange_calendars`(XNYS)로 NYSE/NASDAQ/AMEX 정규장 세션을 수년치 뽑아
`quant_core/calendars/us_sessions.json`에 저장한다. 런타임(서버·로컬앱)은 이
JSON + zoneinfo만 사용하므로 exchange_calendars를 번들할 필요가 없다.

NYSE/NASDAQ/AMEX는 동일한 정규장 캘린더(휴장일·반일장·시각)를 쓰므로 XNYS 하나로
"US" 키에 저장한다. 개장은 항상 09:30 ET, 정규 마감 16:00 ET, 반일장 13:00 ET.
DST는 런타임 zoneinfo가 처리하므로 여기선 ET 현지 wall-clock("HH:MM")만 저장한다.

사용:
    python gen_market_sessions.py [--start 2024-01-01] [--end 2030-12-31]

세션 데이터는 만료 전(마지막 세션일 도래 전) 재실행해 갱신한다.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

OUT_PATH = Path(__file__).parent / "quant_core" / "calendars" / "us_sessions.json"
ET = ZoneInfo("America/New_York")


def generate(start: str, end: str) -> dict:
    import exchange_calendars as ec
    import pandas as pd

    cal = ec.get_calendar("XNYS", start=start, end=end)
    sessions: dict[str, list[str]] = {}
    for ts in cal.sessions:
        day = ts.date()
        if day.isoformat() < start or day.isoformat() > end:
            continue
        open_utc = cal.session_open(ts)
        close_utc = cal.session_close(ts)
        # UTC tz-aware → ET 현지 wall-clock "HH:MM"
        o_et = open_utc.tz_convert(ET)
        c_et = close_utc.tz_convert(ET)
        sessions[day.isoformat()] = [o_et.strftime("%H:%M"), c_et.strftime("%H:%M")]

    return {
        "market": "US",
        "calendar": "XNYS",
        "tz_local": "America/New_York",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "range": [start, end],
        "note": "NYSE/NASDAQ/AMEX 공통 정규장. 값은 ET 현지 시각[open, close]. "
                "DST는 런타임 zoneinfo가 처리. 반일장은 close=13:00.",
        "sessions": sessions,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default="2030-12-31")
    args = ap.parse_args()

    data = generate(args.start, args.end)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=0),
                        encoding="utf-8")
    n = len(data["sessions"])
    days = sorted(data["sessions"])
    print(f"생성 완료: {OUT_PATH}")
    print(f"  세션 {n}개, 범위 {days[0]} ~ {days[-1]}")
    # 반일장(close != 16:00) 표본 출력 — 검증용
    half = [(d, v) for d, v in data["sessions"].items() if v[1] != "16:00"]
    print(f"  반일장 {len(half)}개 (예: {half[:3]})")


if __name__ == "__main__":
    main()
