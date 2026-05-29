# Trading Workbench P1+P2 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (또는 subagent-driven-development) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 자동매매 모듈의 불변식·상태머신을 문서화(P1)하고, 실제 `trader` 로직을 SimBroker로 오프라인 결정론적으로 구동해 불변식을 단언하는 최소 시뮬레이터(P2)를 만든다.

**Architecture:** sim은 production 코드의 복사본이 아니다 — `Trader(broker)` 생성자와 `intraday_loop._on_exec_event(trader, broker, evt)`라는 **기존 주입 seam**에 `SimBroker`를 끼워 실제 cycle/체결/settlement 로직을 그대로 구동한다. sim 코드는 `platform/local/sim/`(번들 밖), 시나리오는 `platform/local/tests/scenarios/`. import 가드 테스트로 `localapp`이 sim/tests를 import하지 않음을 강제한다.

**Tech Stack:** Python 3.x, pytest, 기존 `localapp.trader`/`intraday_loop`/`broker.Broker` Protocol.

**Spec:** [docs/specs/2026-05-30-trading-workbench-design.md](../specs/2026-05-30-trading-workbench-design.md)

**YAGNI 편차(spec 대비, 4원칙 적용)**:
- `SimClock` 클래스는 P2에서 만들지 않는다 — 최소 시나리오는 `kst_today` 고정 주입으로 충분. 시간 진행(DST·catch-up 타이밍) 시나리오가 필요한 P4로 연기.
- composition-root(`make_broker` injectable) 리팩토링도 P4로 연기 — P2는 `Trader(SimBroker)` + `_on_exec_event`를 직접 구동하므로 runner/scheduler wrapper를 거칠 필요 없음.

---

## File Structure

| 파일 | 책임 |
|---|---|
| `platform/docs/INVARIANTS.md` (생성) | 머니패스 불변식 + 9축 택소노미(섹션). 단언 어휘의 단일 출처 |
| `platform/docs/ORDER_STATE_MACHINE.md` (생성) | 주문·포지션 상태/전이, 전이↔엣지케이스↔불변식 매핑 |
| `platform/local/sim/__init__.py` (생성) | sim 패키지 |
| `platform/local/sim/broker.py` (생성) | `SimBroker` — `Broker` Protocol 구현 + 발주 기록 + 체결이벤트/상태 스크립트 |
| `platform/local/sim/scenario.py` (생성) | (trader, broker)를 하루 흐름으로 구동하는 순수 함수들 |
| `platform/local/sim/invariants.py` (생성) | 실행 가능한 불변식 단언 함수 (INVARIANTS.md ID 참조) |
| `platform/local/tests/scenarios/__init__.py` (생성) | 시나리오 테스트 패키지 |
| `platform/local/tests/scenarios/test_krx_day_happy_path.py` (생성) | 첫 E2E: 매수 cycle→WS 체결→매도→settlement, 불변식 단언 |
| `platform/local/tests/test_sim_prod_boundary.py` (생성) | import 가드: `localapp`이 `sim`/`tests` import 안 함 |

---

## Task 1: INVARIANTS.md (불변식 + 9축 택소노미)

**Files:** Create `platform/docs/INVARIANTS.md`

- [ ] **Step 1: 문서 작성** — 다음 구조로. 각 불변식 = `ID · 진술 · 근거 · 현재 강제지점(file:line) · 수호 테스트`. 시드(축별 ≥1):

