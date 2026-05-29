"""B1 — referenced_symbols 추출 + load_dataset_for 회귀 테스트.

referenced_symbols는 fund-safety 경로: 누락 시 build_signal_mask가 빈 mask →
매도 신호가 조용히 미발동. 그래서 추출 완전성을 회귀로 고정한다.

    cd platform && pytest tests/test_dataset_scope.py -v
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

import quant_core as qc  # noqa: E402


# ── referenced_symbols ────────────────────────────────────────────────────

def test_self_and_macro_reference():
    """[이 종목] >= S&P500.pct_change_1d — SELF 제외, S&P500만 추출."""
    conds = [{
        "left": {"kind": "indicator", "symbol": "__SELF__", "indicator": "pct_change_1d"},
        "op": ">=",
        "right": {"kind": "indicator", "symbol": "S&P500", "indicator": "pct_change_1d"},
    }]
    assert qc.referenced_symbols(conds) == {"S&P500"}


def test_constant_excluded():
    """[이 종목].RSI_14 < 70 — constant 우변·SELF 좌변 → 외부 참조 없음."""
    conds = [{
        "left": {"kind": "indicator", "symbol": "__SELF__", "indicator": "RSI_14"},
        "op": "<",
        "right": {"kind": "constant", "value": 70},
    }]
    assert qc.referenced_symbols(conds) == set()


def test_nested_group_multi_symbol():
    """중첩 그룹 + 복수 외부 종목 참조 — 재귀로 전부 추출."""
    conds = [{
        "logic": "OR",
        "conditions": [
            {"left": {"kind": "indicator", "symbol": "005930", "indicator": "Close"},
             "op": ">",
             "right": {"kind": "indicator", "symbol": "000660", "indicator": "Close"}},
            {"left": {"kind": "indicator", "symbol": "__SELF__", "indicator": "MA20"},
             "op": ">",
             "right": {"kind": "indicator", "symbol": "KOSPI", "indicator": "Close"}},
        ],
    }]
    assert qc.referenced_symbols(conds) == {"005930", "000660", "KOSPI"}


def test_empty_and_none():
    assert qc.referenced_symbols([]) == set()
    assert qc.referenced_symbols(None) == set()


def test_history_operand_symbol():
    """kind=history 피연산자의 symbol도 추출 (constant만 제외)."""
    conds = [{
        "left": {"kind": "indicator", "symbol": "__SELF__", "indicator": "Close"},
        "op": ">",
        "right": {"kind": "history", "symbol": "달러지수", "indicator": "Close",
                  "stat": "mean", "window": 20},
    }]
    assert qc.referenced_symbols(conds) == {"달러지수"}


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
    monkeypatch.setattr(dataset, "load_fund_all", lambda: {})

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


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
