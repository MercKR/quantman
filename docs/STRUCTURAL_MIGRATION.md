# 구조 재설계 마이그레이션 (M0~M4) — 진행·검증 로그

산발적 결함을 단건 임기응변이 아니라 구조·workflow 근본 결함으로 묶어 재설계하는
작업. 단계는 blast radius 순(M0=가장 안전 → M2=머니패스). 이 문서는 **컴팩션으로
대화가 날아가도 살아남도록** 계획·진행·검증사항을 영속한다.

> 검증 환경 제약(2026-05-30 토): 장 마감 + live 환경 부재로 실거래(VTS) 검증 불가.
> 단위테스트는 가능. "테스트해야 할 사항"은 아래 **검증 로그**에 단계별로 누적하고,
> 개발은 계속 진행한다.

---

## 진행 현황

| 단계 | 축(결함) | 핵심 추상화 | 상태 | 검증 |
|---|---|---|---|---|
| **M0** | 민감 상태 저장 분산(ACL/원자성 누락) | StateStore (`state_store.py`) | ✅ 완료 | 단위 9 + 전체 회귀 ✅ |
| **M1** | 거래소 코드 맵 4벌 분산 | Market 레지스트리 (`_OVERSEAS_EXCD` 단일출처) | ✅ 완료 | 단위 3 ✅ |
| **M2** | 체결 인지 3경로 ODNO 정규화 불일치 | `canonical_odno()` 단일 정규화 | ✅ 코드+단위 완료 / ⏳ **live VTS 게이트** | 단위 7 ✅ · live 대기 |
| **M3** | 실행 컨텍스트 — 크로스스레드 공유변경(ledger/pending race) | 단일 RLock 직렬화 + ks hook defer | ✅ 코드+단위 완료 / ⏳ **live 동시부하 게이트** | 단위 5 + 회귀 122 ✅ · 실부하 대기 |
| **M4** | universe(매수후보·보유종목) 출처 분산 | 단일 출처 | 🔲 대기 | — |

> 참고: M0~M4 외 축(스레드 안전 등)의 원래 번호 정의는 컴팩션으로 유실. 위 표는
> task 목록 + 코드 실측으로 재구성한 것. 새로 발견되는 결함은 여기 추가한다.

---

## Trading Workbench 진행 (작업환경 — 엣지케이스 체계 검증)

설계: [specs/2026-05-30-trading-workbench-design.md](specs/2026-05-30-trading-workbench-design.md) ·
계획: [plans/2026-05-30-trading-workbench-p1-p2.md](plans/2026-05-30-trading-workbench-p1-p2.md)

| 단계 | 내용 | 상태 |
|---|---|---|
| **P1** | INVARIANTS.md + ORDER_STATE_MACHINE.md (불변식·상태머신·9축 택소노미) | ✅ 완료 |
| **P2** | SimBroker·invariants·scenario + KRX 하루 E2E + import 가드 | ✅ 완료 (125 passed) |
| **P4** | 9축 갭 시나리오 백필 + 과거 incident 재현 + 커버리지 맵 | 🔄 진행 중 (체결경로·원장정합성 채움, 131 passed) |
| **P5** | M4(universe 단일출처) 리팩토링을 환경 위에서 실행 | 🔲 대기 |
| **P3** | record-replay 픽스처(live 캡처) — **live 게이트 의존** | ⏳ 게이트 |

산출물: `docs/INVARIANTS.md`, `docs/ORDER_STATE_MACHINE.md`, `local/sim/{broker,invariants,scenario}.py`,
`local/tests/scenarios/`, `local/tests/test_sim_prod_boundary.py`.

**P4 범위(경량 계획 — 이미 spec이 설계, 확립된 패턴 적용)**: INVARIANTS.md 갭 채우기 —
INV-LEDGER-2(분할매수 평단), INV-RECON-1(외부매도 drift), INV-FILL-3(REST 폴링 경로),
그리고 self-verification(과거 incident: M3 race=test_trader_concurrency가 이미 재현,
INV-CAL-2 점검가드 회귀). 각 시나리오 TDD + 전체 회귀.

