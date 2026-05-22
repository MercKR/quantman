"""KIS 종목마스터 다운로드 · 파싱.

한국투자증권이 공식적으로 배포하는 .mst 마스터 파일을 받아
{단축코드, 표준코드, 한글명, 시장} 행으로 파싱한다.

ZIP 파일 한 개당 한 행 = 한 종목, EUC-KR(=cp949) 인코딩, 가변폭 한글명 + 고정폭 메타.
공식 sample 코드 기준:
- KOSPI 메타 부분 길이 228자
- KOSDAQ 메타 부분 길이 222자
- 0:9    단축코드
- 9:21   표준코드
- 21:-N  한글종목명 (N = 메타 길이)
"""

from __future__ import annotations

import io
import logging
import urllib.request
import zipfile

log = logging.getLogger("localapp.kis_master")

KOSPI_URL = "https://new.real.download.dws.co.kr/common/master/kospi_code.mst.zip"
KOSDAQ_URL = "https://new.real.download.dws.co.kr/common/master/kosdaq_code.mst.zip"

# 마스터별 메타(끝부분 고정폭) 길이
_META_LEN = {"KOSPI": 228, "KOSDAQ": 222}

# 해외 미국 마스터 (.cod 탭 TSV) — 로컬 주문 라우팅(거래소 EXCD)용.
# 서버 kis_master_cache와 동일 소스/포맷. 로컬이 자급해야 서버 단절 시에도
# 보유분 청산·손절 발주가 올바른 거래소로 나간다(runner 견고성 원칙).
OVERSEAS_US_URLS = {
    "NAS": "https://new.real.download.dws.co.kr/common/master/nasmst.cod.zip",
    "NYS": "https://new.real.download.dws.co.kr/common/master/nysmst.cod.zip",
    "AMS": "https://new.real.download.dws.co.kr/common/master/amsmst.cod.zip",
}


def _download_mst(url: str, timeout: int = 30) -> bytes:
    """ZIP을 다운받아 내부 마스터 파일의 raw bytes를 반환 (.mst 국내 / .cod 해외)."""
    req = urllib.request.Request(url, headers={"User-Agent": "quant-platform-local"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        zdata = r.read()
    with zipfile.ZipFile(io.BytesIO(zdata)) as z:
        names = z.namelist()
        name = (next((n for n in names if n.lower().endswith(".mst")), None)
                or next((n for n in names if n.lower().endswith(".cod")), None)
                or (names[0] if names else None))
        if name is None:
            raise RuntimeError(f"ZIP 내부에 마스터 파일이 없습니다: {names}")
        return z.read(name)


def parse_master(raw: bytes, market: str) -> list[dict]:
    """공식 sample 코드 기반 파싱.

    빈 줄/짧은 줄은 스킵. 잘못된 한글이 깨지더라도 종목코드는 반드시 ASCII이므로 안전.
    """
    meta_len = _META_LEN.get(market)
    if meta_len is None:
        raise ValueError(f"알 수 없는 시장: {market}")

    out: list[dict] = []
    for row in raw.decode("cp949", errors="ignore").splitlines():
        if len(row) <= meta_len + 21:
            continue
        code = row[0:9].rstrip()
        std_code = row[9:21].rstrip()
        name = row[21:len(row) - meta_len].strip()
        if not code or not code[:6].isalnum():
            continue
        # 종목코드는 6자리 숫자(주식) 혹은 알파벳+숫자(ETF/ETN 등). 마스터에 따라 다름.
        out.append({
            "symbol": code, "std_code": std_code, "name": name, "market": market,
        })
    return out


def fetch_all_tradable(timeout: int = 30) -> list[dict]:
    """KOSPI + KOSDAQ 합산 종목마스터를 반환. 다운로드 실패한 시장은 건너뛴다."""
    rows: list[dict] = []
    for market, url in [("KOSPI", KOSPI_URL), ("KOSDAQ", KOSDAQ_URL)]:
        try:
            raw = _download_mst(url, timeout=timeout)
            parsed = parse_master(raw, market)
            log.info("KIS 종목마스터 [%s] %d개 파싱", market, len(parsed))
            rows.extend(parsed)
        except Exception as e:
            log.warning("KIS 종목마스터 [%s] 다운로드/파싱 실패: %s", market, e)
    return rows


# ── 해외(미국) 마스터 — .cod 탭 TSV ─────────────────────────────────────────

def parse_overseas_master(raw: bytes, exchange: str) -> list[dict]:
    """미국 .cod 마스터 파싱 — 탭 구분 24컬럼. 서버 kis_master_cache와 동일 포맷.

    핵심 컬럼:
      [4] 단축 티커 (KIS overseas API의 OVRS_PDNO / 주문 PDNO)
      [6] 한글명, [7] 영문명
      [8] 종목구분 (2=주식, 3=ETF)
      [9] 통화 (미국은 USD)
    exchange는 파일 출처(NAS/NYS/AMS)로 주어진다.
    """
    out: list[dict] = []
    for row in raw.decode("cp949", errors="ignore").splitlines():
        if "\t" not in row:
            continue
        cols = row.split("\t")
        if len(cols) < 10:
            continue
        ticker = cols[4].strip()
        if not ticker:
            continue
        sec_type = cols[8].strip()
        kind = "etf_etn" if sec_type == "3" else "stock"
        out.append({
            "symbol": ticker,
            "name": cols[6].strip() or cols[7].strip(),
            "exchange": exchange,        # NAS / NYS / AMS
            "kind": kind,
            "currency": "USD",
        })
    return out


def fetch_us_masters(timeout: int = 30) -> list[dict]:
    """NASDAQ + NYSE + AMEX 합산 마스터. 실패한 거래소는 건너뛴다."""
    rows: list[dict] = []
    for exchange, url in OVERSEAS_US_URLS.items():
        try:
            raw = _download_mst(url, timeout=timeout)
            parsed = parse_overseas_master(raw, exchange)
            log.info("KIS 해외 마스터 [%s] %d개 파싱", exchange, len(parsed))
            rows.extend(parsed)
        except Exception as e:
            log.warning("KIS 해외 마스터 [%s] 다운로드/파싱 실패: %s", exchange, e)
    return rows
