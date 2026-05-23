"""C-02 회귀 — np.log() 정의역 마스킹.

음수 가능 level 시계열(금리차·스프레드 등 매크로)에 log() 적용 시 'divide by zero
in log' / 'invalid value in log' 경고가 떨어지면서 결과가 -inf/NaN으로 오염되고,
다운스트림 condition_mask가 fillna(False)로 조용히 신호를 누락한다.

C-02 수정 후: Close <= 0 또는 prev_close <= 0인 시점은 NaN으로 명시 처리되어
경고가 0이 되고, 정상 가격 구간의 결과는 변화 없음.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_CORE_DIR = Path(__file__).resolve().parent.parent
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))

from quant_core.indicators import (_safe_log_return, add_returns,
                                    add_realized_vol, add_zscore)


def _df_with_close(values):
    return pd.DataFrame({
        "Open": values, "High": values, "Low": values, "Close": values,
        "Volume": [100] * len(values),
    })


def test_safe_log_normal_prices_unchanged():
    """양수 가격에서는 기존 np.log 결과와 동일."""
    close = pd.Series([100.0, 101.0, 102.0, 99.0, 100.5])
    safe = _safe_log_return(close)
    naive = np.log(close / close.shift(1))
    # NaN-aware 동등성
    pd.testing.assert_series_equal(safe, naive)


def test_safe_log_zero_close_masked_to_nan():
    """Close에 0이 끼면 그 시점 결과는 NaN (경고 없음)."""
    close = pd.Series([100.0, 0.0, 101.0, 102.0])
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        safe = _safe_log_return(close)   # 경고로 raise되면 실패
    # index 1: log(0/100) → masked
    # index 2: log(101/0) → masked
    assert np.isnan(safe.iloc[1])
    assert np.isnan(safe.iloc[2])
    assert not np.isnan(safe.iloc[3])    # 102/101 정상


def test_safe_log_negative_values_masked():
    """음수 level(매크로 스프레드 등)은 마스킹 — log(neg) 경고 차단."""
    close = pd.Series([1.0, -0.5, 0.3, -0.1])
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        safe = _safe_log_return(close)
    # 음수가 끼는 모든 전이는 NaN
    assert safe.iloc[1:].isna().all()


def test_add_returns_no_warnings_on_macro_like_series():
    """add_returns 호출 시 음수/0이 섞인 시계열에서 경고 0."""
    df = _df_with_close([1.5, -0.3, 0.0, 2.0, 1.7])
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        out = add_returns(df)
    # log_return_1d에 음수/0 시점은 NaN (명시적)
    assert out["log_return_1d"].iloc[1:4].isna().all()
    # pct_change_*는 그대로 동작 (음수 가능 series에 의미는 없지만 경고는 없음)
    assert "pct_change_1d" in out.columns


def test_add_realized_vol_no_warnings():
    df = _df_with_close([10.0, -2.0, 5.0, 0.0, 8.0, 9.0, 7.5])
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        add_realized_vol(df)


def test_add_zscore_no_warnings_without_log_return_col():
    """log_return_1d 컬럼이 미리 없을 때 zscore가 자체 계산하는 경로도 경고 0."""
    df = _df_with_close([10.0, -1.0, 0.5, 0.0, 3.0, 4.0, 5.0])
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        add_zscore(df)
