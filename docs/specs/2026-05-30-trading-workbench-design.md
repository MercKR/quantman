# 설계: Trading Workbench — 자동매매 작업환경

- 날짜: 2026-05-30
- 상태: 설계 승인됨 (brainstorming 완료) → 다음 단계 writing-plans
- 범위: **작업환경 구축만.** 트레이딩 코드 재작성은 이 spec에 없음 — 환경이 검증하는
  "첫 리팩토링"으로 M마이그레이션을 편입하고, 각 리팩토링 대상은 식별만 하고 각자
  별도 spec→plan으로 실행한다.

---

## 1. 문제 / 동기

자동매매의 **핵심 workflow는 단순**하다(정해진 시각에 깨어나 → 전략 평가 → 발주 →
체결 추적 → 원장 반영 → 서버 동기화). 어려움은 **수많은 엣지케이스를 일관·호환되게
처리**하는 데 있고, 지금은 그 처리가 `trader.py`(~1,300줄)에 happy-path와 **인라인으로
뒤섞여** 있다(주석 L-01·L-04·L-06·L-09·Q5·Q7·M2·M3·Phase40/48가 그 증거).

이번 세션에서 드러난 **메타-고통 4가지** (작업환경이 풀어야 할 진짜 대상):

1. **검증 불가** — 장 마감/paper 창 제한으로 live 검증이 안 돼 엣지케이스가 "추측"으로
   남는다 (M2·M3가 live 게이트 대기 중인 이유).
2. **계획 유실** — 컴팩션마다 마이그레이션 계획이 날아간다.
3. **흩어진 결함 class** — 같은 결함이 여러 곳(거래소맵 4벌·ODNO 3경로)에 → 단건 수정이
   다른 곳 누락을 유발.
4. **숨은 의존성** — 락 타입 변경이 기존 테스트 계약을 깨뜨림. 전체 회귀로만 발견.

## 2. 목표 / 비목표

**목표**: 모든 엣지케이스를 *반복 가능한·단언된 테스트*로 전환해, 자동매매 모듈을
**안전하게 보완·리팩토링**할 수 있는 실행 가능한 작업환경을 만든다. live 테스트는 작은
"API-사실 probe" 집합으로 축소한다.

**비목표 (YAGNI — 측정된 필요 없이는 안 만든다)**:
- 가짜 시계로 도는 full-scheduler process (seam-level 구동 + 표적 동시성 테스트로 충분).
- 시뮬레이터용 GUI.
- 실제 시세 동역학 시뮬레이션 (스크립트/녹화 데이터로 대체).
- 트레이딩 로직의 빅뱅 재작성.

## 3. 엣지케이스 택소노미 (MECE 9축)

작업환경의 모든 산출물(불변식·시나리오·테스트)이 이 9축에 매핑된다.

| # | 축 | 대표 사례(코드 근거) |
|---|---|---|
| A1 | 시장·캘린더 상태 | 휴장(L-03)·DST(US 22:30↔23:30)·KIS 점검창 과보수 가드 사고(2026-05-28)·거래정지(Phase48) |
| A2 | 주문 생애주기 | NEW→SUBMITTED→{PENDING→PARTIAL*→FILLED\|CANCELLED\|REJECTED}; 시장가/지정가/예약(US limit·MOO); DAY정책(Q7) |
| A3 | 체결 인지 | WS통보 vs REST폴링(Q3) vs 즉시체결; ODNO 정규화(M2); 중복 dedup(L-09) |
| A4 | 크래시·재기동·catch-up | 발주 멱등(L-01 fsync 저널); 놓친 cycle 보완(cycles.jsonl); PC off |
| A5 | 동시성 | 스케줄러·WS체결·60초 monitor 3스레드 상태변경(M3 RLock) |
| A6 | 계좌·원장 정합성 | KIS reconcile(Phase40)·외부 수동매매 차감·over-sell(L-04)·평단 갱신 |
| A7 | 리스크·안전 | killswitch Tier1/2(Q5)·drawdown·±30% 가격제한 사전클램프·turnover/count 한도 |
| A8 | 외부 API 한계 | rate limit(8/s)·EGW00201 재시도·토큰 24h·모의/실전 TR 분기 |
| A9 | 영속화·보안 | 원자성(L-02)·owner-only ACL(R5/M0)·민감정보 서버 미유출 경계 |

## 4. 4개 조립 산출물

세 모델은 경쟁이 아니라 한 환경으로 조립된다. 시뮬레이터가 키스톤(실행), 불변식이
언어(단언), 상태머신이 모델(구동 대상), 테스트 아키텍처가 조직(택소노미 매핑).

### ① INVARIANTS.md — 법칙 (선언적)
머니패스 불변식을 9축에 MECE 매핑. 각 항목 = `ID · 진술 · 근거 · 현재 강제지점(file:line) ·
수호 테스트`. 시드 목록:

