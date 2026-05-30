"""백테스트 결과(pandas·numpy)를 JSON 안전 형태로 변환."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def _num(v: Any):
    """NaN/inf는 None으로, numpy 스칼라는 파이썬 기본형으로."""
    if v is None:
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(v, (np.bool_, bool)):
        return bool(v)
    return v


def clean_json(obj: Any):
    """중첩 dict/list의 NaN/inf→None, numpy 스칼라→파이썬형으로 정리.

    펼침·이벤트 resultset(버킷/윈도별 지표 dict)을 JSONResponse(allow_nan=False)에
    안전하게 통과시킨다 — n=0 버킷의 nan 지표가 500을 내지 않도록.
    """
    if isinstance(obj, dict):
        return {k: clean_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean_json(v) for v in obj]
    return _num(obj)


def _series_points(s: pd.Series) -> list[dict]:
    return [
        {"date": idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx),
         "value": _num(val)}
        for idx, val in s.items()
    ]


def serialize_backtest(result: dict) -> dict:
    """IR 엔진 backtest_from_spec 결과를 JSON 직렬화 가능한 dict로."""
    if not result.get("success"):
        return {"success": False, "error": result.get("error")}

    trades_df: pd.DataFrame = result["trades"]
    trades = []
    for _, row in trades_df.iterrows():
        rec = {}
        for k, v in row.items():
            if hasattr(v, "strftime"):
                rec[k] = v.strftime("%Y-%m-%d")
            else:
                rec[k] = _num(v)
        trades.append(rec)

    return {
        "success": True,
        "metrics": {k: _num(v) for k, v in result["metrics"].items()},
        "equity": _series_points(result["equity"]),
        "benchmark": _series_points(result["benchmark"]),
        "trades": trades,
    }
