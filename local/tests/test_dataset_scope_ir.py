"""Stage 3-D — 로컬 dataset 스코프(needed_symbols)가 IR universe·참조 종목을 포함.

cycle/intraday loop이 dataset에서 인덱싱할 종목 집합을 IR 전략에 대해서도 정확히 산출해야
한다. 누락 시 IR 후보 Close 부재(매수 skip)·exit.condition 참조 부재(매도 조용히 미발동).

    cd platform/local && python -m pytest tests/test_dataset_scope_ir.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

_LOCAL = Path(__file__).resolve().parent.parent
if str(_LOCAL) not in sys.path:
    sys.path.insert(0, str(_LOCAL))

from localapp import dataset_scope

# 매도조건: [이 종목] Close < SPY Close  → 외부 참조 종목 = SPY (__SELF__ 제외)
_EXIT_COND = {
    "op": "compare", "params": {"op": "<"},
    "inputs": {"left": {"op": "data", "params": {"ref": "__SELF__.Close"}},
               "right": {"op": "data", "params": {"ref": "SPY.Close"}}},
}
_SIGNAL = {
    "op": "compare", "params": {"op": ">"},
    "inputs": {"left": {"op": "data", "params": {"ref": "__SELF__.Close"}},
               "right": {"op": "const", "params": {"value": 0}}},
}


def _ir_def(symbols, *, exit_cond=None):
    return {
        "name": "IR", "engine": "ir",
        "universe": {"kind": "list", "symbols": symbols},
        "signal": _SIGNAL,
        "position": {"direction": "long", "entry": {"mode": "on_signal"},
                     "exit": {"condition": exit_cond} if exit_cond else {}},
    }


def test_ir_universe_symbols_included():
    """IR universe.symbols(매매 타겟)가 needed에 포함."""
    strat = {"id": "s1", "definition": _ir_def(["005930", "AAPL"])}
    needed = dataset_scope.needed_symbols([strat], [], {})
    assert "005930" in needed
    assert "AAPL" in needed


def test_ir_exit_condition_refs_included():
    """exit.condition이 참조하는 외부 종목(SPY)이 needed에 포함 — 매도 평가용."""
    strat = {"id": "s1", "definition": _ir_def(["005930"], exit_cond=_EXIT_COND)}
    needed = dataset_scope.needed_symbols([strat], [], {})
    assert "SPY" in needed       # exit.condition 참조 → 없으면 조건 조용히 거짓
    assert "005930" in needed


def test_ir_held_position_definition_scoped():
    """보유 IR 포지션의 자기 definition에서도 universe·참조 종목 추출."""
    ledger = {"s1": {"symbol": "005930", "qty": 10,
                     "definition": _ir_def(["005930"], exit_cond=_EXIT_COND)}}
    needed = dataset_scope.needed_symbols([], [], ledger)
    assert "005930" in needed
    assert "SPY" in needed


def test_ir_invalid_def_falls_back_to_universe():
    """신호 Node 파싱 실패해도 universe 종목은 보존(안전)."""
    bad = {"engine": "ir", "universe": {"kind": "list", "symbols": ["005930"]},
           "signal": {"op": "__nonexistent__"}, "position": {}}
    needed = dataset_scope.needed_symbols([{"id": "s", "definition": bad}], [], {})
    assert "005930" in needed
