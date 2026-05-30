"""L-04 회귀 — intraday stop 매도 발주 직전 over-sell 클램프.

장중 사용자가 HTS/MTS에서 수동 매도했을 때 ledger는 그대로 남아 있으므로,
ledger 기반으로 매도하면 over-sell(KIS reject 또는 short-sell). 발주 직전에
broker.account_snapshot()으로 실 보유를 확인하고 min(ledger, broker)로 클램프.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_LOCAL_DIR = Path(__file__).resolve().parent.parent
if str(_LOCAL_DIR) not in sys.path:
    sys.path.insert(0, str(_LOCAL_DIR))

from localapp.intraday_stop import IntradayStopManager


def _strat_def_for_loss():
    """손절 -1%로 항상 트리거되는 최소 IR 전략 정의."""
    return {
        "name": "T", "engine": "ir",
        "universe": {"kind": "single", "symbols": ["005930"]},
        "signal": {"op": "compare", "params": {"op": ">"},
                   "inputs": {"left": {"op": "data", "params": {"ref": "__SELF__.Close"}},
                              "right": {"op": "const", "params": {"value": 0}}}},
        "position": {"direction": "long", "entry": {"mode": "on_signal"},
                     "exit": {"stop_loss": -1.0}},
    }


def _ledger_one(symbol="005930", qty=10, entry=100.0, peak=100.0):
    # 원장 엔트리가 definition을 자기완결로 보유(production _apply_fill과 동형) —
    # on_tick은 pos["definition"]으로 청산 룰을 읽는다.
    return {
        "T:005930": {
            "symbol": symbol, "qty": qty,
            "entry_price": entry, "peak_price": peak,
            "strategy_name": "T", "definition": _strat_def_for_loss(),
        }
    }


def _mgr_with(broker_snapshot, ledger=None, submit=None):
    broker = MagicMock()
    broker.account_snapshot.side_effect = broker_snapshot
    submit = submit or MagicMock()
    mgr = IntradayStopManager(
        broker=broker,
        get_ledger=lambda: ledger or _ledger_one(),
        submit_sell_fn=submit,
        dataset={},
    )
    return mgr, broker, submit


def test_clamps_to_broker_qty_when_user_partially_sold():
    """ledger 10 vs broker 6 → 매도 6주로 클램프."""
    mgr, broker, submit = _mgr_with(
        broker_snapshot=lambda: {"positions": [{"symbol": "005930", "qty": 6}]})
    mgr.on_tick("005930", 98.0)  # -2%, 손절 트리거
    assert submit.call_count == 1
    args = submit.call_args.args
    # signature: (ledger_key, strat_name, symbol, qty, ref_price, policy, reason, decisions)
    assert args[3] == 6


def test_skips_and_marks_sold_when_broker_qty_zero():
    """ledger 10 vs broker 0 → 외부 전량 매도. submit 안 함, _sold_today에 표시."""
    mgr, broker, submit = _mgr_with(
        broker_snapshot=lambda: {"positions": []})
    mgr.on_tick("005930", 98.0)
    submit.assert_not_called()
    assert "T:005930" in mgr._sold_today


def test_skips_tick_when_snapshot_fails_with_no_cache():
    """스냅샷 실패 + 캐시 없음 → submit skip(다음 tick에 재시도)."""
    def _raise():
        raise RuntimeError("KIS down")
    mgr, broker, submit = _mgr_with(broker_snapshot=_raise)
    mgr.on_tick("005930", 98.0)
    submit.assert_not_called()
    # _sold_today에 추가 안 됨 → 다음 tick에 재시도 가능
    assert "T:005930" not in mgr._sold_today


def test_uses_cache_within_ttl():
    """TTL 안에서는 account_snapshot이 1회만 호출됨 (rate limit 보호)."""
    calls = {"n": 0}
    def _snap():
        calls["n"] += 1
        return {"positions": [{"symbol": "005930", "qty": 10}]}
    mgr, broker, submit = _mgr_with(broker_snapshot=_snap)
    mgr.on_tick("005930", 98.0)
    mgr.on_tick("005930", 97.0)
    # 첫 tick에서 _sold_today에 들어가 두 번째 tick은 매도 평가 안 함 →
    # snapshot도 한 번만 호출 (1tick 1호출).
    assert calls["n"] == 1


def test_passes_through_when_broker_matches_ledger():
    """ledger 10 == broker 10 → 그대로 10주 매도."""
    mgr, broker, submit = _mgr_with(
        broker_snapshot=lambda: {"positions": [{"symbol": "005930", "qty": 10}]})
    mgr.on_tick("005930", 98.0)
    assert submit.call_args.args[3] == 10
