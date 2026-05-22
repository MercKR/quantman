"""S&P500 구성종목 유니버스 생성기 (개발 전용).

Wikipedia 'List of S&P 500 companies'에서 종목 목록을 받아
`quant_core/universe/sp500.json`에 저장한다. 미국 자동선택 스크리너의 큐레이션
유니버스(스테이지1)로 사용. 구성종목은 분기 단위로만 바뀌므로 가끔 재실행.

심볼은 Wikipedia 표기(클래스주는 점: BRK.B, BF.B)를 그대로 보관한다. yfinance
fetch(대시 BRK-B)·KIS 주문(슬래시 BRK/B) 변환은 사용처(데이터 수집·라우팅)에서
market_index 정규화로 처리한다.

사용: python gen_sp500.py
"""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

OUT_PATH = Path(__file__).parent / "quant_core" / "universe" / "sp500.json"
WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


def main() -> None:
    import pandas as pd

    req = urllib.request.Request(WIKI_URL, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
    table = pd.read_html(StringIO(html))[0]

    seen = set()
    rows = []
    for sym, name in zip(table["Symbol"], table["Security"]):
        s = str(sym).strip().upper()
        if not s or s in seen:
            continue
        seen.add(s)
        rows.append({"symbol": s, "name": str(name).strip()})
    rows.sort(key=lambda r: r["symbol"])

    data = {
        "source": "wikipedia:List_of_S&P_500_companies",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(rows),
        "note": "스테이지1 미국 자동선택 큐레이션 유니버스. 심볼은 Wikipedia 표기"
                "(클래스주 점 형식). yfinance/KIS 변환은 market_index 정규화로 처리.",
        "constituents": rows,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=0),
                        encoding="utf-8")
    print(f"생성 완료: {OUT_PATH}  ({len(rows)}종목)")
    print("표본:", [r["symbol"] for r in rows[:5]],
          "... 클래스주:", [r["symbol"] for r in rows if "." in r["symbol"]][:5])


if __name__ == "__main__":
    main()
