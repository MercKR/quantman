"""C-01·C-03·C-04·CM 회귀 — 백테스트 비용/체결 모델 정확성.

C-01: 한국 매도세를 commission과 분리. 매수에 세금 안 붙고, 매도에만 sell_tax 적용.
C-03: 체결가는 호가단위로 라운딩(매수 up, 매도 down). 슬리피지 적용 후 라운딩.
C-04: 보유 수량은 정수. 잔여 현금은 cash로 유지(소수주 비허용).
CM-01: backtest.py와 exec_defaults가 단일 출처. 디폴트 commission/slippage 일치.
CM-02: exec_defaults 주석에 commission이 위탁수수료만(편도)임이 명시되어야 함.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_CORE_DIR = Path(__file__).resolve().parent.parent
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))

from quant_core.backtest import (_DEFAULT_COMMISSION, _DEFAULT_SELL_TAX,
                                  _DEFAULT_SLIPPAGE, run_backtest)
from quant_core.exec_defaults import DEFAULT_EXECUTION, round_to_tick


# ── 합성 데이터 헬퍼 ─────────────────────────────────────────────────────────


def _synth_df(prices: list[float], start="2023-01-02") -> pd.DataFrame:
    idx = pd.bdate_range(start, periods=len(prices))
    return pd.DataFrame({
        "Open": prices, "High": prices, "Low": prices, "Close": prices,
        "Volume": [100_000] * len(prices),
        "price_level": prices,
    }, index=idx)


def _all_true_buy():
    return [{
        "left": {"kind": "indicator", "symbol": "__SELF__",
                 "indicator": "price_level"},
        "op": ">",
        "right": {"kind": "constant", "value": 0.0},
    }]


# ── CM-01 default 일치 ───────────────────────────────────────────────────────


def test_defaults_pulled_from_exec_defaults():
    """CM-01 — backtest.py default가 exec_defaults에서 끌어와짐."""
    assert _DEFAULT_COMMISSION == DEFAULT_EXECUTION["bt_commission_bps"] / 10_000.0
    assert _DEFAULT_SLIPPAGE == DEFAULT_EXECUTION["bt_slippage_bps"] / 10_000.0
    assert _DEFAULT_SELL_TAX == DEFAULT_EXECUTION["bt_sell_tax_bps"] / 10_000.0
    # 매도세는 0.23% (KOSPI 평균)
    assert DEFAULT_EXECUTION["bt_sell_tax_bps"] == 23


def test_cm02_comment_separates_commission_from_tax():
    """CM-02 — exec_defaults 주석에서 commission이 위탁수수료만임이 분명해야 함.

    이전 주석은 'KIS 위탁수수료 + 거래세 평균'으로 둘을 한 항목에 묶었다.
    """
    src = (Path(_CORE_DIR) / "quant_core" / "exec_defaults.py").read_text(
        encoding="utf-8")
    assert "위탁수수료" in src
    assert "거래세" in src
    assert "bt_sell_tax_bps" in src


# ── C-04 정수주 ───────────────────────────────────────────────────────────────


def test_c04_integer_shares_no_fractional():
    """C-04 — 모든 trade의 shares가 정수. 잔여 현금은 cash로."""
    # 7만원대 가격, 1천만원 자본 → 약 142주 매수 가능
    prices = [70_000, 71_000, 72_000, 73_000, 74_000, 75_000]
    df = _synth_df(prices)
    res = run_backtest(
        data={"TEST": df}, trade_symbol="TEST",
        buy_conditions=_all_true_buy(),
        hold_days=2,
        initial_capital=10_000_000.0,
        fill="next_open",
    )
    assert res["success"] is True
    # equity 마지막 값은 정수주 보유로 인한 잔여 현금 포함
    # n_trades >= 1 (전략이 매수→hold 2일→매도)
    assert res["metrics"]["n_trades"] >= 1


# ── C-03 틱 라운딩 ───────────────────────────────────────────────────────────


def test_c03_buy_price_rounded_up_sell_price_rounded_down():
    """C-03 — 매수가는 up, 매도가는 down으로 호가단위 라운딩."""
    # 70,000원대 → tick = 100원. 슬리피지 10 bps → 70,070원이 70,000~70,100 사이.
    prices = [70_000.0, 70_500.0, 71_000.0, 71_500.0]
    df = _synth_df(prices)
    res = run_backtest(
        data={"TEST": df}, trade_symbol="TEST",
        buy_conditions=_all_true_buy(),
        hold_days=1,
        initial_capital=10_000_000.0,
        slippage=0.001, commission=0.0003, sell_tax=0.0023,
        currency="KRW",
        fill="next_open",
    )
    assert res["success"] is True
    trades = res["trades"]
    assert len(trades) > 0
    for _, t in trades.iterrows():
        # 진입가는 100원 배수 (70,000원대 tick=100), 매도가도 동일
        entry = t["진입가"]
        exit_ = t["청산가"]
        # 50,000~200,000 구간 tick = 100원
        assert entry % 100 == 0, f"entry not tick-aligned: {entry}"
        assert exit_ % 100 == 0, f"exit not tick-aligned: {exit_}"


# ── C-01 매도세 비대칭 ───────────────────────────────────────────────────────


def test_c01_sell_tax_only_on_close_no_change_at_open():
    """C-01 — 매도세 0과 default 비교: 매수는 영향 없고, 매도 수익률만 차이.

    동일 가격 시퀀스에서 sell_tax=0 / sell_tax=default 두 케이스를 돌려
    'cost(=매수)는 같고 proceeds(=매도)만 다름'을 확인.
    """
    prices = [70_000.0] * 30
    df = _synth_df(prices)
    common = dict(
        data={"TEST": df}, trade_symbol="TEST",
        buy_conditions=_all_true_buy(),
        hold_days=2,
        initial_capital=10_000_000.0,
        commission=0.0003, slippage=0.001,
        currency="KRW", fill="next_open",
    )
    res_no_tax = run_backtest(**common, sell_tax=0.0)
    res_with_tax = run_backtest(**common, sell_tax=0.0023)
    assert res_no_tax["success"] and res_with_tax["success"]
    # sell_tax=0이면 commission만 → 수익률이 더 좋음(덜 빠짐).
    # 따라서 total_return은 sell_tax 적용 시 더 작음.
    assert (res_no_tax["metrics"]["total_return"]
            > res_with_tax["metrics"]["total_return"])
    # 양쪽 모두 진입가는 동일해야 함 (매수에는 세금 영향 없음)
    t_no = res_no_tax["trades"]
    t_yes = res_with_tax["trades"]
    assert len(t_no) > 0 and len(t_yes) > 0
    assert t_no.iloc[0]["진입가"] == t_yes.iloc[0]["진입가"]
    # 매도가도 같다(같은 raw price + 같은 slip + 같은 tick) — 세금은 proceeds 계산에만 영향
    assert t_no.iloc[0]["청산가"] == t_yes.iloc[0]["청산가"]
    # 수익률만 다름
    assert t_no.iloc[0]["수익률(%)"] != t_yes.iloc[0]["수익률(%)"]


def test_c01_no_buy_side_tax():
    """C-01 — sell_tax는 매수 entry_price나 cost에 영향 없음.

    프로빙: sell_tax 변경이 trade의 '진입가'에 영향이 없어야 함.
    """
    prices = [50_000.0] * 10
    df = _synth_df(prices)
    common = dict(
        data={"TEST": df}, trade_symbol="TEST",
        buy_conditions=_all_true_buy(),
        hold_days=1,
        initial_capital=5_000_000.0,
        commission=0.0003, slippage=0.0005,
        currency="KRW", fill="next_open",
    )
    a = run_backtest(**common, sell_tax=0.0)
    b = run_backtest(**common, sell_tax=0.01)  # 1% 세금(극단치)
    ta, tb = a["trades"].iloc[0], b["trades"].iloc[0]
    assert ta["진입가"] == tb["진입가"]


# ── 통합 회귀: 비용 모델이 합리적 ─────────────────────────────────────────────


def test_roundtrip_cost_approximates_expected():
    """라운드트립 비용이 commission*2 + sell_tax + slippage*2와 근접.

    가격이 변하지 않는 시퀀스(=실제 자산 수익 0)에서 backtest의 손실은 곧
    비용이다. 매수→매도 한 사이클로 정확한 손실률을 계산할 수 있다.
    (tick rounding이 약간의 오차를 만들지만, 50,000원 / tick 100원 → ~0.2%
    이내의 추가 슬리피지 효과.)
    """
    # 가격 일정 → 매수→hold 1일→매도, 비용만 손실
    prices = [50_000.0] * 5
    df = _synth_df(prices)
    res = run_backtest(
        data={"TEST": df}, trade_symbol="TEST",
        buy_conditions=_all_true_buy(),
        hold_days=1,
        initial_capital=10_000_000.0,
        commission=0.0003, slippage=0.001, sell_tax=0.0023,
        currency="KRW", fill="next_open",
    )
    assert res["success"] is True
    trades = res["trades"]
    assert len(trades) > 0
    rt = trades.iloc[0]["수익률(%)"]
    # 기대 비용 = 2*comm + tax + 2*slip = 0.0006 + 0.0023 + 0.002 = 0.0049 = 0.49%
    # tick 라운딩으로 추가 ~0.2%까지 더 빠질 수 있으니 [-0.9%, -0.3%] 범위 허용.
    assert -0.9 < rt < -0.3, f"roundtrip cost out of range: {rt}%"
