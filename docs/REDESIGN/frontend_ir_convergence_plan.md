# 프론트엔드 IR 수렴 계획 — "전략 만들기" → "전략 연구소" 대체

작성 2026-05-30(개정). 목표: 백엔드 통합 IR 엔진(`quant_core/ir_engine`)을 프론트·저장·
실거래의 **단일 표현**으로 만들고, 레거시 operand 빌더("전략 만들기")를 단계적으로
제거한다.

**결정 개정(2026-05-30)**: BlockTree로 IR의 **논리 완전성·자유도를 검증 완료**(Stage 0).
이제 그 위에 제품의 핵심 차별점인 **문장형 빈칸 UI를 주 뷰로 전환**한다(Stage 0.7).
같은 IR(Node tree)을 렌더만 다르게 — 모델은 하나. BlockTree는 "고급" 토글로 유지(깊은
트리 편집·파워유저). 문장형이 준비되어야 Stage 4(전략 만들기 제거)에서 차별점이 안 죽는다.

---

## 1. 확인된 현재 구조 — 실거래 vs 시뮬레이션이 다른 경로

| | 표현 | 신호평가 | 사이징 | 스크리너 |
|---|---|---|---|---|
| **실거래(라이브)** | operand `Strategy.ConditionGroup` (DB) | `server/app/preview_engine.py` → `qc.explain_buy_signal_per_symbol`(=`analysis.build_signal_mask`) | 서버 `_size_and_append_candidate`(`atr_risk`/amount_pct) | `server/app/screener.py` (preset/spec) |
| **시뮬(IR 백테스트)** | Node `StrategyIR` | `quant_core/ir_engine/run_unified` | IR `SIZERS`(equal/signal/vol_inverse/target_vol/fixed_weight) | IR `universe.screener`(filter Node + rank) |
| **시뮬(레거시)** | operand | `quant_core/backtest.py`+`analysis` | 레거시 | 레거시 |

**실거래 workflow 모듈**: `server/app/preview_engine.py`(서버측 매수신호+사이징, KIS 0회) ·
`server/app/screener.py` · `server/app/routers/{sync,preview,trading}.py` ·
`local/localapp/{runner,trader,intraday_loop,catchup,...}.py`(후보 발주+청산평가+KIS 실행).
저장: DB `Strategy.definition`(operand).

**시뮬레이션 모듈**: `quant_core/ir_engine/*`(`/ir/strategy`) · 레거시 `backtest.py`(`/backtest`).

### ⚠ 중대 발견 — 백테스트 ≠ 라이브
실거래 신호평가/사이징과 IR 백테스트가 **다른 엔진·표현**(라이브 `atr_risk` 사이징은 IR에 없음).
같은 전략도 백테스트와 실거래가 달라질 수 있다. **수렴의 본질 가치 = 단일 엔진으로
backtest=live 일치(자금 안전 근본 개선).**

---

## 2. 단계별 계획 (각 단계 독립 배포·게이트 통과 후 진행, 라이브 무중단)

### Stage 0 — 전략 연구소 완성 (순수 프론트, 라이브 무영향) ✅
`/lab` IrBuilder가 풀 StrategyIR 표현:
- **0a** `BlockTree` param kind `value_list`·`bool` 렌더 + `IrParamSpec` 타입 → `is_in`(섹터제외) 입력 가능.
- **0b** 사이징 `target_vol`(+`target_vol_pct`)·`fixed_weight`(+`weights`)·`fixed_amount`·`pct_cash`; 진입 `top_pct`·`threshold`·`refill`.
- **0c** 유니버스 `screener`(filter=condition BlockTree + rank ref/top_n/direction); 시뮬 비용(commission·slippage·sell_tax·short_borrow·funding·rfr).
- **0.5 (일원화)** 룰/팩터 토글 제거 — 엔진의 직교 축을 그대로 노출: 진입 트리거(이벤트/정기/상시)·신호타입(condition|score 자유, 루트 picker가 둘 다 제공)·**청산(항상 노출 — 정기+청산 = A-1 플래그십 가능)**·사이징(전 모드)·방향. 부적합 조합은 validate가 안내. (구 UI가 통합 엔진을 안 반영하고 옛 Path A/B 이분법을 되살렸던 문제 해소.)
- 게이트: 검증전략(A-1 섹터제외·정기+청산·A-2 롱숏·B-1 target_vol·B-5 fixed_weight) 조립 가능 · `tsc`·`build` 클린 · 브라우저 렌더·해피패스·직교화 실측. **완료.**
- ⚠ 라이브 스택의 신규 엔진기능 실측은 **uvicorn이 `core/`를 안 봐서 stale** — `--reload-dir ../core`로 재시작 필요(코드는 계약검증 7/7).

