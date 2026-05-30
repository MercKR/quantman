"""B1 — cycle/intraday loop이 실제로 dataset에서 인덱싱하는 종목 집합 계산.

전체 universe(~4468) 대신 (macro ∪ 전략타겟/후보 ∪ 보유 ∪ 조건참조)만
qc.load_dataset_for로 로드해 cycle 시작 지연(실측 5분+)을 수초로 단축한다.

왜 이 집합으로 충분한가:
  - 매수: _enter_from_preview가 신호를 재평가하지 않는다(preview가 평가 완료).
    candidate Close만 있으면 됨 → 전략 타겟/후보 종목.
  - 매도: trader._exit_reason_for → IR exit.condition 평가가 조건 참조 종목(예: S&P500)을
    data[symbol]로 접근. 보유분의 *자기 정의*(ledger pos["definition"]) 조건에서
    참조 종목을 추출해야 한다 (strategies 인자가 아니라).
  - 안전망: ALL_SYMBOLS(macro/asset ~51) 항상 포함 — 지수 참조는 거의 macro라
    referenced_symbols가 한 종목이라도 놓쳐도 빈 mask(신호 미발동)가 안 나게 한다.
"""

from __future__ import annotations

import quant_core as qc
from quant_core.blocks import Node
from quant_core.blocks import referenced_symbols as _node_refs


def _ir_symbols(strat_def: dict) -> set[str]:
    """IR 정의의 universe 종목 + 신호·매도조건 Node가 참조하는 외부 종목.

    universe.symbols(매매 타겟) + signal/exit.condition Node의
    referenced_symbols(예: 지수·VIX 참조). EOD 청산이 exit.condition을 평가하므로 그 참조
    종목이 dataset에 없으면 조건이 조용히 거짓 → 매도 미발동(fund-safety). 그래서 포함 필수.
    """
    out: set[str] = set((strat_def.get("universe") or {}).get("symbols") or [])
    exit_cond = ((strat_def.get("position") or {}).get("exit") or {}).get("condition")
    for raw in (strat_def.get("signal"), exit_cond):
        if raw:
            try:
                out |= _node_refs(Node.model_validate(raw))
            except Exception:   # noqa: BLE001 — 파싱 실패 시 universe 종목만(안전망 ALL_SYMBOLS 보완)
                pass
    return out


def _symbols_of(strat_def: dict) -> set[str]:
    """IR(전략 연구소) 정의의 타겟·참조 종목 집합."""
    return _ir_symbols(strat_def)


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
        needed |= _symbols_of(s.get("definition") or {})

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
        needed |= _symbols_of(pos.get("definition") or {})

    return needed
