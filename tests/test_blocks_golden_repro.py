"""P0-7 — Phase 0 완료 게이트: golden 5전략 조건의 새 평가기 재현.

명세 §14 Phase 0 검증. golden_backtest.STRATEGIES의 **원본** 조건 dict를 그대로
가져와(재타이핑 drift 방지) 새 evaluate로 평가한 마스크가 기존 build_signal_mask와
비트 동일함을 고정한다. 이게 통과하면 Phase 1에서 백테스트 엔진의
build_signal_mask를 새 평가기로 교체해도 golden metric이 안 바뀐다.

합성 005930(결정론적)로 검증 — 전체 dataset 로드(수분) 없이 CI 안전.

    cd platform && pytest tests/test_blocks_golden_repro.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT / "tests"))

from quant_core.analysis import build_signal_mask  # noqa: E402
from quant_core.blocks import EvalContext, Node, const, data, evaluate, select_symbol  # noqa: E402

from golden_backtest import STRATEGIES, TEST_SYMBOL  # noqa: E402


def _synthetic() -> dict[str, pd.DataFrame]:
    """golden 조건이 참조하는 지표 컬럼을 가진 합성 dataset."""
    idx = pd.date_range("2020-01-01", periods=300, freq="B")

    def mk(seed):
        r = np.random.default_rng(seed)
        return pd.DataFrame({
            "price_level": r.uniform(50, 150, 300),
            "ma_dev_20d": r.uniform(-5, 5, 300),
            "ma_gap_20_60": r.uniform(-3, 3, 300),
            "bb_pct": r.uniform(0, 1, 300),
            "pct_change_20d": r.uniform(-10, 10, 300),
            "pct_change_252d": r.uniform(-20, 20, 300),
        }, index=idx)

    return {TEST_SYMBOL: mk(1), "000660": mk(2)}


def _to_node(conditions, logic) -> Node:
    """golden 서브셋(compare self-ref vs const) 조건 dict → Node 트리."""
    def cond_node(c):
        left = c["left"]
        right = c["right"]
        ln = data(f'{left["symbol"]}.{left["indicator"]}')
        rn = (const(right["value"]) if right.get("kind") == "constant"
              else data(f'{right["symbol"]}.{right["indicator"]}'))
        return Node(op="compare", params={"op": c["op"]}, inputs={"left": ln, "right": rn})

    if len(conditions) == 1:
        return cond_node(conditions[0])
    return Node(op="logic", params={"logic": logic},
                inputs={str(i): cond_node(c) for i, c in enumerate(conditions)})


def _reproduces(name: str, data_dict: dict) -> int:
    cfg = STRATEGIES[name]
    conds = cfg["buy_conditions"]
    logic = cfg["buy_logic"]
    old = build_signal_mask(data_dict, conds, logic, current_symbol=TEST_SYMBOL)
    node = _to_node(conds, logic)
    ctx = EvalContext.from_dataset(data_dict)
    new = select_symbol(evaluate(node, ctx), TEST_SYMBOL).reindex(old.index).fillna(False).astype(bool)
    pd.testing.assert_series_equal(new, old, check_names=False)
    return int(old.sum())


def test_all_golden_strategies_reproduced():
    """golden 5전략 buy 조건 전부 새 평가기로 비트 동일 재현."""
    data_dict = _synthetic()
    reproduced = []
    for name in STRATEGIES:
        n_true = _reproduces(name, data_dict)
        reproduced.append((name, n_true))
    # 5전략 모두 처리됐고, 적어도 일부는 비공허(전부 빈 마스크면 평가기 무너짐)
    assert len(reproduced) == len(STRATEGIES)
    assert any(n > 0 for _, n in reproduced), f"전부 빈 마스크 — 평가기 의심: {reproduced}"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
