# Phase 2 — Visual & UX Design (정적 진단)

**제약:** 인증 wall — 로그인 없이 라이브 페이지 진단 불가. dev 서버는 5173에서 가동 중이나 페이지 단위 snapshot은 인증된 사용자만. 본 cycle은 **코드/CSS/컴포넌트 정적 진단** + Phase 49 변경 부분 집중.

## 1. 페이지별 점수 (0-10) — 직전(2108) 대비

| 페이지 | 2108 | 1430 | 변화 | 근거 |
|---|---|---|---|---|
| Login | 8 | 8 | 0 | 변경 없음 |
| Pair | 8 | 8 | 0 | 변경 없음 |
| Dashboard | 7 | 7 | 0 | D-03 (페이지 단위 empty state) 미해결 |
| Monitor | 7 | 7 | 0 | 변경 없음 |
| Strategies | 8 | 8 | 0 | "매수 대상" → "매수후보" 라벨 일관성 갱신 |
| **Backtest** | 7 | **7.5** | +0.5 | Phase 49 sentence + 모달 — 가독성↑. 일부 신규 결함 |
| Settings | 8 | 8 | 0 | 변경 없음 |
| **종합** | **7.5** | **7.6** | +0.1 | Phase 49 UX 통합으로 미세 향상 |

## 2. Phase 49 신규 진단

### 검증 통과

| 항목 | 결과 |
|---|---|
| `BuyTargetModal` 모달 패턴 (modal-overlay·head·body·foot) | 기존 PromoteModal 패턴 재사용 ✓ |
| `BuyTargetModal` 한 모달 + 내부 탭 (`detail-tabs` 재사용) | DESIGN.md 패턴 일관 ✓ |
| `BuyTargetPanel` 큰 버튼 2개 (큰 패딩, hover, .on 상태) | accent token 사용, 모바일 grid → 1열 wrap ✓ |
| `BuyPricePanel` 시장가/지정가 라디오 카드 | accent-soft 활성, warn-box 패턴 ✓ |
| `sentence-clause` 4 절 (조건·가격·수량·종목) | 점선 구분 + ① ② ③ ④ 번호. visual hierarchy 명확 ✓ |
| `sentence-advanced` 펼침형 details/summary | 화살표 토글 (▸/▾) custom marker ✓ |
| `SymbolChip`/`IndicatorChip` 좌·우 공용 (compatGroup) | 우변 종목·지표 분리 ✓ |
| `RightOperand` 숫자↔지표 토글 (`.kind-toggle`) | ghost-chip 11px 패딩 ✓ |
| 종목·지표 chip의 popover dismiss (usePopoverDismiss) | 기존 패턴 재사용 ✓ |
| `.sentence` `flex-wrap: wrap` (index.css:142) | chip 다중·multi-line wrap 정상 ✓ |
| tsc·eslint 통과 | tsc 0, eslint Phase 49 신규 위반 0 ✓ |

### 신규 결함

**D49-01 [Medium]** `BuyTargetModal` — 적용/취소 분리 부재
- 위치: `web/src/pages/Backtest.tsx` BuyTargetModal footer
- 현재: footer에 "적용" 버튼 하나만, 클릭 시 onClose. 모달 안 변경은 onChange로 부모 state에 **실시간 commit**.
- 영향: 사용자가 종목 잘못 선택 → 모달 닫고 다시 열어 수정. 취소 의도 모달이 없음.
- 4원칙 비교: PR-3 (단순한 쪽 선택, 임시 state 사용 안 함)에 부합 — 정당화 가능. 그러나 사용자 멘탈모델은 "모달 = commit/cancel 분리"에 익숙. UX 마찰 가능성.
- 결정 필요: (a) 현재 단순 유지 (b) 임시 state + apply/cancel 분리.

