## 주요 변경 — Catch-up 본질 보강 5건 (D-1 · D-2 · D-3 · D-5 · G-8 server)

v0.9.12까지 갖춰진 catch-up 골격(cycle·settlement·손절·plan idempotency)에 **빈틈 보완** 묶음. 사용자 align 후 권장안 적용 + UI 누락 거짓 음성 fix (G-8 server).

### Fix 1 (D-1) — Error로 종료된 cycle entry 재시도 허용

**근본 원인**: `cycles.jsonl`에 `summary.error` 있는 entry가 남으면 catch-up이
"이미 실행됨"으로 판정 → 다음 부팅에서도 skip. PC ON 상태에서 cycle 외부
예외(KIS 일시 거부·네트워크 transient) 발생 시 자동 회복 못 함.

**변경**: [localapp/catchup.py](localapp/catchup.py)
- `_last_of`이 `summary.error` 있는 entry는 건너뜀 → catch-up 재시도 허용
- 자금 안전은 L-01 intent journal idempotency가 차단 (submitting 상태 intent는 KIS 당일 주문 매칭으로 마감)

**비고**: 실제로 `runner.run_cycle`의 outer try/except는 log_cycle 호출 안 함 →
대부분의 cycle 외부 예외는 cycles.jsonl entry 자체가 안 남음. 본 fix는 settlement
오류나 trader.cycle 내부 log_cycle 직후의 edge case 안전망.

### Fix 2 (D-2) — Settlement 누락 일수 가시성

**근본 원인**: 사용자가 며칠 PC OFF 후 부팅하면 단일 `run_post_close_settlement`
호출로 reconcile drift 누적분 모두 정리되지만, "5일 누적 누락" 같은 가시성 없음.
amber 배너에 "차이 없음"만 표시되어 무엇이 일어났는지 모름.

**변경**:
- [localapp/catchup.py](localapp/catchup.py)
  - `CatchupPlan`에 `krx_settlement_days_missed`·`us_settlement_days_missed` 필드
  - `_count_business_days_missed(market, last_settle, target)` helper
  - `_decide_catchup_plan`이 누락 영업일 수 계산
  - `_save_result`이 settlement 결과에 `days_missed` 포함
- [localapp/gui.py](localapp/gui.py)
  - `_format_catchup_summary`이 2영업일 이상 누락 시 "(N영업일 누적 누락)" 표시

**비고**: settlement은 current-state reconcile이라 단일 호출로 충분. days_missed는
실행 횟수가 아닌 사용자 가시성 전용.

### Fix 3 (D-3) — Cycle outer error 1·5·15분 backoff 3회 재시도

**근본 원인**: PC ON 상태에서 KIS 일시 장애·네트워크 transient로 cycle outer
try/except가 잡으면 error snapshot push 후 종료 → 다음 cron까지 cycle 미실행.
사용자가 인지·수동 개입 못 하면 매수 0건 + 청산 보류 상태.

**변경**: [localapp/runner.py](localapp/runner.py)
- `run_cycle`의 cycle 실행 블록을 `for attempt in range(1, 5)` 루프로 감쌈
- backoff schedule `(60, 300, 900)` — 1분·5분·15분 (총 4 시도, 최대 ~21분)
- 각 시도마다 `refresh_market_data`·`broker`·`trader` 모두 재초기화
- 4회 모두 실패해야 error snapshot push

**자금 안전**: L-01 intent journal이 중복 발주 차단. 이미 KIS에 발주된 매수는
당일 주문 매칭으로 재발주 방지. KRX 정규장 6h 30min 윈도우에 21분 backoff는
안전 마진 충분.

### Fix 4 (D-5) — Catch-up helpers 준비 실패 시 가시성

**근본 원인**: KIS 자격증명 미등록 등으로 `_prepare_helpers()`가 None 반환하면
results 비어 `_save_result` 호출 안 함 → catchup_result.json 미저장 → 사용자
amber 배너 미표시. 신규 사용자가 흔히 겪는 silent fail.

**변경**:
- [localapp/catchup.py](localapp/catchup.py)
  - helpers None 시 `results["_helpers_unavailable"]`에 error·plan_summary 저장 + `_save_result` 호출
  - `_save_result`이 `_helpers_unavailable` 키 인식
- [localapp/gui.py](localapp/gui.py)
  - `_format_catchup_summary`이 `_helpers_unavailable` 키 발견 시 "Catch-up 실행 보류" + "[설정] 메뉴에서 KIS appkey·계좌번호 입력 필요" 안내