```
A1 시장·캘린더:  INV-TIME-1 거래일 판정=KST (trader.kst_today, L-06) [test_atomic_save_kst]
A2 주문 생애주기: INV-ORDER-1 intent journal 없는 발주 없음 (intents.begin, _submit_buy/sell L-01) [test_intents]
A3 체결 인지:     INV-FILL-1 각 체결은 정확히 1회 원장 반영 (_apply_fill 단일 writer + dedup L-09) [test_exec_notice_dedup]
                 INV-FILL-2 ODNO 비교는 canonical (canonical_odno, M2) [test_canonical_odno]
A4 재기동:        INV-ORDER-2 한 intent당 최대 1회 제출 (intents reconcile) [test_intents]
A5 동시성:        INV-CONC-1 ledger/pending 변경은 _CYCLE_LOCK 직렬화 (M3) [test_trader_concurrency]
A6 정합성:        INV-LEDGER-1 ledger qty>0 (0이하는 삭제); INV-LEDGER-2 평단=가중평균 (_apply_fill L-04/L-05) [test_oversell_clamp]
A7 리스크:        INV-KS-1 killswitch active→신규 매수 0; INV-CASH-1 매수합≤매수가능 (_cycle_body, killswitch Q5)
A8 외부 API:      INV-API-1 rate limit≤8/s (throttle); INV-API-2 EGW00201 재시도 (_get/_post_retry)
A9 영속·보안:     INV-PERSIST-1 민감 저장=원자+ACL (state_store, M0) [test_state_store]; INV-SEC-1 자격증명·계좌·원시주문 서버 미유출
```
각 항목에 1줄 진술 + 근거 + file:line + 테스트명. 미강제(갭) 항목은 `⚠️ 강제 안 됨 — 시나리오 필요`로 표기.

- [ ] **Step 2: 자가검토** — 9축 모두 ≥1 불변식 존재 확인. TBD/모호 표현 제거.
- [ ] **Step 3: Commit**
```bash
git add docs/INVARIANTS.md
git commit -m "docs: 자동매매 머니패스 불변식 + 9축 택소노미 (Workbench P1)"
```

## Task 2: ORDER_STATE_MACHINE.md (상태머신 모델)

**Files:** Create `platform/docs/ORDER_STATE_MACHINE.md`

- [ ] **Step 1: 문서 작성** — 다음을 포함:
  - 주문 상태: `NEW → SUBMITTED → {PENDING → PARTIAL* → FILLED | CANCELLED | REJECTED}`
  - 예약(US): `RESERVED → (개장 자동전송) → SUBMITTED → …`
  - 포지션: `FLAT → OPEN → (추가매수) OPEN' → CLOSING → FLAT`
  - 전이 표: 각 전이 = 트리거(코드 경로 file:func) · 보존 불변식(INV-ID) · 엣지케이스(축).
    예: `SUBMITTED→PENDING` = `_after_submit`가 self.pending 등록(INV-CONC-1); `PENDING→FILLED` =
    `_on_exec_event`/`_resolve_pending`→`_apply_fill`(INV-FILL-1/2, INV-LEDGER-1).
- [ ] **Step 2: 자가검토** — 모든 전이가 INVARIANTS.md의 실제 ID를 참조하는지 확인.
- [ ] **Step 3: Commit**
```bash
git add docs/ORDER_STATE_MACHINE.md
git commit -m "docs: 주문·포지션 상태머신 모델 (Workbench P1)"
```

## Task 3: SimBroker (Broker Protocol 구현)

**Files:** Create `platform/local/sim/__init__.py` (빈 파일), `platform/local/sim/broker.py`

- [ ] **Step 1: 실패 테스트 작성** — `platform/local/tests/scenarios/test_krx_day_happy_path.py`에 먼저 SimBroker 기본 동작 테스트:

```python
import sys
from pathlib import Path
_LOCAL = Path(__file__).resolve().parent.parent.parent
if str(_LOCAL) not in sys.path:
    sys.path.insert(0, str(_LOCAL))

from sim.broker import SimBroker


def test_simbroker_records_and_pads_odno():
    b = SimBroker(balance={"cash": 10_000_000, "total_eval": 10_000_000,
                            "foreign_eval_krw": 0, "cash_usd": 0, "fx_usdkrw": 0})
    r = b.buy_limit("005930", 10, 70000)
    assert r["success"] is True
    assert r["order_no"] == "0000000001"          # zero-padded-10 (KIS 형식)
    assert b.submitted[0]["symbol"] == "005930"
    st = b.order_status(r["order_no"], "005930")
    assert st["status"] == "submitted"
```

