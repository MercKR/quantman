"""Workbench 시나리오 — 리스크·안전 가드(A7).

발주 직전 가격 클램프(INV-PRICE-1)를 실제 _submit_buy 경로로 검증한다. full cycle
없이 발주 helper만 구동(intents·pending 모두 tmp 격리).
"""

from __future__ import annotations

import sys
from pathlib import Path

_LOCAL = Path(__file__).resolve().parent.parent.parent
if str(_LOCAL) not in sys.path:
    sys.path.insert(0, str(_LOCAL))


def test_buy_limit_clamped_to_daily_price_limit(isolated_trader):
    """INV-PRICE-1: 과도한 tolerance여도 매수 지정가는 한국 ±30% 상한으로 사전 클램프.

    KIS 서버 거부 누적을 막는 사전 클램프(qc.apply_daily_price_limit). tolerance
    100%면 limit이 ref의 2배로 가려 하지만 +30%(=ref*1.30) 부근으로 잘려야 한다.
    """
    t, broker = isolated_trader
    ref = 70000.0
    policy = {"use_limit": True, "buy_tolerance_pct": 100.0}   # 의도적 과도 tolerance

    t._submit_buy("s1", "T", {}, "005930", 10, ref, policy, [])

    limit = broker.submitted[-1]["limit"]
    assert limit < 140000, f"INV-PRICE-1: 클램프 안 됨(tolerance 그대로 적용) limit={limit}"
    assert ref < limit <= int(ref * 1.30) + 100, f"INV-PRICE-1: ±30% 상한 밖 limit={limit}"


def test_killswitch_blocks_new_buys(isolated_trader):
    """INV-KS-1: kill switch active면 cycle 진입 패스가 차단돼 신규 매수가 0이다.

    진입 패스는 _enter_from_preview 직전 ks_active 게이트로 막힌다(보유 청산은 별개).
    ledger·dataset 비어도 게이트가 buy_candidates 처리 전에 차단하므로 현실적 시세
    셋업 없이 검증 가능.
    """
    from localapp import killswitch
    t, broker = isolated_trader
    killswitch.activate("테스트 — 일일손실 한도 도달")
    assert killswitch.is_active()

    candidates = [{"strategy_id": "s1",
                   "candidates": [{"symbol": "005930"}],
                   "screener_members": ["005930"]}]
    payload = t.cycle(strategies=[], dataset={}, buy_candidates=candidates,
                      risk_limits={"kill_switch_daily_loss_pct": 3.0}, market="KRX")

    buys = [s for s in broker.submitted if s["side"] == "buy"]
    assert buys == [], f"INV-KS-1 위반: killswitch active인데 매수 발주됨 {buys}"
    assert any(d["action"] == "skip_killswitch" for d in payload["decisions"]), \
        "skip_killswitch 결정이 기록되지 않음"