### Stage 0.7 — 문장형 UI (핵심 차별점, 순수 프론트+카탈로그 메타, 라이브 무영향)
**결정: 방식 A(카탈로그 phrase 템플릿 + 재귀 렌더러), BlockTree 완전 대체(문장형 단일 뷰).**
같은 IR을 **문장형 빈칸**으로 렌더 — `SentenceTree`가 `BlockTree`를 대체. 깊은 중첩은 인라인 절(괄호·들여쓰기)로 편집.
- **신호(Node tree)**: 카탈로그 블록마다 **문장 템플릿(`phrase`) 메타** 추가(backend, 자기서술 유지) →
  프론트 `SentenceTree` 재귀 렌더러가 슬롯=하위문장·params=인라인 빈칸으로 조립.
  예: `compare(>, Close, ts_mean(Close,20))` → "[이 종목]의 [종가]가 [[종가]의 20일 평균]보다 [크면]".
  깊은 중첩은 절(clause)/하위문장로, 너무 깊으면 "고급(블록)" 권유.
- **전략 골격(유니버스·진입·포지션·청산·사이징)**: Node가 아니라 spec 필드 → 프론트 문장 조합.
  예: "[코스피 전체]에서 [정기·매월] 리밸런싱으로 [점수] 상위 [20]종목을 [동일가중]으로 보유,
  [적자전환]이면 청산. 비용 [기본]."
- **단일 뷰**: `SentenceTree`가 신호·청산·스크리너필터·그룹라벨·펼침라벨의 `BlockTree`를 전부 대체. BlockTree 제거.
- 게이트: 검증전략(룰·A-1 정기+청산·A-2 롱숏·B-5)이 문장형으로 표현·편집·IR 왕복 ·
  `tsc`·`build` 클린 · 브라우저 렌더·해피패스 실측.

### Stage 1 — 연구소 저장/불러오기 (IR StrategyDef, 라이브 무영향) ✅
- **판별자**: `Strategy.engine` 컬럼(`operand`|`ir`, 기본 operand) — `db._NEW_COLS` 멱등 마이그레이션.
  명시·exhaustive 디스패치: `_validate(engine, def)` → operand=`qc.Strategy`, ir=`StrategyIR.model_validate`.
  교차검증으로 침묵 손상 차단(IR 정의를 operand engine으로 저장 시 422).
- **저장**(`IrBuilder`): 이름 입력 + 저장 버튼(초안/모의/수정). `engine='ir'`로 create/update → `/strategies/:id`.
- **불러오기**: `/lab?edit=<id>` → `hydrate()`가 `buildStrategy`의 역으로 전 폼 state 복원(신호 트리·유니버스·포지션·청산·시뮬·펼침).
- **내 전략/상세**: `Strategies` 카드·`StrategyDetail` config 탭을 engine으로 분기 —
  IR 카드는 유니버스·진입·방향·사이징 요약, IR config 탭은 설정 조회 + "전략 연구소에서 편집".
  버전·현황·백테스트 내역 탭은 engine-무관(그대로).
- 게이트: ✅ 라운드트립(브라우저 실측: 저장→카드→상세→편집→수정저장→버전2) · 레거시 operand 무손상 ·
  서버 6/6 + 라이브 API 라운드트립 · `tsc`·`build` 클린.

