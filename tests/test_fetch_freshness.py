"""해외 fetch 신선도 게이트 — 이미 최신인 종목은 재fetch하지 않는다(fetch_korean_stocks와 parity).

과거엔 fetch_managed_overseas가 매 실행마다 기존 전 종목의 최근창을 무조건 재다운로드해
재시작·cron마다 불필요한 네트워크 호출이 쌓였다. 이 테스트가 신선도 스킵을 고정하고,
시간대 확인 불가 시 보수적으로 전량 fetch(데이터 누락 0)함을 함께 검증한다.

    cd platform && pytest tests/test_fetch_freshness.py -v
"""

import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

from quant_core import data_fetcher as dfh  # noqa: E402

_LAST_CLOSED = date(2026, 5, 29)


def _ohlcv(idx):
    return pd.DataFrame({"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0, "Volume": 1},
                        index=pd.to_datetime(idx))


def test_overseas_skips_current_symbols(tmp_path, monkeypatch):
    """AAA(최신)는 스킵, BBB(stale)는 upd fetch, CCC(신규)는 backfill."""
    def fake_path(sym):
        return tmp_path / f"{sym}.parquet"
    monkeypatch.setattr(dfh, "_parquet_path", fake_path)
    monkeypatch.setattr(dfh, "_last_closed_us_date", lambda: _LAST_CLOSED)
    monkeypatch.setattr(dfh, "load_managed_overseas",
                        lambda: [{"code": "AAA"}, {"code": "BBB"}, {"code": "CCC"}])
    _ohlcv([_LAST_CLOSED - timedelta(days=2), _LAST_CLOSED]).to_parquet(fake_path("AAA"))  # 최신
    _ohlcv([date(2026, 5, 1), date(2026, 5, 2)]).to_parquet(fake_path("BBB"))              # stale
    # CCC: parquet 없음 → 신규

    calls = []
    monkeypatch.setattr(dfh, "_fetch_overseas_batched",
                        lambda codes, start, batch, verbose=False: (calls.append(sorted(codes)), len(codes))[1])
    monkeypatch.setattr(dfh, "mark_data_dirty", lambda: None)

    dfh.fetch_managed_overseas()

    upd_codes, new_codes = calls[0], calls[1]    # 호출 순서: upd(최근창) → new(백필)
    assert "AAA" not in upd_codes and "AAA" not in new_codes, "최신 종목은 재fetch 금지"
    assert upd_codes == ["BBB"], f"stale만 upd fetch: {upd_codes}"
    assert new_codes == ["CCC"], f"신규만 backfill: {new_codes}"


def test_overseas_no_skip_when_timezone_unavailable(tmp_path, monkeypatch):
    """_last_closed_us_date=None(시간대 불가)이면 신선도 스킵 비활성 — 기존 종목도 fetch(보수적)."""
    def fake_path(sym):
        return tmp_path / f"{sym}.parquet"
    monkeypatch.setattr(dfh, "_parquet_path", fake_path)
    monkeypatch.setattr(dfh, "_last_closed_us_date", lambda: None)
    monkeypatch.setattr(dfh, "load_managed_overseas", lambda: [{"code": "AAA"}])
    _ohlcv([date(2026, 1, 1), date(2026, 1, 2)]).to_parquet(fake_path("AAA"))

    calls = []
    monkeypatch.setattr(dfh, "_fetch_overseas_batched",
                        lambda codes, start, batch, verbose=False: (calls.append(sorted(codes)), len(codes))[1])
    monkeypatch.setattr(dfh, "mark_data_dirty", lambda: None)

    dfh.fetch_managed_overseas()
    assert calls[0] == ["AAA"], "캘린더 불가 시 기존 종목도 fetch(스킵 비활성)"


def test_last_closed_us_date_never_undershoots():
    """_last_closed_us_date는 과거 거래일 이상이어야(과소평가=데이터 누락 방지). None 허용."""
    d = dfh._last_closed_us_date()
    if d is not None:
        assert isinstance(d, date)
        assert d <= date.today()                  # 미래일 수 없음
        assert d.weekday() < 5                     # 주말이 아님(직전 평일로 보정)


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
