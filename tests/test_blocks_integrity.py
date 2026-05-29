"""P0-6 — 무결성 게이트 회귀 (delay·PIT·causal).

명세 §6. look-ahead 가드(apply_delay)의 실동작과 PIT/causal 검출을 고정한다.

    cd platform && pytest tests/test_blocks_integrity.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

from quant_core.blocks import (  # noqa: E402
    DatasetMeta, Node, apply_delay, data, integrity_issues,
)


# ── look-ahead 가드 ───────────────────────────────────────────────────────────

def test_apply_delay_shifts():
    idx = pd.date_range("2021-01-01", periods=5, freq="B")
    panel = pd.DataFrame({"AAA": [1, 2, 3, 4, 5]}, index=idx, dtype=float)
    out = apply_delay(panel, 1)
    pd.testing.assert_frame_equal(out, panel.shift(1))


def test_apply_delay_zero_noop():
    idx = pd.date_range("2021-01-01", periods=3, freq="B")
    panel = pd.DataFrame({"AAA": [1.0, 2.0, 3.0]}, index=idx)
    pd.testing.assert_frame_equal(apply_delay(panel, 0), panel)


# ── 데이터 시점: delay ────────────────────────────────────────────────────────

def test_delay_lt1_flagged():
    node = Node(op="rank", inputs={"signal": data("Close")})
    issues = integrity_issues(node, DatasetMeta(delay=0, has_pit=True))
    assert any("delay" in i.message for i in issues)
    assert all(i.severity == 40 for i in issues)  # SEV_INTEGRITY


def test_delay_ok():
    node = Node(op="rank", inputs={"signal": data("Close")})
    issues = integrity_issues(node, DatasetMeta(delay=1, has_pit=True))
    assert not any("delay" in i.message for i in issues)


# ── 데이터 시점: PIT (펀더멘털 사용 시에만) ───────────────────────────────────

def test_pit_warns_only_with_fundamentals():
    # 펀더멘털(roic) 참조 + PIT 미태깅 → 경고
    fund_node = Node(op="rank", inputs={"signal": data("__SELF__.roic")})
    assert any("PIT" in i.message for i in integrity_issues(fund_node, DatasetMeta(has_pit=False)))
    # OHLCV/기술지표만 → PIT 경고 없음 (노이즈 방지)
    tech_node = Node(op="rank", inputs={"signal": data("Close")})
    assert not any("PIT" in i.message for i in integrity_issues(tech_node, DatasetMeta(has_pit=False)))


def test_pit_ok_when_tagged():
    fund_node = Node(op="rank", inputs={"signal": data("__SELF__.roic")})
    assert not any("PIT" in i.message for i in integrity_issues(fund_node, DatasetMeta(has_pit=True)))


# ── 파라미터 시점: causal (현재 카탈로그 전부 causal) ─────────────────────────

def test_all_current_blocks_causal():
    node = Node(op="rank", inputs={"signal":
        Node(op="ts_mean", params={"window": 20}, inputs={"signal": data("Close")})})
    # meta 없이 param-time만 → 비-causal 블록 없으므로 이슈 0
    assert integrity_issues(node) == []


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