### Stage 2 — 서버 preview를 IR로 (backtest=live 일치, 머니패스)
- **2-A ✅ IR 다음날 후보 평가기**: `preview_engine._evaluate_ir_strategy` — StrategyIR을
  마지막 바에서 평가, ir_engine의 `_universe_symbols·_scoped·_select·_target_weights·_screener_mask`를
  **재사용**해 backtest=live 신호 선택 일치. `build_user_preview`가 `s.engine`으로 디스패치.
  사이징은 preview 추정(로컬앱이 실사이징). US 종목 qty=None. 단위테스트 5/5(신호 파리티·디스패치·operand 무영향).
  **프로덕션 dormant** — IR은 draft 전용이라 paper/live 쿼리에 안 잡힘.
- **2-B (남음) atr_risk 사이저 IR 부활**: 소비처(로컬앱 IR 실행)가 Stage 3에서 생기면 정당.
  그 전엔 enum 미추가(원칙: 미구현 모드를 enum에 두지 않음). → Stage 3과 함께.
- **2-C (남음) 스크리너 재조정**: `server/screener.py`(라이브 preset/spec) ↔ IR `universe.screener`(filter+rank) 일치.
- **컷오버 게이트(= IR paper 재오픈)**: Stage 2+3 동시 충족 후에만 IrBuilder "모의 적용" 재개.
  preview(2-A)만으론 후보만 보이고 로컬앱이 실행 못 함 → 반드시 Stage 3과 함께 열어야 깨진 중간상태 회피.
- 게이트: paper 시나리오 · MockBroker · (선택)섀도 비교.

### Stage 3 — 로컬앱 청산·사이징을 IR로
- **3-0 ✅ 사이클 매핑**: `runner.run_cycle`→`trader._cycle_body`(청산 `_evaluate_exit` @1213,
  `qc.Strategy(**def)` @1207)→`_enter_from_preview`/`_try_buy_one_symbol`(사이징 @814-850).
  Broker는 `make_broker()`@runner:36-48 주입(MockBroker 치환점). 로컬앱은 OHLC+지표 보유(IR 조건 평가 가능).
- **3-A ✅ 라이브 결정 로직 (순수, 검증)**: `quant_core/ir_engine/live.py` —
  `cycle_exit_reason`(보유기간+매도조건 Node; tp/sl/trail은 operand처럼 intraday 전담)·
  `event_buy_qty`(이벤트 진입 사이징 = 엔진 `_budget`과 동일). 단위 10/10.
  **파리티 버그 수정**: preview 이벤트 사이징이 일부 모드에서 엔진과 불일치했던 것을 바로잡음
  (on_signal은 항상 per-name 예산, 단일 유니버스=100%). preview·live가 `event_buy_qty` 단일 소스 공유.
- **3-B 청산 배선 ✅**: `trader._exit_reason_for(defn, ...)` engine 디스패치(operand=`_evaluate_exit`+strat,
  ir=`cycle_exit_reason`+strat=None). `_cycle_body`가 이를 호출하고 IR은 리밸런스 skip·sell_pct 100% 가드.
  단위 5/5(operand 무영향 + IR 보유기간·매도조건). 파일·브로커 부작용 없는 순수 디스패치 검증.
- **3-B 매수 사이징 + 하니스 IR화 ✅**: `_try_buy_one_symbol`에 `engine=='ir'`→`event_buy_qty` 분기(operand는 else로 strat 가드).
  **기존** `local/sim` 하니스 재사용·확장: `SimBroker.account_snapshot(overseas=)` 수용 + `scenario.strategy_buy_and_fill`
  (결정경로 `_try_buy_one_symbol` 구동) 추가. `tests/scenarios/test_ir_strategy_cycle.py` 3/3 — IR 매수 사이징(pct_cash 14주·단일 100% 142주)
  →체결→원장→청산판정(매도조건)→FLAT + operand 무손상. 전체 시나리오+Trader 37 통과(회귀 없음).
  (※ MockBroker 신규 빌드 불필요였음 — 기존 SimBroker 하니스 존재. 중복 스캐폴딩 제거함.)
