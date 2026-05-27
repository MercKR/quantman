"""KIS 정기 점검 시간대 실측 — 가드 범위 좁히기 위한 데이터 수집.

배경
----
`trader.py::_in_kis_maintenance_window`는 평일 03:00~06:00, 토 17:00~월 07:00을
점검 시간대로 *추정*해 cycle을 차단한다. KIS 공식 doc에 점검 시간이 없어
보수적으로 잡은 범위지만, 미장 마감(KST 05:00) 직전 매수 catch-up이 차단되는
부작용이 있다. 이 스크립트가 며칠 누적한 데이터로 *진짜* 점검 윈도우를
도출해 가드 범위를 좁힌다.

측정 대상 endpoint (자동매매가 catch-up에서 실제 호출하는 것들):
  - HHDFS76200200 — 해외 시세 (현재가상세, v0.9.7 fix 대상)
  - FHKST01010100 — 국내 시세 (현재가)
  - VTTC8434R / TTTC8434R — 잔고 조회

호출 형식
---------
    python -m tools.probe_kis_maintenance [--interval 300] [--once]

옵션
----
  --interval N    호출 간격(초). 기본 300 = 5분. KIS rate-limit 영향 없음.
  --once          1회만 호출 후 종료 (cron job 패턴).

기본은 무한 loop — 사용자가 Ctrl+C로 종료. 결과는
`~/.quant-platform/probes/kis_maintenance.jsonl`에 한 줄씩 append.

분석 권장
---------
며칠 누적 후:
    cat ~/.quant-platform/probes/kis_maintenance.jsonl | jq -c \\
        'select(.ok == false) | {ts, endpoint, rt_cd, msg_cd, err}' | head -50

응답이 "정상"(rt_cd=0)인 시간대 vs "비정상"인 시간대 → 진짜 점검 범위 도출.
GOTCHAS.md에 기록 후 trader.py 가드 범위 fix.

보안
----
KIS 자격증명은 로컬 PC 전용 (보안 원칙). 이 스크립트는 서버에 어떤 데이터도
전송하지 않는다 — 로컬 JSONL 누적만.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# localapp 경로 — 이 스크립트는 platform/local/tools/에 위치, parent가 localapp.
_HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_HERE))

from localapp.kis_broker import KisBroker  # noqa: E402
from localapp.config import APP_DIR  # noqa: E402

KST = ZoneInfo("Asia/Seoul")
OUT_PATH = APP_DIR / "probes" / "kis_maintenance.jsonl"


def _probe_one(broker: KisBroker, endpoint: str, tr: str, path: str,
                params: dict, base_attr: str) -> dict:
    """한 endpoint 호출 + 결과 dict.

    예외/응답 모두 동일 형식으로 기록 — 분석 시 일관성 위해.
    """
    started = time.perf_counter()
    rec = {
        "ts": datetime.now(KST).isoformat(timespec="seconds"),
        "endpoint": endpoint,
        "tr_id": tr,
    }
    try:
        body = broker._get_retry(
            path, tr, params,
            base=getattr(broker, base_attr),
        )
        rt_cd = body.get("rt_cd")
        rec.update({
            "ok": rt_cd == "0",
            "rt_cd": rt_cd,
            "msg_cd": body.get("msg_cd"),
            "msg1": (body.get("msg1") or "")[:80],
            "latency_ms": int((time.perf_counter() - started) * 1000),
        })
    except Exception as e:
        rec.update({
            "ok": False,
            "err": f"{type(e).__name__}: {str(e)[:100]}",
            "latency_ms": int((time.perf_counter() - started) * 1000),
        })
    return rec


def _probe_round(broker: KisBroker) -> list[dict]:
    """한 라운드 = 3 endpoint 호출."""
    out = []

    # 1) 해외 시세 (HHDFS76200200) — AAPL
    out.append(_probe_one(
        broker,
        endpoint="overseas_quote",
        tr="HHDFS76200200",
        path="/uapi/overseas-price/v1/quotations/price-detail",
        params={"AUTH": "", "EXCD": "NAS", "SYMB": "AAPL"},
        base_attr="quote_base",
    ))

    # 2) 국내 시세 (FHKST01010100) — 삼성전자
    out.append(_probe_one(
        broker,
        endpoint="domestic_quote",
        tr="FHKST01010100",
        path="/uapi/domestic-stock/v1/quotations/inquire-price",
        params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": "005930"},
        base_attr="quote_base",
    ))

    # 3) 잔고 조회 — 모의/실전 분기
    bal_tr = "VTTC8434R" if broker.virtual else "TTTC8434R"
    out.append(_probe_one(
        broker,
        endpoint="balance",
        tr=bal_tr,
        path="/uapi/domestic-stock/v1/trading/inquire-balance",
        params={
            "CANO": broker.cano, "ACNT_PRDT_CD": broker.acnt_cd,
            "AFHR_FLPR_YN": "N", "OFL_YN": "", "INQR_DVSN": "02",
            "UNPR_DVSN": "01", "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N", "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "", "CTX_AREA_NK100": "",
        },
        base_attr="base",
    ))

    return out


def _append(records: list[dict]) -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> None:
    # cp949 console에서 한글 출력 가능하게 — Windows PowerShell 기본 인코딩 우회.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    ap = argparse.ArgumentParser(description="KIS 점검 시간대 실측 probe")
    ap.add_argument("--interval", type=int, default=300,
                     help="호출 간격(초). 기본 300=5분.")
    ap.add_argument("--once", action="store_true",
                     help="1회 호출 후 종료 (cron job 패턴).")
    args = ap.parse_args()

    try:
        broker = KisBroker()
    except Exception as e:
        print(f"KIS 자격증명 로드 실패: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[probe] 시작 - interval={args.interval}s, output={OUT_PATH}")

    while True:
        try:
            records = _probe_round(broker)
            _append(records)
            now = datetime.now(KST).strftime("%H:%M:%S")
            summary = " ".join(f"{r['endpoint']}={'OK' if r['ok'] else 'FAIL'}"
                                for r in records)
            print(f"[{now}] {summary}")
        except KeyboardInterrupt:
            print("\n[probe] 종료 (Ctrl+C)")
            break
        except Exception:
            # 예외도 기록 — 점검 시간대 응답이 raise할 가능성.
            traceback.print_exc()
            _append([{
                "ts": datetime.now(KST).isoformat(timespec="seconds"),
                "endpoint": "probe_error",
                "ok": False,
                "err": traceback.format_exc()[-200:],
            }])

        if args.once:
            break
        try:
            time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n[probe] 종료 (Ctrl+C)")
            break


if __name__ == "__main__":
    main()