- `INV-FILL-1` 각 체결은 정확히 1회만 원장 반영 (단일 writer `_apply_fill` + dedup L-09)
- `INV-ORDER-1` intent journal 없는 발주 없음 (L-01)
- `INV-ORDER-2` 한 intent당 최대 1회 제출 — 재기동 멱등
- `INV-CONC-1` ledger/pending 변경은 `_CYCLE_LOCK` 직렬화 하에서만 (M3)
- `INV-LEDGER-1` ledger qty < 0 불가 (over-sell clamp L-04)
- `INV-KS-1` killswitch active → 신규 매수 0
- `INV-CASH-1` 매수 발주 합 ≤ 매수가능금액
- `INV-TIME-1` 거래일 판정 = KST (L-06)
- `INV-PERSIST-1` 민감 저장 = 원자적 + owner-only ACL (M0)
- `INV-SEC-1` 자격증명·계좌번호·원시주문은 서버 payload·로그에 없음
- … (축당 1개 이상, P1에서 완성)

### ② 주문·포지션 상태머신 — 모델 (구조적)
- 주문: `NEW → SUBMITTED → {PENDING → PARTIAL* → FILLED | CANCELLED | REJECTED}`
- 예약(US): `RESERVED → (개장 자동전송) → SUBMITTED → …`
- 포지션: `FLAT → OPEN → (추가매수) OPEN' → CLOSING → FLAT`
- **엣지케이스 = 전이**로 매핑(special-case 아님). 각 전이는 보존해야 할 불변식을 명시.
- 코드화는 최소 — 문서 + 필요 시 작은 enum/guard. 무거운 FSM 프레임워크 금지(YAGNI).

### ③ 시뮬레이터 — 키스톤 (실행, record-replay) · `platform/local/sim/`
- `SimClock` — 가상 KST 시계 (08:55/09:00/15:35/US open 등으로 전진).
- `SimBroker(Broker)` — `Broker` 인터페이스 구현; 스크립트 또는 **리플레이** 응답 반환;
  가짜 WS 체결이벤트를 `on_exec` 콜백에 주입.
- `fixtures/` — 실 KIS VTS에서 **1회 캡처**한 골든 JSON(주문응답·daily-ccld·체결통보 프레임·
  에러코드). 각 파일은 출처 표기: `captured VTS YYYY-MM-DD` 또는 `ASSUMED — probe 대기`.
- `scenario` 러너 — 하루 조립: ledger/pending seed → 시계 전진 → cycle/WS/settlement 호출
  → 불변식 + 기대 종료상태 단언.
- **충실도 경계 명시**: 픽스처가 seed 안 한 응답은 우리 *가정*일 뿐 — 발명 금지.

### ④ 택소노미 연동 테스트 아키텍처
- `tests/scenarios/` — 9축 × 케이스별 시나리오, 불변식 재사용 단언.
- 기존 122 테스트 → 9축으로 재조직·재명명(기능 유지, 재작성 아님). 회귀 바닥.
- **커버리지 맵**: 택소노미 셀 → 시나리오 → 불변식. 테스트 없는 셀 = 보이는 갭.

## 5. Sim/Prod 경계 — "실제 workflow는 어떻게 구별되나"

**핵심 원칙: sim은 workflow의 복사본이 아니다.** 프로덕션 오케스트레이션·결정 코드는
**그대로 실행**되고 오직 외부 경계만 주입 seam에서 교체된다. 그래서 sim 결과가 신뢰
가능하다(테스트하는 게 진짜 코드).

**주입 seam (코드 실측)**:
- REST: `make_broker()` ([runner.py:36](../../local/localapp/runner.py), 호출 6곳: runner×3·intraday_loop·catchup·gui) → `Broker`.
- WS: `KisWebSocket(broker, on_tick=…)` / `KisOrderWebSocket(broker, hts_id, on_exec=…)` (intraday_loop).
- 시계: `datetime.now(KST)` / `kst_today()` / `time.time()`.

| 경계 | 프로덕션 | 시뮬레이터 |
|---|---|---|
| REST | `make_broker()`→`KisBroker` | `SimBroker`(같은 인터페이스) |
| WS | 실제 연결 | 가짜 소스가 같은 `on_exec`에 스크립트 이벤트 주입 |
| 시계 | wall clock + 스케줄러 | `SimClock` + 시나리오 러너가 cycle()/settlement() 호출 |

**경계 강제 4가지 (양방향 오염 차단)**:
1. **물리적 격리** — `sim/`·`fixtures/`는 배포 패키지 밖. PyInstaller는 `localapp/`만 번들
   → sim 코드는 프로덕션에서 실행 자체가 불가.
2. **`if sim:` 분기 금지** — 임시방편 anti-pattern. 대신 **의존성 주입**: 프로덕션은
   아무것도 안 넘김(실 default), sim만 Sim*를 주입.
3. **import 가드 테스트** — `localapp/`가 `sim`/`tests`를 절대 import 안 하는지 단언.
4. **seam이 유일 접점** — Broker/WS/clock 선 위는 prod·sim 바이트 동일. "실제 workflow"는
   한 번만 정의된다.

**선결 정리**: 지금 `make_broker()`가 6곳 인라인 → 단일 injectable provider(composition
root)로 모은다. 이것이 sim 주입점인 동시에 코드 정리의 첫 항목(§6).