- [ ] **Step 2: 실패 확인** — Run: `cd platform/local && python -m pytest tests/scenarios/test_krx_day_happy_path.py::test_simbroker_records_and_pads_odno -v` → Expected: FAIL (`ModuleNotFoundError: sim`)

- [ ] **Step 3: SimBroker 구현** — `platform/local/sim/broker.py`:

```python
"""SimBroker — Broker Protocol의 결정론적 구현(오프라인 테스트용).

발주를 기록하고 KIS 형식(zero-padded-10) ODNO를 발급한다. 체결은 자동으로
일어나지 않으며, 시나리오가 exec_event()(WS 통보 주입용) 또는 mark_filled()
(REST 조회 응답용)로 명시 구동한다 — 결정론 보장. 실제 KIS 응답 형식이 확정되면
fixtures/로 교체(record-replay, P3).
"""
from __future__ import annotations


class SimBroker:
    def __init__(self, balance: dict | None = None, prices: dict | None = None):
        self._balance = balance or {"cash": 10_000_000, "total_eval": 10_000_000,
                                     "foreign_eval_krw": 0, "cash_usd": 0, "fx_usdkrw": 0}
        self._prices = dict(prices or {})
        self._positions: list[dict] = []
        self.submitted: list[dict] = []
        self._statuses: dict[str, dict] = {}
        self._n = 0

    def _order(self, side: str, symbol: str, qty: int, limit: float = 0) -> dict:
        self._n += 1
        odno = f"{self._n:010d}"
        self.submitted.append({"side": side, "symbol": symbol, "qty": qty,
                                "limit": limit, "order_no": odno})
        self._statuses[odno] = {"order_no": odno, "status": "submitted",
                                 "filled_qty": 0, "remain_qty": qty, "fill_price": 0.0}
        return {"success": True, "order_no": odno, "filled_qty": 0, "price": 0}

    # ── Broker Protocol ──
    def account_snapshot(self) -> dict:
        return {"balance": dict(self._balance), "positions": list(self._positions)}

    def price(self, symbol: str) -> float:
        return float(self._prices.get(symbol, 0.0))

    def today_open(self, symbol: str) -> float:
        return float(self._prices.get(symbol, 0.0))

    def buy(self, symbol, qty): return self._order("buy", symbol, qty)
    def sell(self, symbol, qty): return self._order("sell", symbol, qty)
    def buy_limit(self, symbol, qty, limit_price): return self._order("buy", symbol, qty, limit_price)
    def sell_limit(self, symbol, qty, limit_price): return self._order("sell", symbol, qty, limit_price)
    def buy_resv_limit(self, symbol, qty, limit_price): return self._order("buy", symbol, qty, limit_price)
    def sell_resv_moo(self, symbol, qty): return self._order("sell", symbol, qty)

    def cancel(self, order_no, symbol, qty) -> dict:
        if order_no in self._statuses:
            self._statuses[order_no]["status"] = "cancelled"
        return {"success": True, "order_no": order_no}

    def order_status(self, order_no, symbol=None) -> dict:
        return self._statuses.get(order_no, {"order_no": order_no, "status": "unknown",
                                              "filled_qty": 0, "remain_qty": 0, "fill_price": 0.0})

    def pending_orders(self) -> list[dict]:
        return [dict(s) for s in self._statuses.values()
                if s["status"] in ("submitted", "partial")]

    # ── 시나리오 제어 ──
    def exec_event(self, order_no: str, qty: int, price: float,
                    hour: str = "100000") -> dict:
        """_on_exec_event에 주입할 H0STCNI0 체결 통보 이벤트 구성."""
        o = next(s for s in self.submitted if s["order_no"] == order_no)
        return {"CNTG_YN": "2", "ODER_NO": order_no, "STCK_SHRN_ISCD": o["symbol"],
                "CNTG_QTY": str(qty), "CNTG_UNPR": str(price),
                "STCK_CNTG_HOUR": hour, "RFUS_YN": ""}

    def mark_filled(self, order_no: str, qty: int, price: float) -> None:
        """REST 조회(order_status)가 filled를 반환하도록 상태 갱신."""
        s = self._statuses[order_no]
        s.update(status="filled", filled_qty=qty, remain_qty=0, fill_price=price)
```

