"""S1 — StrategyIR 스키마 + 정합성 검증 회귀.

명세 §7·§3.3. 전략 구조가 룰·팩터 전략을 빠짐없이 표현하고, 신호타입×진입/방향
호환 등 구조 규칙을 강제하는지 고정한다.

    cd platform && pytest tests/test_engine_spec.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

from quant_core.blocks import Node, const, data  # noqa: E402
from quant_core.ir_engine import (  # noqa: E402
    Entry, PositionSpec, Sizing, StrategyIR, Universe, validate_strategy,
)


def _cond():
    return Node(op="compare", params={"op": ">"},
                inputs={"left": data("__SELF__.ma_dev_20d"), "right": const(0.0)})


def _score():
    return Node(op="rank", inputs={"signal": data("momentum_12_1m")})


def _errs(s):
    return [i for i in validate_strategy(s) if i.is_error]


# ── 정상 구조 ─────────────────────────────────────────────────────────────────

def test_rule_strategy_valid():
    """룰: 단일종목 + 조건신호 + on_signal + 손익절."""
    s = StrategyIR(
        signal=_cond(),
        universe=Universe(kind="single", symbols=["005930"]),
        position=PositionSpec(
            entry=Entry(mode="on_signal"),
        ),
    )
    assert _errs(s) == []


def test_factor_strategy_valid():
    """팩터: 전체 유니버스 + 점수신호 + 정기리밸런싱 + 상위N + 롱숏."""
    s = StrategyIR(
        signal=_score(),
        universe=Universe(kind="all"),
        position=PositionSpec(
            direction="long_short",
            sizing=Sizing(mode="signal_proportional"),
            entry=Entry(mode="scheduled", rebalance="monthly", top_n=20),
        ),
    )
    assert _errs(s) == []


# ── 구조 규칙 위반 ────────────────────────────────────────────────────────────

def test_on_signal_requires_condition():
    s = StrategyIR(signal=_score(), universe=Universe(kind="single", symbols=["005930"]),
                   position=PositionSpec(entry=Entry(mode="on_signal")))
    assert any(i.rule == "S-entry" for i in validate_strategy(s))


def test_long_short_requires_score():
    s = StrategyIR(signal=_cond(), universe=Universe(kind="all"),
                   position=PositionSpec(direction="long_short", entry=Entry(mode="scheduled")))
    assert any(i.rule == "S-dir" for i in validate_strategy(s))


def test_signal_proportional_requires_score():
    s = StrategyIR(signal=_cond(), universe=Universe(kind="all"),
                   position=PositionSpec(sizing=Sizing(mode="signal_proportional"),
                                         entry=Entry(mode="scheduled")))
    assert any(i.rule == "S-size" for i in validate_strategy(s))


def test_single_universe_needs_one_symbol():
    s = StrategyIR(signal=_cond(), universe=Universe(kind="single", symbols=[]),
                   position=PositionSpec(entry=Entry(mode="on_signal")))
    assert any(i.rule == "S-univ" for i in validate_strategy(s))


def test_on_signal_all_universe_rejected():
    s = StrategyIR(signal=_cond(), universe=Universe(kind="all"),
                   position=PositionSpec(entry=Entry(mode="on_signal")))
    assert any(i.rule == "S-univ" for i in validate_strategy(s))


def test_exit_condition_must_be_condition():
    from quant_core.ir_engine import Exit
    s = StrategyIR(
        signal=_cond(), universe=Universe(kind="single", symbols=["005930"]),
        position=PositionSpec(entry=Entry(mode="on_signal"),
                              exit=Exit(mode="on_condition", condition=_score())))
    assert any(i.rule == "S-exit" for i in validate_strategy(s))


def test_roundtrip_serialization():
    s = StrategyIR(signal=_score(), universe=Universe(kind="all"),
                   position=PositionSpec(direction="long_short",
                                         entry=Entry(mode="scheduled", top_n=10)))
    restored = StrategyIR.model_validate(s.model_dump())
    assert restored == s


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
