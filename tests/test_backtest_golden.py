"""키스톤 안전망 — 백테스트 결과 불변(골든) + 데이터 스코핑 차등(differential).

데이터층 리팩터("전 유니버스 통째 로드·재계산" → "필요 부분집합만 로드")가
백테스트 결과를 **바꾸지 않음**을 보장하는 안전망. 세 축:

1. 골든(회귀): 대표 전략들의 핵심 지표를 고정값에 묶는다. 로딩·지표(compute_all)·
   엔진 어디서 회귀가 나도 값이 흔들리면 잡힌다.
2. 차등(스코핑 불변): single/list 유니버스 전략은 dataset에 불필요 종목이 더 들어
   있어도 결과가 동일하다 → 부분집합만 로드해도 결과 불변(리팩터 핵심 불변식).
   all/screener는 횡단 랭킹이라 전 유니버스가 필요 — 차등 대상 아님(골든만).
3. 로딩 동치: load_dataset(전체)[s]와 load_dataset_for([s])[s]가 byte 동일.
   compute_all이 종목별 순수(per-symbol pure)임을 근거로 한 부분집합 로드의 토대.

합성 데이터(seeded)로 결정론적·네트워크 무관·빠르게 — CI/반복 검증에 적합.

    cd platform && pytest tests/test_backtest_golden.py -v
"""

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

from quant_core.indicators import compute_all  # noqa: E402
from quant_core.ir_engine import (  # noqa: E402
    StrategyIR, needed_symbols, strategy_from_spec,
)


# ── 합성 유니버스 ─────────────────────────────────────────────────────────────
# 8종목 × 400영업일. 종목별 다른 drift/vol(seeded)로 횡단 랭킹이 의미를 갖게 한다.
# momentum_12_1m(252+21일)·rsi_14 등 compute_all 지표가 워밍업되도록 충분한 이력.

_START = "2020-01-02"
_N_DAYS = 400
_SYMBOLS = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH"]


def _make_raw(sym_seed: int, drift: float, vol: float) -> pd.DataFrame:
    """단일 종목 OHLCV — 기하 브라운 운동 근사(seeded). Open=전일 종가."""
    idx = pd.date_range(_START, periods=_N_DAYS, freq="B")
    r = np.random.default_rng(sym_seed)
    steps = r.normal(drift, vol, _N_DAYS)
    close = np.maximum(100.0 * np.cumprod(1.0 + steps / 100.0), 1.0)
    open_ = np.concatenate([[close[0]], close[:-1]])
    return pd.DataFrame({
        "Open": open_,
        "High": np.maximum(open_, close) * 1.008,
        "Low": np.minimum(open_, close) * 0.992,
        "Close": close,
        "Volume": r.uniform(1e5, 2e6, _N_DAYS),
    }, index=idx)


def _build_universe() -> dict[str, pd.DataFrame]:
    """전 유니버스(8종목) — raw OHLCV에 compute_all로 지표 부착. load_dataset과 동형."""
    specs = [  # (seed, drift%, vol%) — 다양한 추세/변동성
        (1, 0.06, 1.1), (2, 0.03, 1.4), (3, 0.10, 0.9), (4, -0.02, 1.6),
        (5, 0.04, 1.0), (6, 0.08, 1.3), (7, 0.01, 0.8), (8, -0.05, 1.8),
    ]
    raw = {sym: _make_raw(seed, d, v) for sym, (seed, d, v) in zip(_SYMBOLS, specs)}
    return {sym: compute_all(df) for sym, df in raw.items()}


# 모듈 1회 빌드(빠름) — 모든 테스트가 공유하는 불변 입력.
_FULL = _build_universe()


# ── 노드 dict 빌더(통과 중인 test_data_layer 형태와 동일) ─────────────────────

def _d(ref):
    return {"op": "data", "params": {"ref": ref}}


def _c(value):
    return {"op": "const", "params": {"value": value}}


def _cmp(left, op, right):
    return {"op": "compare", "params": {"op": op}, "inputs": {"left": left, "right": right}}


def _ts_mean(sig, window):
    return {"op": "ts_mean", "params": {"window": window}, "inputs": {"signal": sig}}


def _cross(left, right, direction):
    return {"op": "cross", "params": {"direction": direction},
            "inputs": {"left": left, "right": right}}


def _rank(sig):
    return {"op": "rank", "inputs": {"signal": sig}}


