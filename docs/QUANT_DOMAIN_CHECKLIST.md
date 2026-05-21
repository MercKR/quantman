# 시스템 트레이딩 도메인 체크리스트

이 문서는 `/풀리뷰`의 **Phase 8**에서 사용된다. 각 항목은 ✅ (검증 완료) / ⚠️
(부분·의심) / ❌ (실패·결함) 중 하나로 평가한다. ❌는 critical 결함으로
SUMMARY에 surface한다.

체크 방법은 "Verify" 줄에 명시 — grep, 코드 inspection, 골든 테스트, 또는 수동
실행 중 어느 것인지.

---

## 1. 백테스트 정확성

### 1.1 Look-ahead Bias 방지

- [ ] **신호 → 진입 시점:** 종가로 시그널 → 다음 거래일 시가 진입 (default
      `fill="next_open"`).
      Verify: `core/quant_core/backtest.py:7-11` docstring + `tests/golden_backtest.py`
      "buy_and_hold" 케이스.
- [ ] **지표 계산 lookback:** 모든 indicator가 자기 시점 이전 데이터만 사용.
      Verify: `core/quant_core/indicators.py` 각 함수 `.rolling()`·`.shift()`
      파라미터 검토 — 음수 shift 없어야 함.
- [ ] **build_signal_mask 시계열 순서:** 결과 mask가 input dates 순서와 일치.
      Verify: golden test에서 같은 데이터 두 번 실행 시 결과 동일.

### 1.2 시장 마찰 모델링

- [ ] **슬리피지:** `slippage` 파라미터로 사용자 조정 가능, default 0.0005 (0.05%).
      Verify: `backtest.py:75` default 값 + UI에서 노출되는지.
- [ ] **수수료:** `commission` 파라미터, default 0.00015 (0.015%).
      Verify: `backtest.py:74`. 매수·매도 동일 가정 → 한국 시장 실제 (매도 시
      거래세 0.18% + 농특세 0.05% = 0.23% 추가) 반영 여부 확인.
- [ ] **세금 (한국):** 매도 시 거래세·농특세 차감 모델.
      Verify: 현재 미반영으로 추정. 골든 테스트에서 명시적 검증 → ❌ 시 backlog 추가.
- [ ] **호가 단위 라운딩:** 가격 입력·체결가가 한국거래소 호가 단위 (1원~1000원
      구간별) 준수.
      Verify: `core/quant_core/exec_defaults.py:round_to_tick`, `tick_size` 호출
      여부 grep — `core/`·`local/`에서.

### 1.3 기업 액션 (Corporate Actions)

- [ ] **배당 조정:** 가격 데이터가 배당 조정된 adjusted close 사용.
      Verify: `core/data/*.parquet` 생성 스크립트 (`data_fetcher.py`) 검토.
      KRX·NAVER 원본의 adjustment 여부 확인.
- [ ] **액면분할 조정:** 분할 발생 종목 (예: 삼성전자 50:1, 2018-05-04) 가격
      연속성 확인.
      Verify: 005930.parquet의 2018-05-03/04 가격 비율 점검.
- [ ] **무상증자·유상증자:** 권리락 가격 조정.
      Verify: 표본 종목 (사용자가 자주 거래하는 것) 권리락일 가격 점검.
- [ ] **상장폐지:** 폐지된 종목은 마지막 거래일 이후 데이터 없음으로 처리.
      Verify: 종목마스터 sync 시 폐지 종목 제거 로직 확인.

### 1.4 자본 곡선 정확성

- [ ] **일별 evaluation:** equity curve의 매일 값이 현금 + 보유 종목 시가
      평가합과 일치.
      Verify: golden test "buy_and_hold"에서 (현금 + 종목 * close) 매일 확인.
- [ ] **부분 체결 처리:** 호가 부족 시 부분 체결 → 잔량은 다음 시점 재시도 또는
      취소.
      Verify: 백테스트는 단일 종목·전액 투입 가정이라 부분 체결 없음 — 실전
      엔진 (`local/`)에서 검증.
- [ ] **미체결 처리:** 매수 시 가격 안 맞으면 미체결 → 다음날 신호 재평가.
      Verify: backtest에서 "next_open" fill 가정으로 항상 체결. 실전에서는
      미체결 큐 관리 필요.

