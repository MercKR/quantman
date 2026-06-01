"""save_managed_overseas — yfinance 미수집('/') 티커 원천 차단 검증.

KIS 미국 마스터의 우선주·유닛·클래스주('/' 표기)는 yfinance가 못 받아(parquet 0개)
"Failed to get ticker" 폭주·로그 스팸만 유발한다. 유일한 write 경로에서 제외하고,
기존 항목도 다음 저장 때 정리되는지(self-clean) 고정한다.

    cd platform && pytest tests/test_managed_overseas_filter.py -v
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

from quant_core import data_fetcher as df  # noqa: E402


@pytest.fixture
def _tmp_path(tmp_path, monkeypatch):
    p = tmp_path / "managed_overseas_stocks.json"
    monkeypatch.setattr(df, "MANAGED_OVERSEAS_PATH", p)
    return p


def test_save_drops_slash_tickers(_tmp_path):
    df.save_managed_overseas([
        {"code": "AAPL", "name": "Apple"},
        {"code": "JPM/D", "name": "JPM Pref D"},      # 우선주 — 제외
        {"code": "RAC/UN", "name": "Unit"},           # 유닛 — 제외
        {"code": "BRK-B", "name": "Berkshire B"},     # 정당 클래스주(대시) — 유지
        {"code": "", "name": "빈코드"},                # 빈 — 제외
    ])
    saved = df.load_managed_overseas()
    codes = {s["code"] for s in saved}
    assert codes == {"AAPL", "BRK-B"}, f"'/'·빈코드 제외돼야: {codes}"


def test_existing_slash_self_cleans_on_next_save(_tmp_path):
    """기존 파일에 '/' 티커가 있어도 다음 저장(시드 cron) 때 정리된다(load+union→save)."""
    _tmp_path.write_text(json.dumps([
        {"code": "JPM/D", "name": "old pref"},
        {"code": "AAPL", "name": "Apple"},
    ], ensure_ascii=False), encoding="utf-8")
    # 시드 패턴: 기존 ∪ 신규를 다시 save
    df.save_managed_overseas(df.load_managed_overseas() + [{"code": "MSFT", "name": "MS"}])
    codes = {s["code"] for s in df.load_managed_overseas()}
    assert codes == {"AAPL", "MSFT"}, f"기존 '/'가 정리되고 신규 추가돼야: {codes}"


def test_dedupe_still_works(_tmp_path):
    df.save_managed_overseas([
        {"code": "AAPL", "name": "Apple"},
        {"code": "AAPL", "name": "dup"},
    ])
    assert len(df.load_managed_overseas()) == 1


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