- [ ] **Step 4: 통과 확인** — Run: `cd platform/local && python -m pytest tests/scenarios/test_krx_day_happy_path.py::test_simbroker_records_and_pads_odno -v` → Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add local/sim/__init__.py local/sim/broker.py local/tests/scenarios/test_krx_day_happy_path.py
git commit -m "feat(sim): SimBroker — Broker Protocol 결정론적 구현 (Workbench P2)"
```

## Task 4: invariants.py (실행 가능한 불변식 단언)

**Files:** Create `platform/local/sim/invariants.py`

- [ ] **Step 1: 실패 테스트 작성** — 같은 테스트 파일에 추가:

```python
from sim.invariants import check_ledger_nonneg, check_pending_has_order_no


def test_invariants_catch_negative_qty():
    import pytest

    class _T:
        ledger = {"s1": {"qty": -1}}
        pending = {}
    with pytest.raises(AssertionError, match="INV-LEDGER-1"):
        check_ledger_nonneg(_T())
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/scenarios/test_krx_day_happy_path.py::test_invariants_catch_negative_qty -v` → Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: 구현** — `platform/local/sim/invariants.py`:

```python
"""실행 가능한 머니패스 불변식 단언. ID는 docs/INVARIANTS.md와 1:1 대응."""
from __future__ import annotations


def check_ledger_nonneg(trader) -> None:
    """INV-LEDGER-1: ledger에 남은 포지션의 qty는 양수다(0 이하는 삭제됨)."""
    for sid, lg in trader.ledger.items():
        assert lg["qty"] > 0, f"INV-LEDGER-1 위반: {sid} qty={lg['qty']}"


def check_pending_has_order_no(trader) -> None:
    """INV-CONC-1 보조: 모든 pending 엔트리는 raw order_no를 보유(KIS 라운드트립)."""
    for key, p in trader.pending.items():
        assert p.get("order_no"), f"pending[{key}]에 order_no 없음"


def check_all(trader) -> None:
    check_ledger_nonneg(trader)
    check_pending_has_order_no(trader)
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/scenarios/test_krx_day_happy_path.py::test_invariants_catch_negative_qty -v` → Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add local/sim/invariants.py local/tests/scenarios/test_krx_day_happy_path.py
git commit -m "feat(sim): 실행 가능한 불변식 단언 (Workbench P2)"
```

## Task 5: scenario.py (하루 흐름 구동 — 순수 함수)

**Files:** Create `platform/local/sim/scenario.py`

- [ ] **Step 1: 구현** — `platform/local/sim/scenario.py`. pytest 의존 없음. (이 task는 helper라 테스트는 Task 6의 E2E가 겸한다.)

```python
"""시나리오 구동 helper — 주어진 (trader, SimBroker)를 하루 흐름으로 움직인다.

production 코드를 그대로 호출한다: _on_exec_event(실 WS 경로), trader._resolve_pending /
reconcile_with_kis(실 settlement 경로). sim은 seam에만 끼며 로직을 재구현하지 않는다.
"""
from __future__ import annotations

from localapp import intraday_loop


def inject_ws_fill(trader, broker, order_no: str, qty: int, price: float,
                    hour: str = "100000") -> None:
    """체결 통보 WS 경로로 체결을 반영(실 _on_exec_event 구동)."""
    evt = broker.exec_event(order_no, qty, price, hour)
    intraday_loop._on_exec_event(trader, broker, evt)


def run_settlement(trader, broker, today_iso: str) -> None:
    """장 마감 후 정산 경로(실 trader 메서드 구동)."""
    decisions: list[dict] = []
    trader._resolve_pending(decisions)
    trader.reconcile_with_kis(today_iso=today_iso)
```

