"""블록 IR 백테스트 라우터 (신규 — 기존 /backtest·빌더와 병행, 충돌 0).

명세 §11·P1-6. 노코드 블록 트리(Node)를 받아 검증→백테스트→결과(+경고)를 반환.
기존 라우터는 그대로 두고 새 prefix /ir 로만 추가한다.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from quant_core.blocks import DatasetMeta, available_refs, catalog_spec
from quant_core.ir_engine import backtest_from_spec

from ..data_cache import get_dataset
from ..deps import get_current_user
from ..models import User
from ..serialize import serialize_backtest

router = APIRouter(prefix="/ir", tags=["ir"])


class IrBacktestIn(BaseModel):
    """IR 백테스트 요청 — buy/sell은 블록 Node 트리(dict)."""

    trade_symbol: str
    buy: dict
    sell: dict | None = None
    hold_days: int | None = None
    take_profit: float | None = None
    stop_loss: float | None = None
    trail_atr_mult: float | None = None
    trail_pct: float | None = None
    sell_amount_pct: float | None = None
    fill: str | None = None
    initial_capital: float = 10_000_000.0
    start: str | None = None
    end: str | None = None


@router.get("/catalog")
def ir_catalog(user: User = Depends(get_current_user)):
    """블록 카탈로그 — 빌더가 제공할 블록·슬롯·기본값 명세."""
    return {"blocks": catalog_spec()}


@router.post("/backtest")
def ir_backtest(body: IrBacktestIn, user: User = Depends(get_current_user)):
    """블록 IR 전략을 백테스트. 검증 실패 시 issues, 성공 시 결과+무결성 경고."""
    dataset = get_dataset()
    spec = body.model_dump(exclude_none=True)
    res = backtest_from_spec(
        spec, dataset,
        valid_refs=available_refs(dataset),
        meta=DatasetMeta(),
    )
    if not res.get("success"):
        return {"success": False, "error": res.get("error"),
                "issues": res.get("issues", [])}
    payload = serialize_backtest(res)
    payload["warnings"] = res.get("warnings", [])
    return payload
