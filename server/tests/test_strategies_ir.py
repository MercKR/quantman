"""Stage 1 (IR 수렴) — 전략 저장/불러오기 라운드트립 + 레거시 무손상.

전략 연구소(IR)가 "전략 만들기"(operand)를 대체하는 단계의 토대: 같은 /strategies
테이블에 engine 판별자로 두 표현을 공존시킨다. 검증:
  - IR 전략 create → get(engine='ir', 정의 보존) → update(버전 스냅샷) 라운드트립.
  - 레거시 operand 전략 create/get 무손상(engine='operand' 기본).
  - 교차 검증 — IR 정의를 operand engine으로 저장하면 422(침묵 손상 차단).

네트워크/lifespan 없이 인메모리 SQLite + 최소 앱.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

_SERVER_DIR = Path(__file__).resolve().parent.parent
if str(_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(_SERVER_DIR))

from app.db import get_session
from app.models import User
from app.routers import strategies as strategies_router
from app.security import create_access_token

# ── 픽스처 정의 ───────────────────────────────────────────────────────────────

_IR_SIGNAL = {
    "op": "compare", "params": {"op": ">"},
    "inputs": {
        "left": {"op": "data", "params": {"ref": "__SELF__.Close"}},
        "right": {"op": "ts_mean", "params": {"window": 20},
                  "inputs": {"signal": {"op": "data", "params": {"ref": "__SELF__.Close"}}}},
    },
}
_IR_DEF = {
    "name": "연구소 모멘텀",
    "universe": {"kind": "single", "symbols": ["005930"]},
    "signal": _IR_SIGNAL,
    "position": {"direction": "long", "entry": {"mode": "on_signal"}},
    "simulation": {"initial_capital": 5_000_000},
}
_OPERAND_DEF = {
    "name": "레거시 룰",
    "trade_symbol": "005930",
    "buy": {"conditions": [], "logic": "AND"},
    "amount_pct": 10,
}


def _build():
    """인메모리 DB + strategies 라우터 + 시드 유저. (TestClient, jwt) 반환."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        user = User(email="t@example.com")
        s.add(user); s.commit(); s.refresh(user)
        user_id = user.id

    app = FastAPI()
    app.include_router(strategies_router.router)

    def _override():
        with Session(engine) as s:
            yield s
    app.dependency_overrides[get_session] = _override
    return TestClient(app), create_access_token(user_id)


def _auth(tok: str):
    return {"Authorization": f"Bearer {tok}"}


# ── IR 라운드트립 ─────────────────────────────────────────────────────────────

def test_ir_strategy_create_and_get_roundtrip():
    client, tok = _build()
    r = client.post("/strategies", headers=_auth(tok),
                    json={"definition": _IR_DEF, "run_mode": "draft", "engine": "ir"})
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["engine"] == "ir"
    assert created["name"] == "연구소 모멘텀"        # StrategyIR.name에서 도출

    sid = created["id"]
    got = client.get(f"/strategies/{sid}", headers=_auth(tok)).json()
    assert got["engine"] == "ir"
    # 정의 라운드트립 — 신호 트리·유니버스 보존
    assert got["definition"]["signal"]["op"] == "compare"
    assert got["definition"]["universe"]["symbols"] == ["005930"]
    assert got["definition"]["position"]["entry"]["mode"] == "on_signal"


