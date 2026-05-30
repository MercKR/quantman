"""G3·G4·G5 — 그룹 노출 캡 · 낙폭 반응형 스케일러 · 시계열 timeframe 회귀.

기존 동작을 새 일반 구조의 특수 케이스로 흡수했는지 고정한다(임시방편 아님).

    cd platform && pytest tests/test_engine_overlays.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

from quant_core.blocks import EvalContext, Node, data, evaluate  # noqa: E402
from quant_core.ir_engine.engine import _apply_dd_control, _cap_groups  # noqa: E402


# ── G3: 라벨 기반 그룹 노출 캡 (per-name 캡의 일반화) ─────────────────────────

def test_group_cap_shrinks_overweight_group():
    w = pd.Series({"A": 0.4, "B": 0.4, "C": 0.2})       # gross 1.0
    labels = pd.Series({"A": 0.0, "B": 0.0, "C": 1.0})  # 그룹0={A,B}=0.8, 그룹1={C}=0.2
    out = _cap_groups(w, labels, 50.0)                   # 그룹당 0.5 캡
    # 그룹0(0.8>0.5) → 0.5/0.8 배 축소; 그룹1(0.2) 그대로
    assert abs(out["A"] - 0.25) < 1e-9 and abs(out["B"] - 0.25) < 1e-9
    assert abs(out["C"] - 0.20) < 1e-9
    assert out.abs().sum() < 1.0                         # 초과분은 현금 버퍼


def test_group_cap_noop_when_within_limit():
    w = pd.Series({"A": 0.3, "B": 0.3, "C": 0.4})
    labels = pd.Series({"A": 0.0, "B": 1.0, "C": 2.0})   # 각자 단독 그룹 (per-name과 동치)
    out = _cap_groups(w, labels, 50.0)
    pd.testing.assert_series_equal(out, w)               # 모두 0.5 이하 → 무변화


# ── G4: 낙폭 반응형 스케일러 (binary kill의 일반화) ──────────────────────────

def test_dd_binary_latches_after_breach():
    """soft 미지정 → binary: 돌파 다음날부터 노출 0 고정(기존 _apply_dd_stop 동치)."""
    net = pd.Series([-0.15, 0.10, 0.10])                 # day0 후 낙폭 15% ≥ hard 10
    out = _apply_dd_control(net, hard_pct=10.0)
    assert out.iloc[0] == -0.15                          # 돌파 당일은 체결
    assert out.iloc[1] == 0.0 and out.iloc[2] == 0.0     # 이후 latch


def test_dd_soft_partial_derisk_vs_binary():
    """soft~hard 구간에서 부분 디리스킹(0<scale<1) — binary는 hard 미만이면 풀노출."""
    net = pd.Series([-0.07, 0.10])                       # day0 후 낙폭 7% (soft4~hard10 사이)
    soft = _apply_dd_control(net, hard_pct=10.0, soft_pct=4.0)
    binary = _apply_dd_control(net, hard_pct=10.0)       # soft 없음
    assert soft.iloc[0] == -0.07 and binary.iloc[0] == -0.07   # 시작은 둘 다 풀노출
    assert binary.iloc[1] == 0.10                        # binary: 7%<10 → 풀노출
    assert 0.0 < soft.iloc[1] < 0.10                     # soft: 부분 축소
    # 낙폭 7% → scale=(10-7)/(10-4)=0.5
    assert abs(soft.iloc[1] - 0.05) < 1e-9


# ── G5: 시계열 timeframe (일봉 전용의 일반화) ────────────────────────────────

def _ctx_one():
    idx = pd.date_range("2022-01-03", periods=80, freq="B")
    close = pd.Series(100 + np.arange(80) * 0.5, index=idx)   # 완만한 상승추세
    d = {"AAA": pd.DataFrame({"Open": close, "High": close, "Low": close,
                              "Close": close, "Volume": 1e6}, index=idx)}
    return EvalContext.from_dataset(d), idx


def _ma(window, tf):
    return Node(op="ts_mean", params={"window": window, "timeframe": tf},
                inputs={"signal": data("__SELF__.Close")})


def test_timeframe_weekly_aligns_and_steps():
    ctx, idx = _ctx_one()
    daily = evaluate(_ma(5, "D"), ctx)["AAA"]
    weekly = evaluate(_ma(5, "W"), ctx)["AAA"]
    assert list(weekly.index) == list(idx)               # 일봉 인덱스로 정렬
    assert not weekly.equals(daily)                      # 주봉은 일봉과 다름
    # 주봉값은 주 경계에서만 바뀜 → 고유값 수가 일봉보다 훨씬 적은 계단형
    assert weekly.dropna().nunique() < daily.dropna().nunique()
    assert weekly.notna().any()                          # 워밍업 후 값 존재


def test_timeframe_monthly_resample_works():
    ctx, _ = _ctx_one()
    monthly = evaluate(_ma(2, "M"), ctx)["AAA"]          # "ME" 리샘플 경로 가동 확인
    assert monthly.notna().any()


def test_timeframe_default_is_daily():
    ctx, _ = _ctx_one()
    explicit_d = evaluate(_ma(5, "D"), ctx)["AAA"]
    no_tf = evaluate(Node(op="ts_mean", params={"window": 5},
                          inputs={"signal": data("__SELF__.Close")}), ctx)["AAA"]
    pd.testing.assert_series_equal(explicit_d, no_tf)    # 기본 = 일봉


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
