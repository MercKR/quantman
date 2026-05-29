"""IR 백테스트 요청 처리 — HTTP/DB와 분리된 순수 핵심 (서버 라우터가 감쌈).

명세 §11(처리절차)·§5·§6. 요청 spec(dict) → Node 파싱 → 메타규칙+무결성 검증 →
기본값 주입 → run_backtest_ir → 결과(+경고). 서버/웹 모두 이 함수를 통한다.

순수 함수라 헤드리스 단위테스트 가능(test_engine_service.py).
"""

from __future__ import annotations

import pandas as pd

from ..blocks import (
    DatasetMeta, Node, apply_defaults, available_refs, integrity_issues, validate,
)
from ..blocks.validate import prioritize
from .backtest import run_backtest_ir

# run_backtest_ir로 그대로 전달할 청산/체결/기간 파라미터 (None이면 drop → 엔진 기본값).
_EXIT_KW = (
    "hold_days", "take_profit", "stop_loss", "trail_atr_mult", "trail_pct",
    "sell_amount_pct", "rule_sell_pcts", "fill", "commission", "slippage",
    "sell_tax", "currency", "initial_capital", "start", "end",
)


def _issue_dict(i) -> dict:
    return {"rule": i.rule, "severity": i.severity, "message": i.message, "path": i.path}


def _parse(spec: dict, key: str):
    raw = spec.get(key)
    if raw is None:
        return None, None
    try:
        return Node.model_validate(raw), None
    except Exception as e:  # noqa: BLE001 — 사용자 입력 파싱 실패는 메시지로 반환
        return None, f"{key} 파싱 오류: {e}"


def backtest_from_spec(
    spec: dict,
    dataset: dict[str, pd.DataFrame],
    *,
    valid_refs: set[str] | None = None,
    meta: DatasetMeta | None = None,
) -> dict:
    """IR 전략 spec을 검증·실행. 실패 시 {success:False, error, issues}.

    spec: {trade_symbol, buy(Node dict), sell?(Node dict), 청산/체결 파라미터...}
    valid_refs: 규칙0 데이터 가용성 검사용 (없으면 dataset에서 자동 생성).
    meta: 무결성 검사용 DatasetMeta (없으면 기본값 — delay=1).
    """
    trade_symbol = spec.get("trade_symbol")
    if not trade_symbol:
        return {"success": False, "error": "trade_symbol이 필요합니다."}
    if "buy" not in spec or spec.get("buy") is None:
        return {"success": False, "error": "매수 신호(buy)가 필요합니다."}

    buy, err = _parse(spec, "buy")
    if err:
        return {"success": False, "error": err}
    sell, err = _parse(spec, "sell")
    if err:
        return {"success": False, "error": err}

    if valid_refs is None:
        valid_refs = available_refs(dataset)
    if meta is None:
        meta = DatasetMeta()

    # 규칙0·1·2·3 (메타규칙) + 규칙4 (무결성)
    issues = list(validate(buy, valid_refs)) + list(integrity_issues(buy, meta))
    if sell is not None:
        issues += list(validate(sell, valid_refs)) + list(integrity_issues(sell, meta))
    issues = prioritize(issues)
    errors = [i for i in issues if i.is_error]
    if errors:
        return {"success": False, "error": errors[0].message,
                "issues": [_issue_dict(i) for i in issues]}

    # 규칙5 — 빈칸 기본값 주입
    buy = apply_defaults(buy)
    sell = apply_defaults(sell) if sell is not None else None

    exit_kw = {k: spec[k] for k in _EXIT_KW if k in spec and spec[k] is not None}
    res = run_backtest_ir(dataset, trade_symbol, buy, sell_node=sell, **exit_kw)
    # 비-error 무결성 경고(예: 펀더멘털 PIT 미태깅)를 결과에 동봉
    res["warnings"] = [_issue_dict(i) for i in issues]
    return res