---

## 검증 로그 (live/실거래 필요 — 환경 복구 시 실행)

각 항목: **검증 계획 / 예상 결과 유형 / 결과 유형별 집중 진단 영역**.

### V-M2-1 · KIS 체결통보 WS의 ODER_NO 패딩 형태 실측
- **왜**: pending 키는 발주응답 ODNO(zero-padded-10)지만 WS 실시간 `ODER_NO`
  패딩은 KIS spec 미보장. canonical 매칭으로 양쪽 모두 안전하게 만들었으나(방어적),
  실제 형태를 한 번 확인해 가정을 사실로 확정한다.
- **검증 계획**: 국내 월 09:00 KST(또는 미국 월 22:30 KST) 개장 후 paper 매수 1건
  체결 → `~/.quant-platform/logs/localapp.log`에서 `[order-ws]` 라인의 `ODER_NO=...`
  값을 발주응답 ODNO(orders.jsonl)와 자릿수 비교.
- **예상 결과 유형 & 집중 진단**:
  - (a) **padded-10 동일** → 과거 정확일치도 우연히 맞았던 것. canonical은 무해·정상.
    추가 조치 없음.
  - (b) **unpadded(선행0 제거)** → 과거 정확일치였다면 **실시간 체결 전량 미인지**
    였음을 확정. canonical 수정이 실제 결함을 제거. → orders.jsonl·cycles.jsonl에서
    과거 "REST 폴링으로만 뒤늦게 인지된 체결" 흔적 점검(지연 패턴).
  - (c) **그 외 포맷(접두 문자 등)** → `canonical_odno` 규칙(lstrip("0"))이 불충분.
    즉시 GOTCHAS.md 기록 + 정규화 규칙 확장.

### V-M2-2 · 미국 예약주문 ODNO ≠ 개장 체결 주문번호 여부 (별도 결함 후보)
- **왜**: 미국 예약매수/매도(TTTT3014U/3016U)는 개장 전 *예약 ODNO*를 반환하지만,
  정규장 개시에 KIS가 자동 전송하는 *실제 주문*은 다른 번호일 수 있다. 다르면
  패딩이 아니라 **번호 자체가 바뀌는 것**이라 canonical로도 매칭 불가 — pending이
  영원히 미체결로 남고 체결을 못 잡는다. **M2 범위 밖의 독립 결함.**
- **검증 계획**: 미국 월 22:30 KST 개장 시 paper 예약매수 1건 → (1) 예약 응답 ODNO
  기록, (2) 개장 후 H0GSCNI0 WS `ODER_NO` 및 inquire-ccnl `odno` 기록, (3) 세 값
  canonical 비교.
- **예상 결과 유형 & 집중 진단**:
  - (a) **세 값 canonical 동일** → 예약 ODNO가 그대로 유지. 현 구조로 안전. 조치 없음.
  - (b) **예약 ODNO ≠ 체결 ODNO** → 실제 결함 확정. 집중 영역:
    `_after_submit`이 예약 ODNO로 pending 키를 잡으므로 개장 체결을 영원히 미인지.
    해결방향(설계 필요): 예약→실주문 매핑을 inquire-ccnl/예약주문조회로 재동기화하거나,
    예약 건은 pending 키를 종목+의도 기반으로 두고 ODNO 확정 시 갱신. **추측 구현
    금지 — 실측 후 별도 설계.**

### V-M3-1 · 실거래 동시부하에서 ledger/pending race·데드락 부재 확인
- **왜**: 단위테스트는 스레드 인터리빙을 결정적으로 강제하지만, 실제 체결 폭주 +
  60초 monitor cycle + 스케줄러 cycle 동시성은 환경에서만 재현된다. M3 RLock
  직렬화가 데드락(특히 _apply_fill→ks hook→cycle 경로)을 만들지 않는지 실측.
