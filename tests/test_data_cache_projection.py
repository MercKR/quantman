"""P1 — data_cache의 raw 캐시 + 컬럼 프로젝션 API 검증.

get_raw_dataset(raw만 로드)·get_projected(요청 컬럼만, 종목 subset, fund attach,
fund 미요청 시 fund 로드 안 함) 배선을 고정한다. 값 자체의 compute_all 동일성은
test_compute_columns가 보장 — 여기선 캐시/프로젝션 wiring을 검증.

    cd platform && pytest tests/test_data_cache_projection.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT / "server"))

dc = pytest.importorskip("app.data_cache")
from quant_core.indicators import compute_columns  # noqa: E402


def _raw(seed: int, n: int = 320) -> pd.DataFrame:
    idx = pd.date_range("2020-01-02", periods=n, freq="B")
    r = np.random.default_rng(seed)
    close = np.maximum(100.0 * np.cumprod(1.0 + r.normal(0.05, 1.2, n) / 100.0), 1.0)
    open_ = np.concatenate([[close[0]], close[:-1]])
    return pd.DataFrame({
        "Open": open_, "High": np.maximum(open_, close) * 1.01,
        "Low": np.minimum(open_, close) * 0.99, "Close": close,
        "Volume": r.uniform(1e5, 2e6, n),
    }, index=idx)


_RAW = {"AAA": _raw(1), "BBB": _raw(2), "CCC": _raw(3)}


def _fund(idx):
    q = pd.date_range(idx[0], idx[-1], freq="QE")
    r = np.random.default_rng(9)
    return pd.DataFrame({
        "shares_outstanding": r.uniform(1e7, 1e8, len(q)),
        "ttm_ni": r.uniform(1e6, 1e8, len(q)),
    }, index=q)


@pytest.fixture(autouse=True)
def _patch(monkeypatch):
    # raw 로더 — get_raw_dataset이 반드시 with_indicators=False로 부르는지 단언
    def fake_load_dataset(with_indicators=True):
        assert with_indicators is False, "get_raw_dataset는 raw(지표계산 0)만 로드해야 함"
        return {s: df.copy() for s, df in _RAW.items()}
    monkeypatch.setattr(dc.qc, "load_dataset", fake_load_dataset)
    monkeypatch.setattr(dc.data_fetcher, "data_generation", lambda: 1)
    # 캐시 리셋
    monkeypatch.setattr(dc, "_raw", None)
    monkeypatch.setattr(dc, "_dataset", None)
    monkeypatch.setattr(dc, "_built_generation", None)
    monkeypatch.setattr(dc, "_manifest", None)
    monkeypatch.setattr(dc, "_symbol_index", None)


def test_get_raw_dataset_is_raw_only():
    raw = dc.get_raw_dataset()
    assert set(raw) == {"AAA", "BBB", "CCC"}
    assert set(raw["AAA"].columns) == {"Open", "High", "Low", "Close", "Volume"}, \
        "raw 캐시는 OHLCV만(지표 컬럼 없음)"


def test_projection_matches_compute_columns():
    cols = {"rsi_14", "momentum_12_1m"}
    proj = dc.get_projected(cols)
    assert set(proj) == {"AAA", "BBB", "CCC"}
    for s in proj:
        for c in cols:
            assert c in proj[s].columns
            assert proj[s][c].equals(compute_columns(_RAW[s], cols)[c]), \
                f"{s}.{c}: 프로젝션이 compute_columns와 불일치"
        # 요청 안 한 무거운 지표는 없어야(프로젝션 실제 동작)
        assert "atr_14_pct" not in proj[s].columns


def test_projection_symbol_subset():
    proj = dc.get_projected({"rsi_14"}, symbols=["AAA"])
    assert set(proj) == {"AAA"}, "요청 종목만 프로젝션돼야"


def test_projection_no_fund_load_when_not_needed(monkeypatch):
    """fund 지표가 요청 안 되면 load_fund_all을 호출하지 않아야(불필요한 ~45초 회피)."""
    def _boom():
        raise AssertionError("fund 미요청인데 load_fund_all 호출됨")
    monkeypatch.setattr(dc.data_fetcher, "load_fund_all", _boom)
    proj = dc.get_projected({"momentum_12_1m"})
    assert all("momentum_12_1m" in df.columns for df in proj.values())


def test_projection_fund_column_attaches(monkeypatch):
    funds = {s: _fund(_RAW[s].index) for s in _RAW}
    called = {"n": 0}

    def fake_fund_all():
        called["n"] += 1
        return funds
    monkeypatch.setattr(dc.data_fetcher, "load_fund_all", fake_fund_all)
    proj = dc.get_projected({"trailing_pe"})
    assert called["n"] == 1, "fund 요청 시 load_fund_all 1회 호출"
    for s in proj:
        assert "trailing_pe" in proj[s].columns
        exp = compute_columns(_RAW[s], {"trailing_pe"}, funds[s])
        assert proj[s]["trailing_pe"].equals(exp["trailing_pe"])


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
