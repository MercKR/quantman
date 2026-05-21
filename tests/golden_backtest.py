"""
Phase 8 — 백테스트 엔진 회귀 테스트 (golden cases).

5개 단순 전략을 고정 데이터·고정 파라미터로 실행하고 저장된 baseline과 비교한다.

함께 검증:
- **회귀:** 엔진 변경이 결과 metric을 바꾸면 즉시 감지
- **결정론성 (idempotency):** 같은 input 두 번 → 같은 결과
- **Look-ahead bias:** 끝 60일 자른 데이터셋과 원본을 같은 종료일까지 실행 시
  결과 동일 (다르면 미래 데이터 참조 의심)

실행:
    cd platform; pytest tests/golden_backtest.py -v

처음 baseline 생성 (의도적 명시 환경변수 필요):
    cd platform; $env:REGENERATE_BASELINE=1; pytest tests/golden_backtest.py::test_regenerate_baseline_all -v
    git add tests/golden_baseline.json
    git commit -m "test: golden backtest baseline"
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# core/ 패키지 경로 등록 (pytest 기준 CWD가 platform/이라고 가정)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))

from quant_core import load_dataset, run_backtest  # noqa: E402

BASELINE_PATH = Path(__file__).parent / "golden_baseline.json"

# 고정 환경 — 회귀 비교 안정성을 위해 변수 모두 상수
TEST_SYMBOL = "005930"           # 삼성전자: 가장 안정적인 장기 데이터
TEST_START = "2020-01-01"
TEST_END = "2023-12-31"
TEST_CAPITAL = 10_000_000.0
TRIM_DAYS = 60                   # look-ahead bias 검증 시 데이터 끝 자르는 폭

# 비교 tolerance — 백테스트는 결정론적이지만 float 오차 허용
RTOL = 1e-9
ATOL = 1e-6


# ── 5개 단순 전략 정의 ────────────────────────────────────────────────────────

STRATEGIES = {
    "01_buy_and_hold": {
        "description": "항상 참 (price_level > 0) + 252일 보유 → 시장 수익률 근사",
        "buy_conditions": [{
            "left": {"kind": "indicator", "symbol": "__SELF__", "indicator": "price_level"},
            "op": ">",
            "right": {"kind": "constant", "value": 0.0},
        }],
        "buy_logic": "AND",
        "hold_days": 252,
        "take_profit": None,
        "stop_loss": None,
        "sell_conditions": None,
    },
    "02_above_ma20": {
        "description": "20일 이평선 위 (ma_dev_20d > 0) + 20일 보유",
        "buy_conditions": [{
            "left": {"kind": "indicator", "symbol": "__SELF__", "indicator": "ma_dev_20d"},
            "op": ">",
            "right": {"kind": "constant", "value": 0.0},
        }],
        "buy_logic": "AND",
        "hold_days": 20,
        "take_profit": None,
        "stop_loss": None,
        "sell_conditions": None,
    },
    "03_uptrend": {
        "description": "정배열 (ma_gap_20_60 > 0) + 60일 보유, ±10/-5% 익절·손절",
        "buy_conditions": [{
            "left": {"kind": "indicator", "symbol": "__SELF__", "indicator": "ma_gap_20_60"},
            "op": ">",
            "right": {"kind": "constant", "value": 0.0},
        }],
        "buy_logic": "AND",
        "hold_days": 60,
        "take_profit": 0.10,
        "stop_loss": -0.05,
        "sell_conditions": None,
    },
    "04_oversold_bounce": {
        "description": "BB 하단 근접 (bb_pct < 0.2) + 10일 보유, +5/-3% 익절·손절",
        "buy_conditions": [{
            "left": {"kind": "indicator", "symbol": "__SELF__", "indicator": "bb_pct"},
            "op": "<",
            "right": {"kind": "constant", "value": 0.2},
        }],
        "buy_logic": "AND",
        "hold_days": 10,
        "take_profit": 0.05,
        "stop_loss": -0.03,
        "sell_conditions": None,
    },
    "05_dual_momentum": {
        "description": "20일·252일 동시 양의 모멘텀 + 60일 보유, -10% 손절",
        "buy_conditions": [
            {
                "left": {"kind": "indicator", "symbol": "__SELF__", "indicator": "pct_change_20d"},
                "op": ">",
                "right": {"kind": "constant", "value": 0.0},
            },
            {
                "left": {"kind": "indicator", "symbol": "__SELF__", "indicator": "pct_change_252d"},
                "op": ">",
                "right": {"kind": "constant", "value": 0.0},
            },
        ],
        "buy_logic": "AND",
        "hold_days": 60,
        "take_profit": None,
        "stop_loss": -0.10,
        "sell_conditions": None,
    },
}


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def dataset():
    """전체 데이터셋을 한 번만 로드 (지표 계산까지). 종목 없으면 skip."""
    data = load_dataset(with_indicators=True)
    if TEST_SYMBOL not in data:
        pytest.skip(f"테스트 종목 {TEST_SYMBOL} parquet 없음")
    if data[TEST_SYMBOL].empty:
        pytest.skip(f"테스트 종목 {TEST_SYMBOL} 데이터 비어있음")
    return data


def _run(strategy_name: str, data, *, end_override: str | None = None) -> dict:
    """전략 하나 실행. end_override로 종료일 덮어쓰기 (look-ahead 검증용)."""
    cfg = STRATEGIES[strategy_name]
    return run_backtest(
        data=data,
        trade_symbol=TEST_SYMBOL,
        buy_conditions=cfg["buy_conditions"],
        buy_logic=cfg["buy_logic"],
        hold_days=cfg["hold_days"],
        take_profit=cfg["take_profit"],
        stop_loss=cfg["stop_loss"],
        sell_conditions=cfg["sell_conditions"],
        initial_capital=TEST_CAPITAL,
        start=TEST_START,
        end=end_override or TEST_END,
    )


def _snapshot(result: dict) -> dict:
    """비교용 핵심 metric만 추출. dict 자체로 직렬화 가능해야 함."""
    # backtest는 정상 결과에도 "error": None을 포함한다. success 키만 신뢰.
    if not bool(result.get("success", True)):
        err = result.get("error") or "unknown"
        return {"success": False, "error": str(err)}
    m = result.get("metrics", {}) or {}

    def _safe(key, default=0.0):
        v = m.get(key, default)
        if v is None:
            return None
        try:
            return round(float(v), 6)
        except (TypeError, ValueError):
            return None

    return {
        "success": True,
        "total_return": _safe("total_return"),
        "n_trades": int(m.get("n_trades", 0) or 0),
        "win_rate": _safe("win_rate"),
        "mdd": _safe("mdd"),
        "cagr": _safe("cagr"),
        "sharpe": _safe("sharpe"),
    }


def _load_baseline() -> dict | None:
    if not BASELINE_PATH.exists():
        return None
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def _save_baseline(snapshot: dict) -> None:
    BASELINE_PATH.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _approx_eq(a, b) -> bool:
    if a is None or b is None:
        return a == b
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) <= max(ATOL, abs(float(b)) * RTOL)
    return a == b


# ── 테스트 ────────────────────────────────────────────────────────────────────

class TestGoldenBacktest:
    """5개 전략의 회귀 + 결정론성 + look-ahead 검증."""

    @pytest.mark.parametrize("name", list(STRATEGIES.keys()))
    def test_matches_baseline(self, name, dataset):
        """저장된 baseline metric과 일치 확인."""
        baseline = _load_baseline()
        if baseline is None:
            pytest.skip(
                "tests/golden_baseline.json 없음. 첫 실행 모드.\n"
                "baseline 생성: $env:REGENERATE_BASELINE=1; "
                "pytest tests/golden_backtest.py::test_regenerate_baseline_all -v"
            )
        if name not in baseline:
            pytest.skip(f"baseline에 '{name}' 없음. 재생성 필요.")

        snapshot = _snapshot(_run(name, dataset))
        expected = baseline[name]

        assert snapshot["success"] == expected["success"], (
            f"{name} success 불일치:\n  actual={snapshot}\n  baseline={expected}"
        )
        if not snapshot["success"]:
            return

        for key in ["total_return", "n_trades", "win_rate", "mdd", "cagr", "sharpe"]:
            assert _approx_eq(snapshot[key], expected[key]), (
                f"{name}.{key} 회귀:\n  actual={snapshot[key]}\n  baseline={expected[key]}"
            )

    @pytest.mark.parametrize("name", list(STRATEGIES.keys()))
    def test_idempotent(self, name, dataset):
        """같은 input 두 번 실행 → 결과 동일 (결정론성)."""
        r1 = _snapshot(_run(name, dataset))
        r2 = _snapshot(_run(name, dataset))
        assert r1 == r2, f"{name} 결정론성 위반:\n  1차={r1}\n  2차={r2}"

    @pytest.mark.parametrize("name", list(STRATEGIES.keys()))
    def test_no_lookahead_bias(self, name, dataset):
        """
        Look-ahead bias 검증.

        같은 종료일(cutoff)까지 백테스트할 때, 전체 데이터를 가진 dataset과
        cutoff 이후 데이터를 잘라낸 dataset의 결과가 같아야 한다.
        다르면 엔진이 cutoff 이후 미래를 참조한다는 뜻.
        """
        cutoff = (
            datetime.strptime(TEST_END, "%Y-%m-%d") - timedelta(days=TRIM_DAYS)
        ).strftime("%Y-%m-%d")

        # 끝 자른 dataset: TEST_SYMBOL만 자르고 나머지는 그대로
        # (조건이 self-ref만 쓰므로 cross-symbol 영향 없음 — 안전을 위해 전부 자름)
        trimmed = {}
        for sym, df in dataset.items():
            trimmed[sym] = df.loc[df.index <= cutoff].copy()

        original_truncated = _snapshot(_run(name, dataset, end_override=cutoff))
        trimmed_run = _snapshot(_run(name, trimmed, end_override=cutoff))

        assert original_truncated == trimmed_run, (
            f"{name} look-ahead 의심:\n"
            f"  원본(전체데이터, end={cutoff})={original_truncated}\n"
            f"  자름(끝자름, end={cutoff})={trimmed_run}\n"
            f"  → 엔진이 cutoff 이후 데이터를 참조하고 있음"
        )


# ── baseline 재생성 (명시적 환경변수 필요) ────────────────────────────────────

def test_regenerate_baseline_all(dataset):
    """
    모든 전략 실행 후 baseline 파일 재생성.

    의도적 환경변수 가드 — 평소엔 skip되어 실수로 baseline 덮어쓰지 않도록.

    실행:
        $env:REGENERATE_BASELINE=1
        pytest tests/golden_backtest.py::test_regenerate_baseline_all -v
    """
    if not os.environ.get("REGENERATE_BASELINE"):
        pytest.skip(
            "REGENERATE_BASELINE 환경변수 필요. baseline 의도적 재생성 시:\n"
            "  $env:REGENERATE_BASELINE=1; pytest tests/golden_backtest.py::test_regenerate_baseline_all -v"
        )

    snapshot = {}
    for name in STRATEGIES:
        result = _run(name, dataset)
        snap = _snapshot(result)
        snapshot[name] = snap
        print(f"\n  {name}: {snap}")

    _save_baseline(snapshot)
    print(f"\n[OK] baseline saved: {BASELINE_PATH}")
    print(f"     next: git add tests/golden_baseline.json && git commit -m 'test: golden backtest baseline'")