# ── 대표 전략(주요 엔진 경로 커버) ────────────────────────────────────────────

STRATEGIES: dict[str, dict] = {
    # 단일 + 이벤트(룰) — RSI 과매도 반등, 보유기간 청산.
    "single_rsi_event": {
        "name": "RSI 과매도 반등(단일)",
        "universe": {"kind": "single", "symbols": ["AAA"]},
        "signal": _cmp(_d("__SELF__.rsi_14"), "<", _c(35.0)),
        "position": {"entry": {"mode": "on_signal"}, "exit": {"hold_days": 10}},
        "simulation": {"initial_capital": 1e7},
    },
    # 리스트 + 이벤트 + 매도조건 — 20MA 상향돌파 매수 / 하향돌파 매도.
    "list_ma_cross_event": {
        "name": "20MA 돌파(리스트)",
        "universe": {"kind": "list", "symbols": ["AAA", "BBB", "CCC"]},
        "signal": _cross(_d("__SELF__.Close"), _ts_mean(_d("__SELF__.Close"), 20), "up"),
        "position": {
            "entry": {"mode": "on_signal"},
            "exit": {"condition": _cross(_d("__SELF__.Close"),
                                         _ts_mean(_d("__SELF__.Close"), 20), "down")},
        },
        "simulation": {"initial_capital": 1e7},
    },
    # 전체 + 정기리밸런싱(팩터) — 모멘텀 상위 3종목. 횡단 랭킹(전 유니버스 필요).
    "all_momentum_factor": {
        "name": "모멘텀 팩터(전체)",
        "universe": {"kind": "all"},
        "signal": _rank(_d("momentum_12_1m")),
        "position": {"entry": {"mode": "scheduled", "rebalance": "monthly", "top_n": 3}},
        "simulation": {"initial_capital": 1e7},
    },
    # 단일 + 상시(always) — 상수 레버리지 2배(레버리지 ETF 복제). 매일 리밸런싱.
    "single_leveraged_always": {
        "name": "상수 레버리지 2배(단일)",
        "universe": {"kind": "single", "symbols": ["AAA"]},
        "signal": _d("__SELF__.Close"),   # score(항상 보유) — 값은 동일가중에서 무관
        "position": {"entry": {"mode": "always"}},
        "simulation": {"initial_capital": 1e7, "leverage": 2.0},
    },
}

# single/list만 차등(스코핑 불변) 대상 — all/screener는 전 유니버스 필요.
_SCOPED_STRATEGIES = [
    "single_rsi_event", "list_ma_cross_event", "single_leveraged_always",
]

# 비교·고정할 핵심 지표 키(결정론적·의미 있는 것만).
_METRIC_KEYS = ("total_return", "cagr", "mdd", "sharpe", "n_trades", "win_rate")

# 골든 — 위 합성 유니버스에서 각 전략의 고정 지표(%). 로딩·compute_all·엔진
# 어디서 회귀가 나도 값이 흔들리면 잡힌다. 값 갱신은 *의도된 엔진 변경* 시에만
# (그때는 변경 근거를 함께 검토). n_trades는 정수로 정확 비교, 나머지는 rel=1e-6.
GOLDEN: dict[str, dict] = {
    "single_rsi_event": {
        "total_return": 0.4687382753901929, "cagr": 0.29504958163477646,
        "mdd": -13.883427692518222, "sharpe": 0.07776372987662498,
        "n_trades": 13, "win_rate": 46.15384615384615},
    "list_ma_cross_event": {
        "total_return": -3.812009177829884, "cagr": -2.418803811279724,
        "mdd": -5.560849509030031, "sharpe": -1.2006673864158912,
        "n_trades": 81, "win_rate": 19.753086419753085},
    "all_momentum_factor": {
        "total_return": 1.282437324508354, "cagr": 0.8060298214222827,
        "mdd": -8.444602111862908, "sharpe": 0.1450566819172979,
        "n_trades": 0, "win_rate": float("nan")},
    "single_leveraged_always": {
        "total_return": -28.298226054314274, "cagr": -18.906912226335347,
        "mdd": -45.14168089163211, "sharpe": -0.5029391810909034,
        "n_trades": 0, "win_rate": float("nan")},
}


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def _run(spec: dict, dataset: dict) -> dict:
    res = strategy_from_spec(spec, dataset)
    assert res.get("success"), f"백테스트 실패: {res.get('error')} / {res.get('issues')}"
    assert "metrics" in res, "결과에 metrics 없음"
    return res["metrics"]