---

## 2. 시그널 → 주문 변환

### 2.1 Idempotency (중복 방지)

- [ ] **같은 시그널 2번 발생 → 주문 1번:** local app에서 같은 (symbol, date,
      side) 조합으로 두 번 시도 시 거부.
      Verify: `local/localapp/` 주문 큐 코드 grep — dedup 키 (보통
      `(symbol, date, side, strategy_id)`) 확인.
- [ ] **재시작 후 중복 방지:** local app crash 후 재시작 시 이미 전송한 주문
      재전송 안 함.
      Verify: 주문 ledger persistence + 재시작 시 outstanding orders 조회.
- [ ] **order_no 기반 KIS 응답 매칭:** KIS가 반환한 order_no를 ledger에 저장,
      후속 체결 통지 (WS) 매칭에 사용.
      Verify: `local/localapp/kis_*.py`에서 order_no 저장·조회 흐름.

### 2.2 포지션 사이징

- [ ] **사용자 지정 비중·금액 정확 반영:** "자본의 10%"·"100만원" 등 입력이
      실제 주문 수량으로 변환 시 라운딩 외 오차 없음.
      Verify: 사이징 함수 grep + 단위 테스트 권장.
- [ ] **잔고 부족 시 거부:** override 금지. 부족하면 알림 + skip.
      Verify: 주문 생성 단계의 cash check.
- [ ] **최소 매매 단위:** 1주 미만은 매수 안 함.
      Verify: 사이징 라운딩 로직.

---

## 3. 모의 ↔ 실전 일관성

### 3.1 시그널 일치

- [ ] **같은 전략·같은 시점에서 모의·실전이 같은 시그널 발생:** Phase 13.4
      overlay에서 두 곡선이 시그널 시점에서 같은 방향으로 움직임.
      Verify: `web/src/components/MonitorTools.tsx:BacktestLiveOverlay` 동작
      확인 + 실제 paired test (모의·실전 한 주 병행).

### 3.2 Fill 차이 인지

- [ ] **모의는 즉시 체결 가정 vs 실전은 큐 대기:** 실전에서 슬리피지·미체결로
      모의와 결과 차이 발생 → 사용자에게 명시.
      Verify: Monitor·Dashboard에서 "백테스트 vs 라이브 괴리" 설명 (Phase
      13.4) 노출 확인.

---

## 4. 리스크 관리

### 4.1 Kill Switch (일일 손실 한도)

- [ ] **`kill_switch_daily_loss_pct` 트리거 시 신규 진입 즉시 차단.**
      Verify: 일별 손실 계산 위치 grep + 차단 분기 코드.
- [ ] **기존 청산은 계속 작동.** kill switch는 stop loss·take profit를
      막지 않음.
      Verify: 청산 경로가 kill switch 분기와 분리되어 있는지.
- [ ] **Webhook 알림 발송 (Phase 38.7).**
      Verify: alert 트리거 위치 grep + webhook 전송 로직.
- [ ] **UI 즉시 반영.** Dashboard 시스템 상태가 "활성 (kill switch)" 표시.
      Verify: Phase 42-3 Dashboard 시스템 상태 행 — 페어링·연결 상태에 따라
      "—"/"정상"/"활성".

### 4.2 Drawdown 한도

- [ ] **`max_drawdown_pct` 트리거 시 신규 진입 차단** (Phase 38.10).
      Verify: drawdown 계산 (자본 고점 대비) + 차단 분기.
- [ ] **Peak 회복 시 자동 해제.** drawdown이 한도 이하로 회복 시 차단 풀림.
      Verify: 해제 조건 코드.

### 4.3 단일 종목·섹터 한도 (구현 여부 확인)

- [ ] **종목당 최대 비중:** 자본의 X% 초과 종목 매수 거부.
      Verify: 현재 미구현으로 추정. ❌ 시 backlog.
- [ ] **섹터 분산:** 한 섹터에 자본 X% 초과 거부.
      Verify: 현재 미구현. ❌ 시 backlog.

---

## 5. KIS ↔ ledger 정합성 (Phase 40)

### 5.1 Reconciliation

- [ ] **주기적 drift 감지.** local app이 KIS에서 잔고·체결 조회 후 ledger와
      비교, 차이 발생 시 alert.
      Verify: reconcile cron 주기 + drift 임계값.
