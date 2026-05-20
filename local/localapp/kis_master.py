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


def _download_mst(url: str, timeout: int = 30) -> bytes:
    """ZIP을 다운받아 내부 .mst 파일의 raw bytes를 반환."""
    req = urllib.request.Request(url, headers={"User-Agent": "quant-platform-local"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        zdata = r.read()
    with zipfile.ZipFile(io.BytesIO(zdata)) as z:
        name = next((n for n in z.namelist() if n.endswith(".mst")), None)
        if name is None:
            raise RuntimeError(f"ZIP 내부에 .mst가 없습니다: {z.namelist()}")
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
