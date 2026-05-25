# Phase 3 — 사용자 플로우 QA (정적 코드 path tracing)

**제약:** 인증 wall — 17 시나리오 중 KIS 자격증명 의존 ~9건은 검증 불가. 본 cycle은 (a) 직전(2108) 결과 회귀 확인 + (b) Phase 49 신규 플로우 path tracing.

## 1. 17개 시나리오 — 회귀 + Phase 49 영향

| # | 시나리오 | 2108 | 1430 | 변화 |
|---|---|---|---|---|
| 1 | 신규 가입 → 로그인 → Google OAuth | ⚠️ 검증불가 | ⚠️ 검증불가 | 0 |
| 2 | 디바이스 페어링 | ⚠️ 검증불가 | ⚠️ 검증불가 | 0 |
| 3 | 첫 전략 생성 (ConditionBuilder) | ✅ | ✅* | **Phase 49 변경 — chip 분리/RightOperand** |
| 4 | 백테스트 실행→결과→저장 | ✅ | ✅ | sentence 레이아웃 통합 |
| 5 | 모의→자동매매 시작 | ⚠️ KIS 필요 | ⚠️ | 0 |
| 6 | Dashboard·Monitor 모니터링 | ✅ | ✅ | 0 |
| 7 | Settings 위험 한도 | ✅ | ✅ | 0 |
| 8 | 페어링 해제 → snapshot stale 차단 | ✅ | ✅ | preview cron 격리(Fix A) 이후 추가 안정 |
| 9 | 로그아웃→재로그인→상태 복원 | ⚠️ | ⚠️ | 0 |
| 10 | KIS 토큰 만료 재발급 | ⚠️ | ⚠️ | 0 |
| 11 | preview 어제종가 stale 차단 (S-05) | ✅ | ✅ | 회귀 없음 |
| 12 | killswitch tier 1+2 (Q5 cycle lock) | ⚠️ | ⚠️→**FX-1** | test stale (Phase 1) — **회귀 보호 손상** |
| 13 | 시세 WS fallback (Q3) | ⚠️ | ⚠️ | 0 |
| 14 | 캘린더 자동갱신 | ✅ | ✅ | test_market_calendar 16/16 pass |
| 15 | DAY 단일 (Q7) | ⚠️ | ⚠️ | 0 |
| 16 | pct_cash 단일종목 한도 | ✅ | ✅ | 0 |
| 17 | WS 체결통보 dedup | ✅ | ✅ | 0 |

*\#3 Phase 49 변경 path:* `MultiSymbolPicker` 또는 `SymbolPicker`를 **BuyTargetModal 안에서 호출**. 모달 닫기 = state commit (모달 내 모든 변경은 실시간 부모 state 반영). ConditionBuilder의 좌·우 chip은 별도 popover.

## 2. Phase 49 신규 시나리오 검증 (정적)

### 18. 매수후보 모달 — 수동 선택

코드 path:
1. `Backtest.tsx` BuildTab → `BuyTargetPanel` 렌더 → 큰 버튼 "수동 선택" 클릭
2. `setModalOpen("manual")` → `BuyTargetModal` 마운트 (initialTab="manual")
3. 모달 head/탭/body 렌더 — MultiSymbolPicker, screenerLimit input
4. 종목 다중 선택 시 `setTradeSymbol("005930,000660,...")` 즉시 부모 갱신
5. 모달 닫기 → 요약 라인 "삼성전자 외 N종목 · 최대 N개 동시 보유" 표시

검증 결과: ✅ tsc·eslint 통과. 인증된 UI 동작 미검증.

### 19. 매수후보 모달 — 자동 선택 + 리밸런싱

코드 path:
1. "자동 선택" 큰 버튼 → modal tab="screener"
2. `SymbolPicker` (lockMode="screener") + `screenerSpec` + 리밸런싱 체크박스
3. setTradeSymbol("screener:marcap_top") 또는 "screener:custom"
4. 리밸런싱 enable → rebalance.enabled = true, 주기 select

검증 결과: ✅. **잠재 결함:** `selectMode`/`switchTab` 시 `setTradeSymbol("")` 호출. 사용자가 자동→수동 전환 시 자동 spec 잃음. 의도된 동작이나 UX confirm 없음.

### 20. 통합 문장 ② 가격 절 — 시장가/지정가 토글