- [ ] **Drift 발견 시 행동:** alert만? 자동매매 일시 중단까지?
      Verify: reconcile 트리거 후 분기 코드. 권장: 일정 임계 초과 시 자동 중단.
- [ ] **수동 매매 끼어도 복구 가능:** HTS/MTS에서 사용자가 수동 매수·매도해도
      다음 reconcile에서 ledger 동기화.
      Verify: reconcile이 단순 비교 alert인지, 자동 ledger 보정인지.
- [ ] **알림 토글:** `alert_on_reconcile_drift` setting 존재 (Phase 42-2).
      Verify: `server/app/schemas.py:UserSettingsIO` + UI 노출.

---

## 6. 자격증명 분리

### 6.1 서버 격리

- [ ] **KIS API key·계좌번호가 서버 schema에 없음.**
      Verify:
      ```powershell
      Select-String -Path platform/server -Pattern "appkey|appsecret|account_number|kis_account" -Recurse
      ```
      결과가 0건이어야 함 (주석·문서 제외).
- [ ] **서버 push payload에 자격증명 없음.** local → server sync에서 잔고·체결
      로그만 전송, raw KIS response 그대로 전달 금지.
      Verify: `local/localapp/sync_*.py`에서 push 직전 payload 검토.
- [ ] **서버 로그에 자격증명 흔적 없음.**
      Verify: server logging middleware가 request body의 민감 필드 마스킹.

### 6.2 로컬 보안

- [ ] **자격증명 평문 저장 안 함.**
      Verify:
      ```powershell
      Select-String -Path platform/local -Pattern "open.*token|open.*credentials|open.*kis_key" -Recurse
      ```
      → 모두 암호화·DPAPI 거쳐야.
- [ ] **Windows DPAPI 또는 사용자 비밀번호 암호화.**
      Verify: 자격증명 저장 모듈 검토.
- [ ] **토큰 파일 권한 (Phase 41-C-2/3):** Windows ACL로 사용자 전용.
      Verify: `local/localapp/`에서 ACL 설정 코드.

---

## 7. 한국 시장 특수성

### 7.1 시간

- [ ] **모든 시각이 KST 기준 (UTC+9).**
      Verify: datetime 처리 위치 grep — `tz=` 또는 `astimezone()` 호출에서 KST
      명시 여부.
- [ ] **정규장 09:00-15:30 인식.**
      Verify: 매매 가능 시간 체크 로직.
- [ ] **시간외 단일가 16:00-18:00.** (사용 시) 단일가 매매 처리.
      Verify: 현재 미사용으로 추정.
- [ ] **휴장일.** 한국거래소 공식 캘린더 사용.
      Verify: `core/data/`에 휴장일 표 또는 KRX 캘린더 API 호출.
- [ ] **임시 휴장 대응.** 갑작스러운 휴장 (예: 코로나 폐장) 시 매매 안전.
      Verify: 데이터 결측 시 동작.

### 7.2 시장 규칙

- [ ] **상한가/하한가 ±30%.** 단, ETF·ETN·신규상장일 등 다른 종목 별도 규칙.
      Verify: 가격 제한 로직 — 있으면 종목 분류별 적용 확인.
- [ ] **시가 단일가 (08:30-09:00).** 시가가 동시호가로 결정됨을 인식.
      Verify: 정상가 가정으로 매매하는지.
- [ ] **종가 단일가 (15:20-15:30).** 종가도 동시호가.
      Verify: 동일.
- [ ] **호가 단위:** 1원/5원/10원/50원/100원/500원/1000원 구간별.
      Verify: `core/quant_core/exec_defaults.py:tick_size` 함수 정확성.

---

## 8. 평가 가이드

각 항목 평가 시:
- **✅ Pass:** 코드·테스트로 확인됨.
- **⚠️ Partial:** 일부만 구현되었거나 검증 어려움. 다음 phase backlog.
- **❌ Fail:** 미구현 또는 결함 발견. Critical 표시 → SUMMARY.md에 surface.

카테고리별 합산:
- 카테고리 점수 = (✅ 수 × 1.0 + ⚠️ 수 × 0.5) / 총 항목 수 × 10
- 도메인 종합 점수 = 7개 카테고리 평균