### Server-side 변경 1건 (G-8) — Timeline catchup_cycle 매칭

**근본 원인**: server `_match_snapshot`이 정시 cycle scheduled time 기준 ±30분
윈도우만 매칭 → 09:38 catch-up entry처럼 윈도우 밖 catch-up이 실행됐어도
"누락" 거짓 음성으로 표시. 사용자 UI에서 "08:55 국장 자동매매 시작 ✗ 누락"이
보이는데 실제로는 cycles.jsonl에 09:38 catchup_cycle entry 있는 모순.

**변경**: [server/app/routers/trading.py](../server/app/routers/trading.py)
- `_match_snapshot`에 2차 fallback: 같은 거래일·같은 market의 `catchup_cycle`/
  `post_close_settlement` snapshot도 정시 cycle 결과로 인정
- 매칭 조건: `cycle_summary.market == market` AND
  `cycle_summary.today == scheduled.date()` AND
  `received_at.date() == scheduled.date()`
- 자금 안전 영향 0 — UI 표시만 수정

**검증** (mock 시나리오):
- KRX 08:55 + 09:38 catchup → 매칭 ✓
- 다른 거래일 catchup → 매칭 안 함 ✓
- 다른 market → 매칭 안 함 ✓
- US 05:05 + 09:27 settle catchup → 매칭 ✓

### Preview catch-up — 변경 없음 (D-4)

v0.9.13 release에서 사용자가 D-4(A)로 결정 — **서버 on-demand preview build
(이전 server 배포)가 KRX·US 양쪽 cover**. 클라이언트 측 추가 catch-up 로직 불필요.
24h 디스크 캐시 + server on-demand 조합으로 fail-safe.

### 검증

- AST·import 통과
- `_decide_catchup_plan` 다양한 now 시나리오 (장중·마감 후·비영업일·주말) 동작 확인
- `_count_business_days_missed` 단위 테스트 (2/1/7 cap 정상)
- 실 cycle 검증: 5/29 22:30 미장 catch-up · 6/1 월 KRX 08:55

### 4원칙 자가검토

- **근본 원인**: ✓ D-1 retry 허용·D-3 backoff·D-5 가시성 모두 silent fail의 본질
  원인(분기 누락) 제거. D-2는 가시성만이라 "원인 해결" 단위 작음 — 의도된 trade-off.
- **Over-eng 금지**: ✓ D-2 settlement 다중 호출 안 함(current-state reconcile이라
  단일로 충분). D-3 1회 retry로 한정(다단 backoff 거부). server-side는 변경 없음.
- **Overthinking 금지**: ✓ catch-up 정기 polling 도입 안 함 — 기동 1회 + cycle 내부
  retry 조합으로 충분.
- **검증**: AST·import·시나리오 시뮬·days_missed 단위 모두 통과. 실 cycle은
  다음 미장·KRX cron에서.

### 내부 변경

**[localapp/catchup.py](localapp/catchup.py)**
- `CatchupPlan.krx_settlement_days_missed`·`us_settlement_days_missed` 필드 추가
- `_count_business_days_missed(market, last_settle, target)` 신규 함수
- `_last_of`이 `summary.error` 있는 entry 건너뛰도록 수정
- `_decide_catchup_plan`이 settlement 누락 시 days_missed 계산 + reasons에 포함
- `run_catchup_on_startup`이 helpers None 시 `_helpers_unavailable` results + `_save_result` 호출
- `_save_result`이 `_helpers_unavailable` 키와 settlement `days_missed` 처리

**[localapp/runner.py](localapp/runner.py)**
- `run_cycle` cycle 실행 블록을 `for attempt in range(1, 5)` 루프로 감쌈
- `_RETRY_BACKOFF_SEC = (60, 300, 900)` — 1·5·15분 backoff
- 각 시도마다 모든 리소스 재초기화

**[server/app/routers/trading.py](../server/app/routers/trading.py)**
- `_match_snapshot`에 2차 fallback (G-8): 같은 거래일·market의 catchup_cycle
  /post_close_settlement entry도 정시 cycle 결과로 인정

**[localapp/gui.py](localapp/gui.py)**
- `_format_catchup_summary`이 `_helpers_unavailable` 전용 메시지 분기
- settlement 메시지에 days_missed ≥ 2 시 "(N영업일 누적 누락)" 표시

**[localapp/__init__.py](localapp/__init__.py)**
- 버전 0.9.12-beta → 0.9.13-beta