- [ ] **Step 2: import sanity** — Run: `cd platform/local && python -c "import sim.scenario"` → Expected: 출력 없음(성공)
- [ ] **Step 3: Commit**
```bash
git add local/sim/scenario.py
git commit -m "feat(sim): 시나리오 구동 helper (실 _on_exec_event/settlement seam) (Workbench P2)"
```

## Task 6: KRX 하루 E2E 시나리오 (매수→체결→매도→정산)

**Files:** Modify `platform/local/tests/scenarios/test_krx_day_happy_path.py` (+ `tests/scenarios/__init__.py` 생성)

- [ ] **Step 1: E2E 실패 테스트 작성** — 추가:

```python
import pytest
from sim.broker import SimBroker
from sim import scenario, invariants


@pytest.fixture
def isolated_trader(tmp_path, monkeypatch):
    """trader 영속 경로를 tmp로 격리 + KST 날짜 고정 + 서버 push 차단."""
    from localapp import trader as tr
    from localapp import intraday_loop, killswitch
    for name in ("LEDGER_PATH", "EQUITY_PATH", "PENDING_ORDERS_PATH",
                 "REBALANCE_PATH", "TRADES_PATH"):
        monkeypatch.setattr(tr, name, tmp_path / f"{name}.json")
    monkeypatch.setattr(killswitch, "KILLSWITCH_PATH", tmp_path / "ks.json")
    monkeypatch.setattr(intraday_loop, "push_snapshot", lambda *a, **k: None)
    monkeypatch.setattr(tr, "kst_today", lambda: __import__("datetime").date(2026, 6, 1))

    broker = SimBroker()
    t = tr.Trader(broker)
    return t, broker


def test_krx_day_buy_fill_sell_settlement(isolated_trader):
    t, broker = isolated_trader
    # 1) 매수 발주(실 _submit_buy 경로 대신 직접 발주 → pending 등록까지 실 _after_submit 사용)
    r = broker.buy_limit("005930", 10, 70000)
    t._after_submit(r, "strat1", "삼성", {}, "005930", "buy", 10, 70000, 70000,
                    {"use_limit": True, "buy_tolerance_pct": 1.0}, [], reason="매수신호")
    assert "0000000001" in t.pending or any(
        p["order_no"] == "0000000001" for p in t.pending.values())
    invariants.check_all(t)

    # 2) WS 체결 통보 → 원장 반영(실 _on_exec_event)
    scenario.inject_ws_fill(t, broker, "0000000001", 10, 70000.0)
    sid = "strat1"
    assert t.ledger[sid]["qty"] == 10
    assert not t.pending          # 전량 체결 → pending 회수
    invariants.check_all(t)

    # 3) 중복 체결 통보 → dedup(INV-FILL-1): qty 불변
    scenario.inject_ws_fill(t, broker, "0000000001", 10, 70000.0)
    assert t.ledger[sid]["qty"] == 10, "INV-FILL-1: 중복 체결이 이중 반영됨"

    # 4) 매도 발주 + 체결 → 포지션 청산
    r2 = broker.sell_limit("005930", 10, 71000)
    t._after_submit(r2, sid, "삼성", {}, "005930", "sell", 10, 71000, 71000,
                    {"use_limit": True, "sell_tolerance_pct": 1.0}, [], reason="청산")
    scenario.inject_ws_fill(t, broker, r2["order_no"], 10, 71000.0)
    assert sid not in t.ledger    # FLAT
    invariants.check_all(t)

    # 5) settlement — 미체결 정리 + reconcile(외부 매도 없음 → drift 없음)
    scenario.run_settlement(t, broker, "2026-06-01")
    invariants.check_all(t)
```