- **3-B 매수 라우팅 ✅**: `_enter_from_preview`에 `engine=='ir'` 분기(universe.kind→is_multi_key, operand 블록은 else로,
  trade_symbol 파싱 안 거침). `tests/scenarios/test_ir_strategy_cycle.py`에 실 진입경로 테스트 추가 — 14 시나리오 통과, Trader 스위트 62 회귀없음.
  **→ Stage 3-B(IR 매수+EOD청산) 완료, SimBroker 하니스로 end-to-end 검증.**
- **3-C 장중 가격청산 IR ✅ (갭5)**: 엔진 `_exit_reason`에서 가격기반(tp/sl/atr·트레일)을 공유 scalar
  `price_exit_reason`으로 추출 → 백테스트(`_exit_reason`)·라이브(`live.intraday_exit_reason`) **단일 소스**.
  엔진 144 테스트로 백테스트 파리티 보존. `intraday_stop.on_tick`이 engine 분기(operand=`sell_rules`,
  ir=`position.exit`; IR sell_pct=100%). intraday 시나리오 2 + live 단위 4 + 엔진 144 통과.
  - **⚠ 근본 결함 동시 수정**: `StrategyIR.model_dump`엔 engine이 없어 stored definition에 engine이 빠짐
    → 로컬앱 `definition.get("engine")` IR 판별이 **production에서 항상 operand 오판별**(테스트는 def에
    engine 인라인이라 미검출). 수정: `/sync/strategies`가 serve 시 engine을 definition에 주입(서버 1곳).
    이로써 3-B 매수·EOD청산도 production에서 정상 동작. 서버 주입 테스트 1 추가.
  - **취약 경로 정리**: `intraday_stop.on_tick`이 원장에 없는 `strategy_id`로 strat_def 재조회하던 것을
    EOD와 동일하게 `pos["definition"]` 직접 사용으로 통일(operand 장중청산도 잠재 미발동이던 것 수정).
    `get_strat_def`/`_get_strat_def_lookup` 제거(dead). 기존 intraday 27 테스트 통과.
- 게이트: ✅ SimBroker end-to-end(매수→보유→tick→손절→체결→FLAT) · 청산/사이징 패리티.
- **3-D 데이터 매니페스트 IR 스코프 ✅ (갭1)**: 수급 종목 결정을 engine 분기.
  - **서버**(`main.py` 해외 등록): `s.engine=='ir'`→`universe.symbols`로 managed_overseas 등록
    (column으로 판별 — stored definition엔 engine 없음). KR 종목은 전종목 fetch라 무관.
  - **로컬**(`dataset_scope.needed_symbols`): IR이면 `universe.symbols` + signal/exit.condition Node
    참조(`blocks.referenced_symbols`)를 포함. exit.condition 참조 누락 시 매도 조용히 미발동 방지(fund-safety).
  - 검증: `test_dataset_scope_ir.py` 5(universe·exit참조·보유분·operand무손상·파싱실패 폴백).
- 게이트: ✅ IR universe·참조 종목이 서버 fetch·로컬 load 양쪽 스코프에 포함.
- **3-E 컷오버 ✅ 코드 (갭7)**: IrBuilder draft-only 빗장 해제 — `save(runMode)` + "모의 적용" 버튼
  (operand `Backtest.save("paper")` 패턴 동형). tsc·vite build 통과. 서버 preview는 이미
  paper/live 쿼리(`preview_engine:607`)에 IR 디스패치(`:621`) 존재 → 프론트 빗장이 유일한 활성화
  스위치였음(주석 갱신). **전체 체인 일관**: 저장(paper)→서버 preview IR 후보→데이터 수급(3-D)→
  로컬앱 pull(engine 주입)→매수·EOD청산·장중청산 IR(3-B/3-C).
  - **남은 go-live(사용자 액션)**: 웹·서버 배포(git push — 자동 push 금지) + 실제 모의(VTS) 사이클
    1회 검증. 코드 레벨·SimBroker·서버 라운드트립은 검증 완료, 브라우저 클릭/실거래는 사용자 환경 필요.

