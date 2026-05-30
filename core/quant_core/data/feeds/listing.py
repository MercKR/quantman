"""static.listing 피드 — KR 상장·폐지일 (FinanceDataReader KRX-DESC + KRX-DELISTING).

활성 종목 상장일(KRX-DESC)과 폐지 종목 상장/폐지일(KRX-DELISTING)을 종목코드별 사이드카로 저장.
생존편향(폐지 종목 포함)·신규상장 워밍업 충분성 판정의 선행 데이터. 매니페스트가 종목별로 흡수한다.

사이드카: _listing.json (가격 parquet과 같은 디렉터리). load 의존: json·pathlib뿐.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ..manifest import default_manifest_path

_SIDECAR = "_listing.json"
_cache: Optional[dict] = None
_cache_mtime: Optional[float] = None


def _path() -> Path:
    return default_manifest_path().parent / _SIDECAR


def _date_str(v) -> Optional[str]:
    """날짜 셀을 'YYYY-MM-DD'로. NaT/NaN/빈값은 None."""
    if v is None:
        return None
    try:
        import pandas as pd
        if pd.isna(v):
            return None
    except Exception:                            # pragma: no cover — pandas 부재 방어
        pass
    s = str(v)[:10]
    return s if s and s != "NaT" else None


def fetch() -> dict:
    """활성(KRX-DESC ListingDate) + 폐지(KRX-DELISTING Listing/DelistingDate) → 사이드카."""
    import FinanceDataReader as fdr

    out: dict[str, dict] = {}
    for _, r in fdr.StockListing("KRX-DESC").iterrows():
        code = str(r.get("Code") or "").strip()
        ld = _date_str(r.get("ListingDate"))
        if code and ld:
            out[code] = {"listing_date": ld}
    for _, r in fdr.StockListing("KRX-DELISTING").iterrows():
        code = str(r.get("Symbol") or "").strip()
        if not code:
            continue
        rec = out.get(code, {})
        ld, dd = _date_str(r.get("ListingDate")), _date_str(r.get("DelistingDate"))
        if ld:
            rec["listing_date"] = ld
        if dd:
            rec["delisting_date"] = dd
        out[code] = rec
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out


def load() -> dict:
    """사이드카 로드(mtime 캐시). 미수급이면 빈 dict."""
    global _cache, _cache_mtime
    p = _path()
    if not p.exists():
        return {}
    mtime = p.stat().st_mtime
    if _cache is None or mtime != _cache_mtime:
        _cache = json.loads(p.read_text(encoding="utf-8"))
        _cache_mtime = mtime
    return _cache