- [ ] **Step 2: `tests/scenarios/__init__.py` 생성** (빈 파일).
- [ ] **Step 3: 실행** — Run: `cd platform/local && python -m pytest tests/scenarios/test_krx_day_happy_path.py -v`
  Expected: 전부 PASS. 실패 시 실제 trader API(`_after_submit` 시그니처, `_apply_fill` sid 매핑)와 어긋난 부분을 진단해 테스트(또는 SimBroker)를 실제 동작에 맞춘다. **production 코드는 이 단계에서 바꾸지 않는다**(행동 보존 검증이 목적).
- [ ] **Step 4: 전체 회귀** — Run: `cd platform/local && timeout 240 python -m pytest tests/ -q` → Expected: 기존 122 + 신규 전부 PASS, hang 없음.
- [ ] **Step 5: Commit**
```bash
git add local/tests/scenarios/__init__.py local/tests/scenarios/test_krx_day_happy_path.py
git commit -m "feat(sim): KRX 하루 E2E 시나리오 — 매수→체결→dedup→매도→정산 불변식 단언 (Workbench P2)"
```

## Task 7: import 가드 (sim/prod 경계 강제)

**Files:** Create `platform/local/tests/test_sim_prod_boundary.py`

- [ ] **Step 1: 테스트 작성**:

```python
"""sim/prod 경계 — localapp(프로덕션)은 sim/tests를 절대 import하지 않는다.
배포 번들(localapp)에 테스트/시뮬 코드가 새어들면 안 된다(spec §5)."""
import ast
import sys
from pathlib import Path

_LOCALAPP = Path(__file__).resolve().parent.parent / "localapp"


def test_localapp_never_imports_sim_or_tests():
    offenders = []
    for py in _LOCALAPP.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                mods = [node.module or ""]
            for m in mods:
                if m.split(".")[0] in ("sim", "tests"):
                    offenders.append(f"{py.name}: import {m}")
    assert not offenders, f"프로덕션이 sim/tests import: {offenders}"
```

- [ ] **Step 2: 실행** — Run: `cd platform/local && python -m pytest tests/test_sim_prod_boundary.py -v` → Expected: PASS (현재 localapp은 sim/tests를 import하지 않음).
- [ ] **Step 3: Commit**
```bash
git add local/tests/test_sim_prod_boundary.py
git commit -m "test(sim): sim/prod import 경계 가드 (Workbench P2)"
```

---

## Self-Review

**1. Spec coverage:**
- spec §4① INVARIANTS → Task 1 ✓ / §4② 상태머신 → Task 2 ✓ / §4③ 시뮬레이터(SimBroker·scenario) → Task 3·5 ✓ / §4④ 테스트 아키텍처(시나리오) → Task 6 ✓ / §5 경계 강제(import 가드) → Task 7 ✓.
- §4③ `SimClock`·fixtures(record-replay)·§5 composition-root = **P3/P4로 의도적 연기**(YAGNI, 위 편차 명시). §9 incident 재현·§4④ 커버리지 맵 = P4.
- 갭 없음(이 plan 범위 P1+P2 한정).

**2. Placeholder scan:** 코드 step은 전부 실제 코드 포함. 문서 task(1·2)는 구조+시드 불변식 목록 제공(프로즈는 실행 시 작성 — 문서 특성상 backbone이 곧 내용). TBD/TODO 없음.

**3. Type consistency:** `SimBroker.order_status(order_no, symbol=None)` — 실제 `trader`가 `broker.order_status(order_no, p.get("symbol"))`로 호출하므로 2-인자 시그니처 일치. `exec_event`/`mark_filled`/`submitted`/`_statuses` 명칭 Task 3 정의 ↔ Task 5·6 사용 일치. `check_ledger_nonneg`/`check_pending_has_order_no`/`check_all` Task 4 정의 ↔ Task 6 사용 일치.

**리스크 노트:** Task 6 E2E는 실제 `_after_submit`/`_apply_fill` 동작에 SimBroker/테스트를 맞춰야 한다(production 불변). 어긋나면 그 자체가 실제 결함 신호이므로 진단 후 처리.
