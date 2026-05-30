"""R5 회귀 — StateStore 단일 영속화 경로 (원자성 + owner-only ACL).

state_store는 민감 상태의 모든 저장 지점을 한 경로로 모은다. 두 직교 보장을
테스트한다:
  1) 원자성 — save_json은 tmp+os.replace, append_jsonl은 단일 라인 write.
  2) owner-only ACL — save_json은 매 저장, append_jsonl은 최초 생성 시 1회
     restrict_to_owner 호출. (이전엔 killswitch·ledger·intents·orders·token이
     ACL을 빠뜨려 같은 PC 타 사용자에게 노출 — R5가 이 결함 class를 제거.)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_LOCAL_DIR = Path(__file__).resolve().parent.parent
if str(_LOCAL_DIR) not in sys.path:
    sys.path.insert(0, str(_LOCAL_DIR))

from localapp import state_store


# ── save_json: 원자성 ──────────────────────────────────────────────────────────

def test_save_json_writes_and_leaves_no_tmp(tmp_path):
    p = tmp_path / "ledger.json"
    state_store.save_json(p, {"AAPL": {"qty": 10}})
    assert json.loads(p.read_text(encoding="utf-8")) == {"AAPL": {"qty": 10}}
    assert not (tmp_path / "ledger.json.tmp").exists()


def test_save_json_atomic_on_serialize_failure(tmp_path):
    """직렬화 실패 시 본 파일은 이전 완전본 그대로 (tmp에 먼저 쓰므로 무손상)."""
    p = tmp_path / "ledger.json"
    state_store.save_json(p, {"prev": 1})
    prev = p.read_text(encoding="utf-8")

    class _Bad:
        pass
    with pytest.raises(TypeError):
        state_store.save_json(p, {"bad": _Bad()})

    assert p.read_text(encoding="utf-8") == prev


def test_save_json_creates_parent_dir(tmp_path):
    p = tmp_path / "nested" / "deep" / "state.json"
    state_store.save_json(p, {"ok": True})
    assert p.exists()


# ── save_json: ACL ──────────────────────────────────────────────────────────────

def test_save_json_applies_owner_acl_every_write(tmp_path):
    p = tmp_path / "killswitch.json"
    with patch.object(state_store, "restrict_to_owner") as acl:
        state_store.save_json(p, {"active": True})
        state_store.save_json(p, {"active": False})
    assert acl.call_count == 2
    assert acl.call_args_list[0].args[0] == p


# ── append_jsonl: 동작 + 원자성 ──────────────────────────────────────────────────

def test_append_jsonl_appends_lines(tmp_path):
    p = tmp_path / "orders.jsonl"
    state_store.append_jsonl({"event": "submitted", "n": 1}, p)
    state_store.append_jsonl({"event": "filled", "n": 2}, p)
    lines = [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines()]
    assert lines == [{"event": "submitted", "n": 1}, {"event": "filled", "n": 2}]


def test_append_jsonl_creates_parent_dir(tmp_path):
    p = tmp_path / "nested" / "orders.jsonl"
    state_store.append_jsonl({"a": 1}, p)
    assert p.exists()


# ── append_jsonl: ACL 1회 ────────────────────────────────────────────────────────

def test_append_jsonl_applies_acl_only_on_create(tmp_path):
    """최초 생성 시 1회만 restrict_to_owner — 매 append마다 icacls 호출은 과한 비용."""
    p = tmp_path / "intents.jsonl"
    with patch.object(state_store, "restrict_to_owner") as acl:
        state_store.append_jsonl({"i": 1}, p)   # 생성 → ACL 1회
        state_store.append_jsonl({"i": 2}, p)   # 기존 파일 → ACL 호출 안 함
        state_store.append_jsonl({"i": 3}, p)
    assert acl.call_count == 1
    assert acl.call_args.args[0] == p


# ── append_jsonl: fsync 게이트 ────────────────────────────────────────────────────

def test_append_jsonl_fsync_true_calls_fsync(tmp_path):
    """fsync=True면 디스크 도달 보장 위해 os.fsync 호출 (L-01 intent 저널)."""
    p = tmp_path / "intents.jsonl"
    with patch.object(state_store.os, "fsync") as fs:
        state_store.append_jsonl({"i": 1}, p, fsync=True)
    assert fs.call_count == 1


def test_append_jsonl_default_no_fsync(tmp_path):
    """로그성 append(orders/cycles)는 fsync 불필요 — 기본값에서 호출 안 함."""
    p = tmp_path / "orders.jsonl"
    with patch.object(state_store.os, "fsync") as fs:
        state_store.append_jsonl({"i": 1}, p)
    assert fs.call_count == 0
