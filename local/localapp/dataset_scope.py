"""B1 — cycle/intraday loop이 실제로 dataset에서 인덱싱하는 종목 집합 계산.

전체 universe(~4468) 대신 (macro ∪ 전략타겟/후보 ∪ 보유 ∪ 조건참조)만
qc.load_dataset_for로 로드해 cycle 시작 지연(실측 5분+)을 수초로 단축한다.

왜 이 집합으로 충분한가:
  - 매수: _enter_from_preview가 신호를 재평가하지 않는다(preview가 평가 완료).
    candidate Close만 있으면 됨 → 전략 타겟/후보 종목.
  - 매도: trader._evaluate_exit → build_signal_mask가 조건 참조 종목(예: S&P500)을
    data[symbol]로 접근. 보유분의 *자기 정의*(ledger pos["definition"]) 조건에서
    참조 종목을 추출해야 한다 (strategies 인자가 아니라).
  - 안전망: ALL_SYMBOLS(macro/asset ~51) 항상 포함 — 지수 참조는 거의 macro라
    referenced_symbols가 한 종목이라도 놓쳐도 빈 mask(신호 미발동)가 안 나게 한다.
"""

from __future__ import annotations

import quant_core as qc


def _refs(strat_def: dict) -> set[str]:
    """전략 정의의 buy/sell(신·구) 조건에서 참조 종목 추출."""
    out: set[str] = set()
    buy = (strat_def.get("buy") or {}).get("conditions") or []
    sell_rules = (strat_def.get("sell_rules") or {}).get("conditions") or []
    sell_legacy = (strat_def.get("sell") or {}).get("conditions") or []
    for nodes in (buy, sell_rules, sell_legacy):
        out |= qc.referenced_symbols(nodes)
    return out


def needed_symbols(strategies: list[dict] | None,
                   buy_candidates: list[dict] | None,
                   ledger: dict | None) -> set[str]:
    """이번 cycle이 dataset에서 접근할 종목 전체 집합.

    Args:
        strategies: 배정 전략 목록 [{id, name, definition}] — 매수 타겟·참조 추출.
        buy_candidates: server preview by_strategy — candidate 종목(방어적 추가).
        ledger: trader.ledger {key: pos} — 보유 종목 + 보유분 정의의 조건 참조.
    """
    needed: set[str] = set(qc.ALL_SYMBOLS)   # macro/asset 안전망

    for s in strategies or []:
        sdef = s.get("definition") or {}
        _, targets = qc.parse_trade_symbols(sdef.get("trade_symbol", ""))
        needed.update(targets)
        needed |= _refs(sdef)

    for entry in (buy_candidates or []):
        for c in (entry.get("candidates") or []):
            sym = c.get("symbol")
            if sym:
                needed.add(sym)

    # 보유 종목 — 매도 평가는 ledger pos의 자기 정의를 쓴다.
    for pos in (ledger or {}).values():
        sym = pos.get("symbol")
        if sym:
            needed.add(sym)
        needed |= _refs(pos.get("definition") or {})

    return needed