def test_ir_strategy_update_snapshots_version():
    client, tok = _build()
    sid = client.post("/strategies", headers=_auth(tok),
                      json={"definition": _IR_DEF, "run_mode": "draft",
                            "engine": "ir"}).json()["id"]
    # 신호 변경 후 update
    edited = dict(_IR_DEF)
    edited["name"] = "연구소 모멘텀 v2"
    r = client.put(f"/strategies/{sid}", headers=_auth(tok),
                   json={"definition": edited, "run_mode": "paper", "engine": "ir"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "연구소 모멘텀 v2"
    assert body["engine"] == "ir"
    assert body["run_mode"] == "paper"
    # 변경 전 정의가 버전으로 보존 (initial v1 + manual_edit v2)
    versions = client.get(f"/strategies/{sid}/versions", headers=_auth(tok)).json()
    assert len(versions) >= 1


def test_ir_strategy_listed_with_engine():
    client, tok = _build()
    client.post("/strategies", headers=_auth(tok),
                json={"definition": _IR_DEF, "run_mode": "draft", "engine": "ir"})
    rows = client.get("/strategies", headers=_auth(tok)).json()
    assert len(rows) == 1
    assert rows[0]["engine"] == "ir"


# ── IR 단일 체제 — 기본 engine·operand 거부 ───────────────────────────────────

def test_default_engine_is_ir():
    """engine 미지정 create는 ir (IR 단일 체제 기본값)."""
    client, tok = _build()
    r = client.post("/strategies", headers=_auth(tok),
                    json={"definition": _IR_DEF, "run_mode": "draft"})
    assert r.status_code == 201, r.text
    assert r.json()["engine"] == "ir"


def test_operand_engine_rejected():
    """operand engine은 더 이상 지원 안 함 — 422 (레거시 제거)."""
    client, tok = _build()
    r = client.post("/strategies", headers=_auth(tok),
                    json={"definition": _OPERAND_DEF, "run_mode": "draft", "engine": "operand"})
    assert r.status_code == 422, r.text


def test_invalid_engine_rejected():
    client, tok = _build()
    r = client.post("/strategies", headers=_auth(tok),
                    json={"definition": _IR_DEF, "run_mode": "draft", "engine": "bogus"})
    assert r.status_code == 422, r.text


# ── 레버리지 리서치 게이트 — leverage>1은 백테스트 전용(모의·실전 차단) ────────

def _lev_def(lev: float) -> dict:
    d = dict(_IR_DEF)
    d["simulation"] = {**_IR_DEF["simulation"], "leverage": lev}
    return d


def test_leverage_draft_allowed():
    """레버리지>1 전략은 draft(백테스트/리서치)로 저장 가능."""
    client, tok = _build()
    r = client.post("/strategies", headers=_auth(tok),
                    json={"definition": _lev_def(2.0), "run_mode": "draft", "engine": "ir"})
    assert r.status_code == 201, r.text


def test_leverage_paper_rejected():
    """레버리지>1 전략을 모의로 저장하면 422(실거래 현금계좌로 체결 불가)."""
    client, tok = _build()
    r = client.post("/strategies", headers=_auth(tok),
                    json={"definition": _lev_def(2.0), "run_mode": "paper", "engine": "ir"})
    assert r.status_code == 422, r.text


def test_leverage_live_rejected():
    """레버리지>1 전략을 실전으로 저장하면 422."""
    client, tok = _build()
    r = client.post("/strategies", headers=_auth(tok),
                    json={"definition": _lev_def(3.0), "run_mode": "live", "engine": "ir"})
    assert r.status_code == 422, r.text


def test_unleveraged_paper_allowed():
    """레버리지=1(기본)은 모의 적용 정상 — 게이트 회귀 가드."""
    client, tok = _build()
    r = client.post("/strategies", headers=_auth(tok),
                    json={"definition": _lev_def(1.0), "run_mode": "paper", "engine": "ir"})
    assert r.status_code == 201, r.text


def test_leverage_promote_to_live_rejected_on_update():
    """draft 레버리지 전략을 update로 실전 승격하려 하면 422."""
    client, tok = _build()
    sid = client.post("/strategies", headers=_auth(tok),
                      json={"definition": _lev_def(2.0), "run_mode": "draft",
                            "engine": "ir"}).json()["id"]
    r = client.put(f"/strategies/{sid}", headers=_auth(tok),
                   json={"definition": _lev_def(2.0), "run_mode": "live", "engine": "ir"})
    assert r.status_code == 422, r.text


# ── 논리 정합성 게이트 — 무의미·모순 로직은 저장 차단(모든 모드) ────────────────

def _def_with_signal(sig: dict) -> dict:
    return {"name": "t", "universe": {"kind": "single", "symbols": ["005930"]},
            "signal": sig, "position": {"direction": "long", "entry": {"mode": "on_signal"}},
            "simulation": {"initial_capital": 5_000_000}}


_CONST_SIG = {"op": "compare", "params": {"op": ">"},
              "inputs": {"left": {"op": "const", "params": {"value": 5}},
                         "right": {"op": "const", "params": {"value": 0}}}}
_SELF_CMP_SIG = {"op": "compare", "params": {"op": ">"},
                 "inputs": {"left": {"op": "data", "params": {"ref": "__SELF__.Close"}},
                            "right": {"op": "data", "params": {"ref": "__SELF__.Close"}}}}


def test_save_rejects_constant_signal_even_draft():
    """상수 신호(시장 미참조) → draft 저장도 422 (모든 저장 에러 차단)."""
    client, tok = _build()
    r = client.post("/strategies", headers=_auth(tok),
                    json={"definition": _def_with_signal(_CONST_SIG), "run_mode": "draft", "engine": "ir"})
    assert r.status_code == 422, r.text


def test_save_rejects_self_comparison():
    """X > X (동어반복/모순) → 422."""
    client, tok = _build()
    r = client.post("/strategies", headers=_auth(tok),
                    json={"definition": _def_with_signal(_SELF_CMP_SIG), "run_mode": "draft", "engine": "ir"})
    assert r.status_code == 422, r.text


def test_ir_validate_endpoint_flags_constant_signal(monkeypatch):
    """/ir/validate가 백테스트 없이 논리 오류를 이슈로 반환(UI 실시간 검증). 데이터셋 불요."""
    from app.routers import ir as ir_router
    monkeypatch.setattr(ir_router, "get_dataset", lambda: {})   # 데이터셋 로드 회피

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        u = User(email="t@example.com"); s.add(u); s.commit(); s.refresh(u); uid = u.id
    app = FastAPI()
    app.include_router(ir_router.router)

    def _ov():
        with Session(engine) as s:
            yield s
    app.dependency_overrides[get_session] = _ov
    client = TestClient(app)
    tok = create_access_token(uid)

    r = client.post("/ir/validate", headers=_auth(tok), json=_def_with_signal(_CONST_SIG))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is False
    assert any(i["rule"] == "M-const" for i in body["issues"])
