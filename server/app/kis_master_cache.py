"""KIS 종목마스터 서버 캐시.

KIS가 공개 URL로 매일 배포하는 KOSPI/KOSDAQ .mst 파일을 서버가 직접 다운로드해
메모리에 캐싱한다. 모든 사용자에게 공유되므로 사용자별 로컬앱 push가 불필요.

- 시작 시 1회 다운로드 (lifespan에서 호출)
- APScheduler가 매일 06:00 KST에 갱신
- 다운로드 실패 시 직전 값 유지 (graceful degradation)
"""

from __future__ import annotations

import io
import logging
import threading
import urllib.request
import zipfile
from datetime import datetime, timezone

log = logging.getLogger("app.kis_master")

KOSPI_URL = "https://new.real.download.dws.co.kr/common/master/kospi_code.mst.zip"
KOSDAQ_URL = "https://new.real.download.dws.co.kr/common/master/kosdaq_code.mst.zip"

# 마스터별 메타(고정폭 끝부분) 길이 — KIS 공식 sample 코드 기준
_META_LEN = {"KOSPI": 228, "KOSDAQ": 222}

_lock = threading.Lock()
_state = {
    "symbols": set(),     # set[str] — 단축 코드
    "by_symbol": {},      # {code: {"name": ..., "market": ...}}
    "fetched_at": None,   # datetime | None
    "n_kospi": 0,
    "n_kosdaq": 0,
}


def get_master_list() -> list[dict]:
    """캐시된 KIS 마스터 전 종목 — [{symbol, name, market, kind}, ...]."""
    with _lock:
        return [{"symbol": code,
                  "name": meta.get("name", ""),
                  "market": meta.get("market", ""),
                  "kind": meta.get("kind", "stock")}
                for code, meta in _state["by_symbol"].items()]


def _download_mst(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "quant-platform-server"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        zdata = r.read()
    with zipfile.ZipFile(io.BytesIO(zdata)) as z:
        name = next((n for n in z.namelist() if n.endswith(".mst")), None)
        if name is None:
            raise RuntimeError(f"ZIP 내부에 .mst가 없습니다: {z.namelist()}")
        return z.read(name)


def _parse_master(raw: bytes, market: str) -> list[dict]:
    """KOSPI/KOSDAQ .mst 한 줄에서 단축코드·한글명 추출 + 종목 유형 추정.

    KIS 마스터 메타의 정확한 컬럼 사양은 한투 공식 sample 코드를 봐야 정밀화 가능.
    현재는 코드 패턴 기반 단순 분류:
      - F-prefix 9자리: 펀드 (KIS order-cash 불가) → 제외
      - meta[1]='B': 채권성 상품 → 자동매매 부적합 → 제외
      - 그 외: 'stock' (KIS API는 ETF/ETN도 'J' 시장구분으로 호환)
    """
    meta_len = _META_LEN.get(market)
    if meta_len is None:
        raise ValueError(f"알 수 없는 시장: {market}")
    out: list[dict] = []
    for row in raw.decode("cp949", errors="ignore").splitlines():
        if len(row) <= meta_len + 21:
            continue
        code = row[0:9].rstrip()
        name = row[21:len(row) - meta_len].strip()
        meta = row[-meta_len:]
        meta_byte1 = meta[1] if len(meta) >= 2 else ""
        if not code or not code[:6].isalnum():
            continue
        # 펀드(F-prefix 9자리) — order-cash 매수 불가
        if len(code) == 9 and code.startswith("F"):
            continue
        # 채권성 상품 — 자동매매 부적합 (호가 없음, 매매단위 큼)
        if meta_byte1 == "B":
            continue
        # 종목 유형: meta[1] S=주식, E=ETF/ETN, R=REITs/신주 등. 자동매매 매수 흐름은 동일.
        kind_map = {"S": "stock", "E": "etf_etn", "R": "reits"}
        kind = kind_map.get(meta_byte1, "stock")
        out.append({
            "symbol": code, "name": name, "market": market, "kind": kind,
        })
    return out


def refresh() -> dict:
    """KOSPI + KOSDAQ 마스터를 새로 받아 캐시 교체. 실패한 시장은 직전 값 유지."""
    by_symbol: dict[str, dict] = {}
    n_per: dict[str, int] = {}
    any_success = False
    for market, url in [("KOSPI", KOSPI_URL), ("KOSDAQ", KOSDAQ_URL)]:
        try:
            raw = _download_mst(url)
            rows = _parse_master(raw, market)
            for r in rows:
                by_symbol[r["symbol"]] = {
                    "name": r["name"], "market": market,
                    "kind": r.get("kind", "stock"),
                }
            n_per[market] = len(rows)
            any_success = True
            log.info("KIS 마스터 [%s] %d개 갱신", market, len(rows))
        except Exception as e:
            log.warning("KIS 마스터 [%s] 다운로드 실패: %s", market, e)
            n_per[market] = -1   # 실패 표시

    with _lock:
        if any_success:
            # 부분 성공이라도 받은 시장은 갱신 (실패한 시장은 새로운 by_symbol에 없음)
            # 단, 다른 시장의 직전 값도 보존하려면 merge 필요 — 직전 캐시와 union
            if n_per.get("KOSPI", -1) >= 0 and n_per.get("KOSDAQ", -1) >= 0:
                _state["by_symbol"] = by_symbol
            else:
                # 한쪽만 실패 — 실패한 쪽은 직전 값 보존
                merged = dict(_state["by_symbol"])
                merged.update(by_symbol)
                _state["by_symbol"] = merged
            _state["symbols"] = set(_state["by_symbol"].keys())
            _state["fetched_at"] = datetime.now(timezone.utc)
            _state["n_kospi"] = (n_per.get("KOSPI", 0)
                                  if n_per.get("KOSPI", -1) >= 0
                                  else _state["n_kospi"])
            _state["n_kosdaq"] = (n_per.get("KOSDAQ", 0)
                                   if n_per.get("KOSDAQ", -1) >= 0
                                   else _state["n_kosdaq"])
    return {
        "ok": any_success,
        "n_kospi": _state["n_kospi"],
        "n_kosdaq": _state["n_kosdaq"],
        "fetched_at": _state["fetched_at"].isoformat()
                       if _state["fetched_at"] else None,
    }


def get_master_set() -> set[str]:
    with _lock:
        return set(_state["symbols"])


def get_status() -> dict:
    with _lock:
        return {
            "n_symbols": len(_state["symbols"]),
            "n_kospi": _state["n_kospi"],
            "n_kosdaq": _state["n_kosdaq"],
            "fetched_at": _state["fetched_at"].isoformat()
                           if _state["fetched_at"] else None,
        }