## 6. 기존 코드 정리 — "어떤 식으로 정리하나"

**먼저**: 이 spec은 코드를 지금 다시 쓰지 않는다. (1) 목표 구조 명시(상태머신+불변식이
seam 정의) + (2) 안전망(sim) 구축 → 이후 모든 재구성이 *동작 보존 + sim 단언*이 되게
한다. 실행은 단계별, 각자 sim-검증 plan. **빅뱅 없음.**

**정리 원칙 (엉킴의 정체)**: happy-path workflow와 횡단 엣지케이스 핸들러가 인라인으로
섞인 것이 엉킴이다. **불변식 선을 따라 분리** — 각 핸들러를 *그것이 강제하는 불변식*에
연결된 이름 있는 테스트 가능 유닛으로 추출.

**목표 분해 (상태머신이 안내), `trader.py` →**
- **체결/원장 코어** (단일 writer + 락): `_apply_fill`·`_resolve_pending`·pending 관리 =
  상태머신 엔진. → INV-FILL/CONC/LEDGER
- **주문 라우터**: `_submit_buy/_submit_sell`·`_is_reserved_us`·tick/가격제한 계산. → INV-ORDER/CASH
- **사이클 오케스트레이션**: `cycle`/`_cycle_body`·청산패스·매수패스·리밸런싱 게이팅.
- **리스크/안전**: killswitch·drawdown·turnover 한도 → `killswitch.py`와 통합. → INV-KS
- **reconcile**: 원장↔KIS drift → `analytics.py`와.
- **composition root**: broker/ws/clock 배선 → 단일 provider (§5 sim seam도 여기서 열림).
- **이미 분리됨(유지)**: Broker/KisBroker(REST)·WS feeds·state_store(M0)·intents(L-01)·market_index(M1).

**재구성 이동 1회의 절차 (안전 보장)**: 유닛 선택 → sim 시나리오가 현재 동작+불변식
단언(green) → *동작 변경 없이* 추출 → 같은 시나리오 still green + 기존 122 테스트 green →
커밋. 작고 가역적이고 단언됨.

**안 하는 것**: 미관용 rename·추측 계층화·빅뱅 재작성. 불변식 경계를 따라 엉킴을 줄이는
추출만.

## 7. M-마이그레이션 편입

- **M2(ODNO)/M3(동시성) live 게이트 → API-사실 probe**로 전환: 픽스처 녹화 → 오프라인
  리플레이. M3 race는 동시성 시나리오로 결정론 검증(기존 `test_trader_concurrency` 확장).
- **M4(universe 단일출처) = 환경 위에서 실행하는 첫 리팩토링** — sim이 전/후 동작 보존을
  단언.

## 8. live "probe" 집합 (축소된 live 표면)

한 번의 live VTS 창에서 캡처할 사실 목록 — 각자 픽스처 산출 후 영원히 리플레이:
- V-M2-1 WS `ODER_NO` 패딩 형태
- V-M2-2 미국 예약주문 ODNO ≠ 개장 체결 주문번호 여부
- V-M3-1 실거래 동시부하 데드락/race 부재
- 인코딩: H0GSCNI0 4자리 packed price, daily-ccld 필드, 대표 에러코드(EGW00201 등)

(상세는 [STRUCTURAL_MIGRATION.md](../STRUCTURAL_MIGRATION.md) 검증 로그와 동기화.)

## 9. 환경 자체의 검증 (자기 신뢰)

과거 실제 incident를 시나리오로 재현 → **구버전 코드에서 FAIL, 수정본에서 PASS**:
- (a) 2026-05-28 KIS 점검창 과보수 가드의 catch-up 매수 차단.
- (b) M3 ledger 크로스스레드 race.
- 그리고 기존 122 테스트 전부 유지. 이로써 시뮬레이터가 "진짜 결함을 잡는다"를 증명.

## 10. 단계 (각 단계 독립 가치 · 각자 writing-plans)

- **P1** INVARIANTS.md + 상태머신 doc + 9축 택소노미 (순수 문서 — 즉시 레퍼런스, 앵커)
- **P2** 최소 시뮬레이터(SimClock+SimBroker+러너) + composition root 정리 → KRX 하루
  end-to-end 1개 시나리오 + 불변식 단언 + import 가드 테스트
- **P3** record-replay — live 창에서 probe 캡처 → 픽스처; 동시성 시나리오
- **P4** 9축 전 시나리오 백필 + 커버리지 맵 + 과거 incident 재현
- **P5** M4 리팩토링을 환경 위에서 실행 (첫 검증된 리팩토링)

## 11. 성공 기준

- 9축 모든 셀에 ≥1 시나리오(또는 명시적 갭 표기) — 커버리지 맵으로 가시화.
- 새 엣지케이스 추가 = "택소노미 행 + 불변식 + 시나리오 1개" 루틴으로 환원.
- 과거 incident 2건이 sim에서 재현·회귀 고정.
- live 표면이 §8 probe 목록으로 축소(그 외 전부 오프라인 결정론).
- 프로덕션 코드에 sim import·`if sim` 분기 0 (가드 테스트로 강제).
