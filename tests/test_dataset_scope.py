"""B1 — load_dataset_for 회귀 테스트.

    cd platform && pytest tests/test_dataset_scope.py -v
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

import quant_core as qc  # noqa: E402


# ── load_dataset_for ──────────────────────────────────────────────────────

def test_load_dataset_for_scopes_and_skips_missing(tmp_path, monkeypatch):
    """요청 종목만 로드, 디스크에 없는 종목은 조용히 skip. 지표 컬럼 계산."""
    from quant_core import data_fetcher, dataset

    # 합성 parquet 2개 — OHLCV 최소 형태
    idx = pd.date_range("2024-01-01", periods=60, freq="D")
    df = pd.DataFrame({
        "Open": 100.0, "High": 101.0, "Low": 99.0,
        "Close": 100.0 + pd.Series(range(60), index=idx) * 0.1,
        "Volume": 1000,
    }, index=idx)

    def fake_path(sym):
        return tmp_path / f"{sym}.parquet"

    monkeypatch.setattr(data_fetcher, "_parquet_path", fake_path)
    monkeypatch.setattr(dataset, "_parquet_path", fake_path)
    monkeypatch.setattr(dataset, "load_stock_fundamentals", lambda s: pd.DataFrame())

    df.to_parquet(fake_path("AAA"))
    df.to_parquet(fake_path("BBB"))
    # CCC는 안 만듦 → skip 돼야

    out = qc.load_dataset_for(["AAA", "BBB", "CCC"], with_indicators=True)
    assert set(out.keys()) == {"AAA", "BBB"}, "미존재 CCC는 제외돼야"
    # 지표 컬럼 계산 확인 (compute_all)
    assert len(out["AAA"].columns) > 5, "지표 컬럼이 추가돼야"


def test_load_dataset_for_no_indicators(tmp_path, monkeypatch):
    """with_indicators=False면 raw OHLCV만."""
    from quant_core import data_fetcher, dataset
    idx = pd.date_range("2024-01-01", periods=10, freq="D")
    df = pd.DataFrame({"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0,
                       "Volume": 1}, index=idx)

    def fake_path(sym):
        return tmp_path / f"{sym}.parquet"
    monkeypatch.setattr(data_fetcher, "_parquet_path", fake_path)
    monkeypatch.setattr(dataset, "_parquet_path", fake_path)
    df.to_parquet(fake_path("AAA"))

    out = qc.load_dataset_for(["AAA"], with_indicators=False)
    assert set(out["AAA"].columns) == {"Open", "High", "Low", "Close", "Volume"}


def test_load_dataset_for_loads_only_requested_funds(tmp_path, monkeypatch):
    """부분집합 로드는 요청 종목의 펀더멘털만 읽는다 — 전 종목(load_fund_all) 순회 금지.

    과거엔 load_fund_all()로 전 종목(수천) 펀더멘털을 읽어 단일 종목 로드가 ~42초
    걸렸다. 이 가드가 그 성능 회귀(전체 펀더멘털 로드로의 복귀)를 차단한다.
    """
    from quant_core import data_fetcher, dataset
    idx = pd.date_range("2024-01-01", periods=30, freq="D")
    d = pd.DataFrame({"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0, "Volume": 1}, index=idx)

    def fake_path(sym):
        return tmp_path / f"{sym}.parquet"
    monkeypatch.setattr(data_fetcher, "_parquet_path", fake_path)
    monkeypatch.setattr(dataset, "_parquet_path", fake_path)
    d.to_parquet(fake_path("AAA"))
    d.to_parquet(fake_path("BBB"))

    called: list[str] = []
    monkeypatch.setattr(dataset, "load_stock_fundamentals",
                        lambda s: (called.append(s), pd.DataFrame())[1])

    def _boom():
        raise AssertionError("load_dataset_for가 load_fund_all(전체)을 호출 — 성능 회귀")
    monkeypatch.setattr(dataset, "load_fund_all", _boom)

    out = qc.load_dataset_for(["AAA", "BBB"], with_indicators=True)
    assert set(out) == {"AAA", "BBB"}
    assert set(called) == {"AAA", "BBB"}, f"요청 종목 펀더멘털만 로드해야 함: {called}"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
