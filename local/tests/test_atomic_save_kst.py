"""L-02·L-06 회귀 — 원자적 저장 + KST 거래일.

L-02: _save_json은 tmp+os.replace로 원자 교체. 도중 크래시·디스크 가득참 등으로
.tmp가 남아도 본 파일은 항상 이전 완전본 또는 새 완전본 중 하나.
L-06: kst_today()는 PC tz와 무관하게 한국 시장 거래일을 돌려준다.
"""

from __future__ import annotations

import json
import sys
from datetime import date, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

_LOCAL_DIR = Path(__file__).resolve().parent.parent
if str(_LOCAL_DIR) not in sys.path:
    sys.path.insert(0, str(_LOCAL_DIR))

from localapp.trader import _save_json, kst_today


# ── L-02 ─────────────────────────────────────────────────────────────────────

def test_save_json_writes_and_replaces(tmp_path):
    """정상 저장 후 파일 내용이 일치하고, .tmp는 남지 않는다."""
    p = tmp_path / "ledger.json"
    _save_json(p, {"AAPL": {"qty": 10}})
    assert p.exists()
    assert json.loads(p.read_text(encoding="utf-8")) == {"AAPL": {"qty": 10}}
    assert not (tmp_path / "ledger.json.tmp").exists()


def test_save_json_atomic_on_serialize_failure(tmp_path):
    """직렬화 실패 시 본 파일은 손상되지 않고 .tmp만 남거나 정리된다.

    이전 구현(write_text)은 직렬화가 도중에 던지면 truncate된 본 파일이 남았다.
    원자 구현은 tmp에 먼저 쓰므로 본 파일은 그대로다.
    """
    p = tmp_path / "ledger.json"
    _save_json(p, {"prev": 1})            # 시드: 이전 완전본
    prev = p.read_text(encoding="utf-8")

    # json.dumps에서 예외 → tmp 쓰기 전에 raise
    class _Bad:
        pass
    with pytest.raises(TypeError):
        _save_json(p, {"bad": _Bad()})    # JSON 직렬화 불가 객체

    # 본 파일은 이전 완전본 그대로 (truncate 되지 않음)
    assert p.read_text(encoding="utf-8") == prev


def test_save_json_crash_between_tmp_and_replace_leaves_prev_intact(tmp_path):
    """tmp는 다 썼는데 os.replace 직전에 크래시한 시나리오 — 본 파일은 이전 완전본."""
    p = tmp_path / "ledger.json"
    _save_json(p, {"v": "prev"})
    prev = p.read_text(encoding="utf-8")

    # os.replace를 raise하도록 monkeypatch → 크래시 시뮬레이션
    import localapp.trader as t
    with patch.object(t.os, "replace", side_effect=RuntimeError("crash")):
        with pytest.raises(RuntimeError):
            _save_json(p, {"v": "new"})

    # 본 파일은 이전 완전본 (tmp만 남거나 정리되거나, 본 파일은 무손상)
    assert p.read_text(encoding="utf-8") == prev


# ── L-06 ─────────────────────────────────────────────────────────────────────

def test_kst_today_is_kst_date():
    """KST(UTC+09:00) 거래일을 반환. UTC와 9시간 어긋날 수 있음."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    expected = datetime.now(ZoneInfo("Asia/Seoul")).date()
    assert kst_today() == expected
    assert isinstance(kst_today(), date)