**D49-02 [Medium]** `BuyPricePanel` — KIS 해외 종목은 시장가 unsupported 안내 부재
- 위치: `BuyPricePanel` (Backtest.tsx)
- KIS 해외 분기(`kis_broker.py:447`)는 `ord_dvsn 무시 (해외는 지정가만 지원)` — broker가 silently limit으로 강제 변환.
- 영향: 사용자가 미국 종목 + 시장가 선택 → UI는 "시장가"인데 실제 KIS는 limit 발주. **사용자 멘탈모델 불일치**.
- 다만: 본 플랫폼은 현재 한국 시장 중심(`platform/docs/US_TRADING_DESIGN.md`는 설계만, 라이브 미구현). 한국 종목만 매매하면 무영향.
- 결정 필요: 해외 매매 라이브 활성 시점에 UI 분기 (해외 + 시장가 시 disable 또는 warning).

**D49-03 [Low]** `RightOperand.toIndicator` — 호환 데이터 없을 시 무동작 (사용자 피드백 부재)
- 위치: `web/src/components/ConditionBuilder.tsx` RightOperand (~line 372~)
- `if (!sym) return;` — 호환 종목·지표가 전혀 없으면 클릭해도 변화 없음. 사용자에게 안 변하는 이유 안 알려줌.
- 영향: 매우 드문 케이스 (대부분 호환 종목 존재). toast/disabled 처리로 명확화 가능.

**D49-04 [Low]** `sentence-clause` "④ 매수후보를 매수한다" 절
- 현재: 정보 표시만 (위 "1. 매수후보"에서 선정된 종목 — read-only)
- screener 모드일 때 "(자동 선택 모드)" 추가 표시
- 결함은 아님. 다만 ④번 절이 정보 밀도 낮음. 일관성을 위해 종목 chip pill을 직접 표시하는 옵션 검토.

## 3. 미해결 (직전 review 이월)

| ID | 위치 | 상태 |
|---|---|---|
| D-03 | `Dashboard.tsx` 페이지 단위 empty/error 통합 부재 | 이월 (구조적, 사용자 결정) |
| D-04 | `Backtest.tsx` CapitalInput `useEffect → setState` (set-state-in-effect) | 이월 |
| D-05 | `SymbolPicker.tsx`·`auth.tsx`·`mode.tsx` react-refresh/only-export-components | 이월 |

## 4. 4상태 정의 (DESIGN.md 패턴)

이전 cycle 결과 그대로 유효. Phase 49 변경은 **빈/로딩/에러 상태 회귀 없음**.

- `BuyTargetModal` 안의 picker는 기존 컴포넌트 재사용 → 4상태 처리 그대로 상속.
- `sentence-clause`의 각 절은 정보 표시 위주. error 상태 별도 처리 안 함 (조건이 비어있으면 ConditionBuilder가 starter 조건 1개 자동 추가).

## 5. 4원칙 자기검토 (Phase 2)

| 원칙 | 자기검토 |
|---|---|
| 근본원인 | Phase 49는 "통합 문장" 메타포로 사용자 멘탈모델 향상 — 기존 4 분리 패널의 인지 부하 줄임. 근본 ✅ |
| Over-eng | sentence-clause 컴포넌트 신규 4개 (BuyTargetModal·BuyPricePanel + 분리된 chip). 모두 sentence 메타포 안에서 단일 책임 — 정당. CSS 클래스 추가도 한정적 ✅ |
| Over-think | 모달 안 commit/cancel 미분리는 단순 우선 결정 — D49-01로 surface (사용자 결정) ✅ |
| 검증된 해결책 | tsc·eslint 통과 + 컴포넌트 dynamic import 검증. UI 동작은 인증 wall로 미검증 → 이 한계 명시 ✅ |

## 6. Phase 9 전달

- D49-01 (적용/취소 분리) — 사용자 결정
- D49-02 (해외 시장가 안내) — 해외 라이브 활성 시점까지 deferred
- D49-03 (toIndicator 피드백) — Low backlog
- D-03/D-04/D-05 — 이월