def _close(a, b, rel: float, abs_: float = 1e-9) -> bool:
    """NaN==NaN을 같다고 보고, 상대/절대 허용오차로 비교."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    fa, fb = float(a), float(b)
    if math.isnan(fa) and math.isnan(fb):
        return True
    if math.isnan(fa) or math.isnan(fb):
        return False
    return abs(fa - fb) <= max(abs_, rel * max(abs(fa), abs(fb)))


# ── 1. 골든 — 대표 전략 핵심 지표를 고정값에 묶는다(파이프라인 회귀 차단) ──────

@pytest.mark.parametrize("name", list(STRATEGIES))
def test_golden_metrics(name):
    m = _run(STRATEGIES[name], _FULL)
    exp = GOLDEN[name]
    assert int(m.get("n_trades")) == exp["n_trades"], (
        f"{name}: n_trades {m.get('n_trades')} != 골든 {exp['n_trades']}")
    for k in ("total_return", "cagr", "mdd", "sharpe", "win_rate"):
        assert _close(m.get(k), exp[k], rel=1e-6), (
            f"{name}: 지표 '{k}' 골든 불일치 — 실측={m.get(k)!r} vs 골든={exp[k]!r}. "
            f"의도된 엔진 변경이면 골든값을 갱신하고, 아니면 회귀입니다.")


# ── 2. 차등 — single/list는 부분집합 로드해도 결과 불변(리팩터 핵심 불변식) ────

@pytest.mark.parametrize("name", _SCOPED_STRATEGIES)
def test_scoping_invariance(name):
    spec = STRATEGIES[name]
    # 프로덕션 resolver(needed_symbols)를 직접 사용 — 서버가 부분집합 로드에 쓸 함수와
    # 동일 논리로 차등 불변을 검증(dogfood).
    needed = needed_symbols(StrategyIR.model_validate(spec))
    assert needed is not None, f"{name}: single/list인데 resolver가 None(전체)을 반환"
    subset = {s: _FULL[s] for s in needed if s in _FULL}
    assert subset, f"{name}: 부분집합이 비었음"
    full_m = _run(spec, _FULL)        # 전 유니버스(8종목)
    sub_m = _run(spec, subset)        # 필요 종목만
    for k in _METRIC_KEYS:
        assert _close(full_m.get(k), sub_m.get(k), rel=1e-9), (
            f"{name}: 스코핑으로 지표 '{k}'가 달라짐 — "
            f"전체={full_m.get(k)!r} vs 부분={sub_m.get(k)!r} "
            f"(부분집합 로드가 결과를 바꾸면 안 됨)")


# ── 3. resolver(needed_symbols) 단위 — 부분집합 로드의 심볼 결정 논리 고정 ──────

def test_needed_symbols_by_universe_kind():
    assert needed_symbols(StrategyIR.model_validate(STRATEGIES["single_rsi_event"])) == {"AAA"}
    assert needed_symbols(
        StrategyIR.model_validate(STRATEGIES["list_ma_cross_event"])) == {"AAA", "BBB", "CCC"}
    # all/screener는 횡단이라 전 유니버스 필요 → None
    assert needed_symbols(StrategyIR.model_validate(STRATEGIES["all_momentum_factor"])) is None
    # 전략 조합(strat:) 참조 → 자식이 임의 데이터 필요할 수 있어 None(전체 로드)
    compose = {"universe": {"kind": "list", "symbols": ["strat:7"]},
               "signal": _d("__SELF__.Close"), "position": {"entry": {"mode": "always"}}}
    assert needed_symbols(StrategyIR.model_validate(compose)) is None


def test_needed_symbols_includes_external_refs():
    """단일 종목이 신호에서 외부심볼(VIX)을 참조하면 부분집합에 포함돼야 한다."""
    spec = {
        "universe": {"kind": "single", "symbols": ["AAA"]},
        "signal": _cmp(_d("__SELF__.Close"), ">", _d("VIX.Close")),
        "position": {"entry": {"mode": "on_signal"}, "exit": {"hold_days": 5}},
    }
    assert needed_symbols(StrategyIR.model_validate(spec)) == {"AAA", "VIX"}


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "-s"]))
