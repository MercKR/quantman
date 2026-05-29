# 주문·포지션 상태머신 (ORDER_STATE_MACHINE)

> 자동매매의 엣지케이스는 **special-case가 아니라 상태 전이**다. 이 문서는 주문/포지션의
> 상태·전이를 명시하고, 각 전이가 어떤 코드 경로로 일어나며 어떤 불변식
> ([INVARIANTS.md](INVARIANTS.md))을 보존해야 하는지 고정한다. 시뮬레이터의 시나리오는
> 이 전이들을 구동해 불변식을 단언한다.

---

## 1. 주문(Order) 상태

```
                       reject
        ┌─────────────────────────────────────► REJECTED
        │
NEW ──► SUBMITTED ──► PENDING ──┬──► PARTIAL ──┐
 │        (발주응답)   (미체결)   │     (부분)    │
 │                               │      ▲        │
 │                               │      └────────┘  (추가 부분체결)
 │                               │
 │                               ├──► FILLED      (전량 체결 → pending 회수)
 │                               └──► CANCELLED   (KIS 마감 자동취소 / killswitch / 외부취소)
 │
 └─(미국 정상 cycle)─► RESERVED ─(개장 자동전송)─► SUBMITTED ─► …
```

- **NEW**: 발주 직전. intent journal에 `submitting` 기록(INV-ORDER-1).
- **SUBMITTED**: KIS 발주응답 수신(ODNO 확보). 거부면 REJECTED.
- **PENDING**: `self.pending[canonical(ODNO)]`에 등록, 체결 대기.
- **PARTIAL**: 일부 체결, 잔량 계속 추적(`filled_so_far` 누적).
- **FILLED**: 전량 체결 → 원장 반영 + `del pending`.
- **CANCELLED**: KIS DAY 정책 마감 자동취소(Q7) / killswitch cancel / 외부 취소.
- **REJECTED**: 발주 거부(`success=False`).
- **RESERVED**: 미국 예약주문(개장 전 접수, 개장에 KIS 자동전송) — INV-ORDER-3.

## 2. 주문 전이 표

| 전이 | 트리거 (file:func) | 보존 불변식 | 엣지케이스 축 |
|---|---|---|---|
| NEW→SUBMITTED | `trader.py:_submit_buy`/`_submit_sell` → `broker.*` | INV-ORDER-1 (intent 먼저) | A2 |
| NEW→RESERVED | `_submit_buy`(`_is_reserved_us`)→`buy_resv_limit`/`sell_resv_moo` | INV-ORDER-3 | A2 |
| SUBMITTED→REJECTED | `trader.py:_after_submit` (`not success`) | — (로깅) | A2 |
| SUBMITTED→PENDING | `trader.py:_after_submit` (`self.pending[key]=p`) | INV-CONC-1 (락) | A2,A5 |
| SUBMITTED→FILLED | `_after_submit` 즉시체결 분기 → `_apply_fill` | INV-FILL-1, INV-LEDGER-1/2 | A3 |
| PENDING→FILLED (WS) | `intraday_loop.py:_on_exec_event` → `_apply_fill`; `del pending` | INV-FILL-1/2, INV-CONC-1 | A3,A5 |
| PENDING→FILLED (REST) | `trader.py:_resolve_pending` → `order_status` filled → `_apply_fill` | INV-FILL-2/3 | A3 |
| PENDING→PARTIAL | `_on_exec_event`/`_resolve_pending` (`filled_so_far += delta`) | INV-FILL-1 (dedup) | A3 |
| PARTIAL→FILLED | 동상, 잔량 0 도달 | INV-FILL-1, INV-LEDGER-1 | A3 |
| PENDING→CANCELLED (마감) | `_resolve_pending` (`status==cancelled`) | — | A2 |
| PENDING→CANCELLED (ks) | `trader.py:cancel_all_pending` | INV-KS-2, INV-CONC-1 | A7,A5 |
| RESERVED→SUBMITTED | 개장 KIS 자동전송 → `run_post_open_reconcile` 인지 | INV-FILL-2 (예약 ODNO≠실주문 가능성=⚠️ V-M2-2 probe) | A1,A3 |

## 3. 포지션(Position) 상태

```
FLAT ──(buy fill)──► OPEN ──(buy fill 추가)──► OPEN' ──(sell fill)──► CLOSING ──(qty→0)──► FLAT
                       ▲                                                  │
                       └──────────────────(부분 매도, qty>0)──────────────┘
```

| 전이 | 트리거 (file:func) | 보존 불변식 | 축 |
|---|---|---|---|
| FLAT→OPEN | `_apply_fill` 매수, 신규 sid | INV-LEDGER-1 | A6 |
| OPEN→OPEN' | `_apply_fill` 매수, 기존 sid (평단 갱신) | INV-LEDGER-2 | A6 |
| OPEN→CLOSING→FLAT | `_apply_fill` 매도 (`qty-=fqty`, `qty<=0 → del`) | INV-LEDGER-1 | A6 |
| OPEN→(외부매도)→FLAT | `reconcile_with_kis` (HTS/MTS 수동매도 차감) | INV-RECON-1, INV-CONC-1 | A6,A5 |

## 4. 동시성 관점 (A5)

세 스레드가 위 전이를 유발한다 — 모두 `_CYCLE_LOCK`(RLock) 직렬화 하에서만 원장/pending을
변경한다(INV-CONC-1):
- **스케줄러 스레드**: `run_cycle`/settlement → `trader.cycle`/`_resolve_pending`/`reconcile_with_kis`.
- **WS 체결 스레드**: `_on_exec_event` → `_apply_fill`.
- **60초 monitor 스레드**: killswitch 발동 → `_on_ks_trigger` → `cancel_all_pending`+`trader.cycle`.

ks hook(→cycle)은 `_apply_fill`의 락 임계구역 **밖**에서 호출해 재진입 데드락을 회피한다.

## 5. 시뮬레이터 매핑

`sim/scenario.py`가 위 전이를 실제 코드 경로로 구동한다:
- `inject_ws_fill` → `PENDING→FILLED (WS)` 전이(실 `_on_exec_event`).
- `run_settlement` → `PENDING→CANCELLED(마감)` + `reconcile` 전이.
- 매수/매도 발주는 `_after_submit`로 `SUBMITTED→PENDING`.
각 전이 후 `sim/invariants.py:check_all`로 보존 불변식을 단언한다.