- **검증 계획**: 개장 중 다수 종목 보유 상태에서 (1) WS 체결 다발 + (2) ks 발동
  유도(또는 monitor 강제) 동시 발생시켜 `localapp.log`에 데드락(응답 정지)·
  ledger qty 이중가산/소실이 없는지 확인. cycles.jsonl·orders.jsonl·ledger.json
  교차 검증.
- **예상 결과 유형 & 집중 진단**:
  - (a) **정상 직렬화** → 로그상 cycle/체결이 순차 처리, ledger 합계 정합. 조치 없음.
  - (b) **응답 정지(데드락 의심)** → 어느 thread가 어느 락 대기인지 스택덤프.
    _CYCLE_LOCK 단일락이라 ordering 데드락은 불가하나, ks hook이 락 안에서
    호출되는 경로가 남았는지 점검(설계상 밖으로 뺐음).
  - (c) **ledger 불일치** → 락 미적용 변경 진입점 잔존. grep으로 self.ledger/
    self.pending 직접 변경 지점 재감사(reconcile·catchup 포함).

> 회귀 교훈(2026-05-30): Lock→RLock 전환 시 기존 "비재진입" 가정 테스트 2개가
> 실패하며 전역 락을 누수 → 합산 스위트 90초 hang. 개별 파일은 통과하나 합산만
> 멈추는 형태라, 락 타입/계약 변경 시 **전체 스위트 회귀 필수**. 테스트도 실패 시
> 전역 락을 누수하지 않게 try/finally로 균형 release.

> 진단 원칙(CLAUDE.md §7): 추측 금지. railway/vercel/gh/로컬 로그를 직접 CLI 조회.
> 권한·환경 없으면 사용자에게 스크린샷/로그 요청.

---

## M3 (축4) 코드 실측 분석 — 설계 확정 대기

`Trader`가 실행 컨텍스트를 **가변 인스턴스 속성**으로 사이클마다 set/reset:
`_in_cycle`, `_reserved_us`, `_us_bp_mode`, `_daily_loss_limit_pct`,
`_daily_turnover_limit_krw`, `_daily_trade_count_limit`, `_ks_trigger_hook`,
`_krx_status` (`_cycle_locked`/`_cycle_body`에서 set, try/finally reset).

**발견된 결함성 표면**
- (A) `is_resv = getattr(self,"_reserved_us",False) and _currency_of(symbol)=="USD"`
  가 `_submit_buy`(494)·`_submit_sell`(588)에 **동일 중복**. `getattr(...,default)`는
  `__init__`에서 항상 초기화되므로 **불필요한 방어 코드**(PR-1/PR-3 냄새).
- (B) `_currency_of(symbol)`가 단일 submit 안에서 ~9회 재계산(494·498·500·531·533·
  549·552·602·605). 같은 심볼이라 값 동일 — 1회 계산해 재사용 가능.
- (C) **크로스스레드 공유 변경(핵심·고위험)**: `_apply_fill`(단일 원장 writer)이
  사이클 thread + WS 체결 thread(`intraday_loop._on_exec_event`) 양쪽에서 호출되어
  `self.ledger`/`self.pending`을 **`_CYCLE_LOCK` 없이** 변경. 동시 사이클(ks 청산
  재진입 등)과 race 가능. `_in_cycle`/`_daily_loss_limit_pct`도 한 thread가 쓰고
  다른 thread가 읽음.

**판단**: (A)(B)는 명백·저위험 최소 정리(M1·M2에서 합의한 "최소 통합" 결). (C)는
머니패스 + 동시성이라 ExecutionContext object화만으로 안 풀리고(별 thread가 직전
사이클 한도를 읽어야 함) 락/스냅샷 설계가 필요 — 데드락 위험(_CYCLE_LOCK 기존 복잡)
때문에 **추측 구현 금지, 설계 합의 필요**. 원래 M3 상세설계는 컴팩션으로 유실.