### Stage 4 — 전략 만들기 제거 (✅ 프론트 단일화, 2026-05-30)
- **사용자 결정**: 출시 전(실거래 operand 없음) → 마이그레이션 불필요 + 전체 일괄.
- **프론트 단일 체제 ✅**: `/backtest` 라우트·nav "전략 만들기" 제거, `Backtest.tsx`·`ConditionBuilder.tsx`
  삭제. `StrategyDetail` operand `ConfigEditTab`(=BuildTab 재사용) 제거 → config 탭은 IR 전용,
  레거시 operand 행은 read-only 안내. `Dashboard`·`StrategyDetail`의 `/backtest` 링크 → `/lab`.
  `api.ts`: `runBacktest`·`runAnalysis`·`listBacktestRuns` 등 operand 전용 제거, create/update engine 기본값 ir.
  → 사용자는 **전략 연구소(/lab) + 내 전략(/strategies)** 두 경로만. 결과 보관함은 이미 내 전략의 "백테스트 내역" 탭.
- **내 전략**: 4탭(설정값·버전·현황·백테스트 내역) 이미 IR 분기 — 조회/버전/현황 충족, 편집은 /lab 링크.
- **UX**: 버튼 호버 가시성 — `button:hover`·`.download-link`·`.promote-btn`이 `--accent`(흰 글자 ~3:1) →
  `--accent-hover`(#c25c40, 4.2:1, DESIGN.md 채움 호버 토큰)로 통일.
- 검증: tsc·vite build 통과(번들 834→743 kB). 브라우저 E2E(로컬 dev→8000, test 계정): nav 단일화·
  전략 연구소 실데이터·모의 적용 버튼·내 전략 4탭·버튼 호버(`--accent-hover`)·콘솔 에러 0 실측.
- **백엔드 operand 엔진 완전 제거 ✅ (2026-05-30, IR 동작 검증 후)**:
  - 사전 검증(Phase A/B): 서버 IR(생성·`/ir/strategy` 백테스트 실데이터·`/sync/strategies` engine 주입)·
    웹 E2E 실측 후 제거 착수.
  - core: `strategy.py`·`engine.py`·`analysis.py` **파일 삭제**(qc.Strategy·run_backtest·build_signal_mask·
    run_analysis·parse_trade_symbols·sell_pct_for_reason). `backtest.py`는 ir_engine 공유 헬퍼만 잔존
    (`_empty`·`_metrics`·비용상수·`_MAX_POSITIONS_GLOBAL`·`_PortPosition`). `__init__.py` operand export 제거.
  - server: `/backtest/run`·`/analysis/run`·`/backtest/runs` 엔드포인트 삭제(`/symbols`만 잔존),
    `_validate`·preview·매니페스트 IR 전용. `StrategyIn.engine` 기본 ir.
  - local: `trader._exit_reason_for`/`_try_buy_one_symbol`/`_enter_from_preview`/`_cycle_body`·`intraday_stop.on_tick`·
    `dataset_scope` operand 분기 제거(IR 전용). `_evaluate_exit`·`evaluate_price_trigger`·리밸런스 헬퍼 삭제.
  - tests: operand·parity 테스트 삭제, IR 테스트는 operand 거부/IR 전용으로 갱신.
  - **회귀 검증**: core+platform 254 · 로컬 142 · 서버 IR 통과. operand 함수 참조 0(grep). IR 엔진 11·블록 5 테스트 건재.
- **IR 백테스트 영속화 ✅**: `/ir/strategy`에 `strategy_id` 동봉 시 BacktestRun 저장(`_persist_ir_backtest`)
  → 내 전략 "백테스트 내역" 탭(operand `/backtest/run` 영속화 이전). 웹 IrBuilder가 `?edit` 중 strategy_id 전달.
  test_server_ir_strategy에 영속화 테스트 추가. (이전엔 IR 백테스트 미저장 → 내역 항상 빔이었음.)
- **최종 리뷰·정리 ✅**: 3영역 독립 리뷰(버그 0, 머니패스 정확). 잔여 dead code 전부 제거(로컬 rebalance_state·
  screener_client·skip 카운터, 웹 고아 타입·api, 서버 고아 스키마·serialize_analysis, stale 주석). 웹 tsc·vite build 0.
- 게이트: ✅ operand 코드 0(사용자·백엔드 전부). IR(전략 연구소) 단일 엔진.

---

## 2.9 정밀 검토 (2026-05-30) — 모듈별 갭 + 시뮬레이션 정의

**시뮬레이션 용어(코드 기준)** — 사용자 비노출 forward-sim은 없음:
- 백테스트(과거·`ir_engine`/`backtest`) · 다음날 preview(무상태 신호평가·`preview_engine`) ·
  모의투자(KIS VTS 실서버 — `kis_broker` `virtual=True`, 로컬 sim 아님) · SimBroker 하니스(사이클 결정론·테스트 전용).
- **결정: "자동매매 시뮬레이션 모듈" = SimBroker 검증 하니스(`local/sim`)를 IR에 맞게 완성하는 것**
  (사용자 UI 무변화, 내부 품질). 모의투자(VTS)는 별도 모듈이 아니라 실거래 경로를 VTS로 향하게 한 것 →
  IR 모의투자 = 실거래 경로 IR 완성 + 컷오버.

**라이브 경로 IR 갭 인벤토리(검증된 위치)**:
| # | 결정 지점 | 위치 | IR 상태 |
|---|---|---|---|
| 1 | 데이터 수급 종목 | `server/main.py` 매니페스트 + `local/dataset_scope` | ✅ IR(3-D) — engine 분기로 universe.symbols+참조 |
| 2 | 내일 후보 신호평가 | `server/preview_engine._evaluate_ir_strategy` | ✅ IR(2-A) |
| 3 | 매수 선정·사이징 | `trader._enter_from_preview`·`_try_buy_one_symbol`(`qc.Strategy`·`amount_pct`·`screener_limit`·`parse_trade_symbols`) | operand-only — `event_buy_qty` 분기 필요 |
| 4 | EOD 청산 판정 | `trader._exit_reason_for` | ✅ IR(3-B 청산) |
| 5 | 장중 가격청산(익절·손절·트레일) | `intraday_stop.on_tick` | ✅ IR(3-C) — `price_exit_reason` 공유 scalar 분기 |
| 6 | 리밸런스/스크리너 멤버십 | `trader._rebalance_members`(`trade_symbol`) | operand-only — IR 1차 이벤트진입이라 N/A, 후속 |
| 7 | 컷오버(모의 적용) | IrBuilder `save(runMode)`+모의적용 버튼 | ✅ 코드(3-E) — 배포·실거래 검증은 사용자 |

**최적 경로(test-first, 엔진함수 재사용으로 backtest=live 일치)**:
- (A) 하니스 확장 `sim/scenario.py`에 결정경로 구동 헬퍼 + (B) IR 매수 배선(갭3) + (C) `tests/scenarios/test_ir_strategy_cycle.py`(매수→체결→원장→EOD청산→FLAT) →
  (E) 장중청산(갭5: 엔진 `_exit_reason`→공유 `exit_reason_for` 추출 후 `intraday_stop` 분기) + 시나리오 →
  (D-pre) 데이터 수급(갭1) → **컷오버**(갭7) → Stage 4(operand→IR 마이그레이션·레거시 제거).

## 3. 결정·리스크

- **문장형 UX**: BlockTree로 충분(결정). 별도 레이어 미구축.
- **atr_risk 사이징**: Stage 2에서 IR 사이저로 부활(라이브 패리티 필수). enum 미구현 모드를 두지 않는 원칙은 "소비처 생기면 부활"이었고, 실거래가 그 소비처.
- **마이그레이션**: 표현 불가 operand 전략은 자동 변환 실패 플래그 후 수동 안내.
- **데이터 제약 경계**(불변): 분봉·옵션·미수급 이벤트는 엔진 로직 추가 안 함(`block_ir_spec.md` §전략 커버리지 감사).
- **안전**: 각 머니패스 단계는 섀도 병렬→검증 후 컷오버. 라이브 무중단.