코드 path:
1. `BuyPricePanel` 라디오 카드 클릭 → setUseLimit(true|false)
2. useLimit=true: tolerance input + 발주가 계산 hint
3. useLimit=false: warn-box "시초가 갭에 무방비" 경고

검증 결과: ✅ tsc 통과. 백엔드는 `trader.py:480 use_limit = bool(policy["use_limit"])` 이미 분기.

**잠재 결함 (D49-02):** 미국 종목 선택 시 시장가는 KIS 해외 layer가 silently limit 변환. UI 부정합. — Medium.

### 21. RightOperand 숫자↔지표 토글

코드 path:
1. 우변 kind=constant → 인라인 input + "↔ 지표" 버튼
2. 버튼 클릭 → toIndicator(): 호환 종목·지표 자동 swap. 호환 없으면 무동작.
3. 우변 kind=indicator → SymbolChip + IndicatorChip + "↔ 숫자" 버튼

검증 결과: ✅. **잠재 결함 (D49-03):** 호환 없을 때 무동작 — 사용자 피드백 부재. Low.

### 22. ConditionBuilder 좌·우 chip 분리 (compatGroup)

코드 path:
1. 좌변 종목·지표 변경 → leftGroup 재계산
2. 우변 indicator·history kind이면 SymbolChip + IndicatorChip 두 popover
3. 우변 종목 클릭 시 compatGroup 호환되는 종목만 visible
4. 우변 종목 변경 시 호환 indicator로 자동 swap (`pickSymbol`)

검증 결과: ✅. compatGroup="other"면 모든 종목·지표 통과 (호환 그룹 정의 안 된 지표는 폴백).

## 3. 새로 발견 / 회귀

### 신규 결함

**QA49-01 [Low]** `BuyTargetModal switchTab` — 모드 전환 시 종목 무경고 초기화
- 위치: `Backtest.tsx` BuyTargetModal `switchTab`
- 사용자가 수동→자동 (또는 반대) 클릭 시 `setTradeSymbol("")` — confirm 없이 기존 선택 손실.
- 영향: 의도된 동작이나 작업 중 실수 클릭 시 손실. confirm dialog 또는 warning 권장.

**FX-1 ↔ QA-12 cross-reference**
- killswitch tier 1+2의 회귀 test가 stale (Phase 1 FX-1). QA-12 시나리오의 자동 검증 신호 상실.
- 검증 대안: test 자체 수정 (간단, krx_status={} 인자 추가) 후 재실행.

## 4. 4상태 정의 — Phase 49 영향

| 페이지/패널 | 빈상태 | 로딩 | 에러 | normal |
|---|---|---|---|---|
| Backtest > 1. 매수후보 (panel) | ✅ summary "(아직 선정된 매수후보가 없습니다 — 위 버튼으로 선택)" | n/a | n/a | ✅ |
| Backtest > 2. 매수 조건 sentence | ✅ ConditionBuilder가 빈 시 starter 조건 1개 | n/a | n/a | ✅ |
| Backtest > BuyTargetModal | ✅ 종목 선택 없으면 "0종목" | hasMaster=false 경고 | n/a | ✅ |
| Backtest > BuyPricePanel | n/a (항상 모드 선택됨) | n/a | n/a | ✅ |

## 5. 4원칙 자기검토 (Phase 3)

| 원칙 | 자기검토 |
|---|---|
| 근본원인 | Phase 49 변경은 매수 UX 인지 부하 감소 — 멘탈모델 명확화. 근본 ✅ |
| Over-eng | sentence-clause·BuyTargetModal·BuyPricePanel·RightOperand — 모두 사용자 요청 4가지 (모달·문장·chip 분리·시장가)와 1:1 매핑. 부차 표면 없음 ✅ |
| Over-think | switchTab의 setTradeSymbol("") 즉시 초기화는 단순 — confirm 미도입(D49-01과 일관). 사용자 결정 사항 surface ✅ |
| 검증된 해결책 | tsc·eslint·dynamic import 통과 + Phase 49 path 정적 trace 완료. **인증 wall로 라이브 동작 검증 못함을 명시** ✅ |

## 6. Phase 9 전달

- **FX-1** (test_killswitch_intraday stale) — High, 자동매매 안전성 회귀 보호 손상
- **QA49-01** (switchTab 무경고 초기화) — Low
- 회귀: 0건. 직전 cycle closed 항목 모두 유지.
