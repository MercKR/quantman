# Phase 0 — 환경 점검

**생성:** 2026-05-24 14:30 KST
**모드:** REPORT-ONLY (진단 전용, 코드 수정 금지)
**트리거:** 사용자 요청 — "프로젝트 총체적 리뷰 / 자동매매 best practice 가이드라인 기준"
**가이드라인 문서:** 사용자가 paste 예정이라 했으나 미도착 — 본 cycle은 메모리 + `QUANT_DOMAIN_CHECKLIST.md` + 이전 SUMMARY + 표준 best practice를 baseline으로 진행. paste 도착 시 별도 gap 보강.

---

## 1. Git 상태

- 브랜치: `main`
- Uncommitted (Phase 49 — 매수 UX 통합 작업, 직전 cycle):
  - `web/src/components/ConditionBuilder.tsx` — OperandChip → SymbolChip+IndicatorChip+RightOperand 분리
  - `web/src/pages/Backtest.tsx` — 매수후보 모달화 + 통합 문장 sentence + BuyPricePanel
  - `web/src/pages/Strategies.tsx` — "매수 대상" → "매수후보" 라벨
  - `web/src/types.ts` — `ExecutionPolicy.use_limit` 필드 추가
  - `web/src/index.css` — sentence-clause·buy-target-buttons·price-mode-* CSS
- Untracked: `docs/incidents/` (Railway OOM hand-off 문서)

**판정:** 직전 cycle 작업이 commit 전 상태. 본 리뷰는 *현재 워킹트리* 기준 진단(=Phase 49 변경 포함). 결함 발견 시 별도 PR로 처리 권장.

## 2. 최근 commit 흐름 (10건)

```
bd3571f fix(db): PostgreSQL 분기에 P1-C/D 컬럼 ALTER 누락 보정 (Railway cascade root cause)
a473126 fix(preview): per-user session 격리 — InFailedSqlTransaction cascade 차단
2b7e173 fix(memory): fetch_korean_stocks results dict 제거 (Railway OOM root cause)
3245e87 feat(compliance): P1 5건 + P2 2건 — 자동매매 가이드라인 후속 보강
7c4bac3 feat(compliance): 자동매매 가이드라인 P0 5건 — disclaimer·차단·throttle
a968f6a feat(sizing): 분할매수 — N차 분할 + 평단 가중평균 + Monitor 차수 표시
7c887d8 feat(sizing): 매수액 수정자 — 조건 충족 시 ×N 적용
ec1ffeb feat(sizing): 매수액 4지 모드 통합 — 정률·정액·균등·ATR
6a32700 refactor(web/monitor): 섹션 순서 — 보유→전략→부수정보→footer 정렬
f98cc71 refactor(web/monitor): 전략별 카드 그리드로 P&L·매매 예정·보유 통합
```

Phase 47(사이징) + Phase 48(자동매매 가이드라인 P0/P1/P2 compliance) + Phase 49(매수 UX 통합)이 직전 흐름.

## 3. 외부 환경

| 항목 | 상태 | 비고 |
|---|---|---|
| OS / Shell | Windows 11 / PowerShell + Bash | cp949 encoding 주의 — 한글 출력은 UTF-8 명시 |
| Python | 3.11+ (확인 후 갱신) | server/local 공통 |
| Bun | 설치됨 (`bun run dev` 가용) | web 빌드 |
| Vite dev server | 5173 LISTENING + 5174 (현재 cycle vite) | Phase 49 검증 때부터 가동 중 |
| codex CLI | **NOT FOUND** | Phase 5 자동 skip |
| golden_backtest.py / baseline.json | 존재 (`platform/tests/`) | Phase 8 회귀 가능 |
| 이전 review-reports | `2026-05-23-2108/` (직전) · 그 외 3건 | 회귀 비교 base |
| Railway production | 12:42 deployment SUCCESS (Fix A+B 후) | Phase 6에서 라이브 신호 활용 가능 |
| Vercel preview | 별도 확인 필요 | Phase 6 |

## 4. Phase 실행 가능성 매트릭스

| Phase | 가능? | 비고 |
|---|---|---|
| 0 환경 | ✅ | 본 문서 |
| 1 health (lint·type·test) | ✅ | ruff·mypy·tsc·eslint·pytest 모두 실행 가능 |
| 2 design-review | ⚠️ | dev 서버 가동 중. 인증 우회 안 함 → 로그인 후 페이지별 진단은 사용자 manual 또는 인증 토큰 필요. **대안:** 코드/CSS/컴포넌트 정적 진단으로 진행 |
| 3 qa (시나리오) | ⚠️ | Phase 2와 동일 — 인증 wall. 시나리오별 코드 path tracing으로 진행 |
| 4 code-review | ✅ | diff 기반 review |
| 5 codex | ⏭ skipped | codex CLI 없음 |
| 6 perf | ⚠️ | Vercel/Railway 라이브 metric — Bash로 curl·헤더만 수집 가능. 본격 Web Vitals는 Lighthouse 없으면 제한 |
| 7 security | ✅ | grep·bun audit·pip-audit |
| 8 quant domain | ✅ | QUANT_DOMAIN_CHECKLIST + golden test |
| 9 summary | ✅ | 통합 |

## 5. 의사결정 — paste 미도착 시 진행

사용자 직전 응답: "이번 턴에 다시 paste" 선택 → stop hook 두 번째 발생 시점까지 paste 미도착. 두 번째 stop hook은 "체계적 작업" 강한 신호이므로 **paste 없이 진행** 결정:

- baseline = (a) `platform/docs/QUANT_DOMAIN_CHECKLIST.md` (b) `platform/CLAUDE.md` 4원칙 (c) `platform/DESIGN.md` (d) 메모리에 정리된 Phase 48 12 disclaimer/safeguards (e) 표준 자본시장법·NFA 2-29·MiFID II 등 공개 기준 (f) 직전 `2026-05-23-2108/SUMMARY.md` 회귀 비교
- paste 도착 시 별도 `FINDINGS_REPORT_GUIDELINE_GAP.md`로 보강

## 6. 후속 산출물

```
2026-05-24-1430/
├── phase0-environment.md   ← 본 문서
├── phase1-health.md
├── phase2-design.md
├── phase3-qa.md
├── phase4-code-review.md
├── phase5-codex.md   (skipped 한 줄)
├── phase6-perf.md
├── phase7-security.md
├── phase8-quant-domain.md
├── FINDINGS_REPORT.md   ← 모든 결함 6필드 통합
└── SUMMARY.md
```
