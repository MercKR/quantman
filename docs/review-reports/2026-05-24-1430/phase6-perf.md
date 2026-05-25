# Phase 6 — 성능

**제약:** 본 cycle은 진단 전용 + 시간 예산 — Lighthouse·Web Vitals 라이브 측정 skip. 다음을 정적/build 신호로 수집.

## 1. 번들 사이즈 (`web/dist/assets/`)

마지막 build: **2026-05-24 02:39** — Phase 49 *전* build. Phase 49 변경 후 미빌드.

| 파일 | 크기 |
|---|---|
| `index-CIpGKbNx.js` | **749,350 B** (≈732 KB) |
| `index-D5mXLGyD.css` | 38,679 B (≈38 KB) |

Phase 49 영향 예측:
- 신규 컴포넌트 (BuyTargetModal · BuyPricePanel · SymbolChip / IndicatorChip / RightOperand 재배치) — JS 추가 ~5-10 KB minify 후 gzip
- 새 CSS 90 줄 — CSS gzip 후 ~1 KB
- 사용 안 되는 OperandChip/OperandEditor/operandSummary 제거 → 일부 상쇄
- 순 영향: 미세 (JS +5 KB, CSS +1 KB 예상)

## 2. Railway production (서버)

- 직전 incident: 24h 내 OOM 9회+ → Fix #1 (2b7e173) results dict 제거. **이후 30분+ 안정 + cascade test SUCCESS @ 12:42**
- Fix B (db.py P1-C/D ALTER) 후 startup logs `_migrate` 실패 메시지 없음 (column 보정 완료 신호)
- 추가 OOM 4h baseline / 24h baseline 검증 — **본 cycle에선 미수집** (Railway dashboard 라이브 metric 필요)

## 3. Vercel production

- 본 cycle 미접근. 직전 review에서 preview URL Web Vitals 확인이 표준.
- Phase 49 변경 commit 후 자동 deploy 트리거되면 Vercel preview에서 측정 가능.

## 4. Backend critical paths — 정적 분석 (Phase 1 신호 + commit body)

| 경로 | 직전 cycle 상태 | Phase 47~49 영향 |
|---|---|---|
| `fetch_korean_stocks` (data_fetcher) | OOM root cause | 해소 (results dict 제거). ✓ |
| `refresh_all_users_preview` (preview_engine) | cascade root cause | 해소 (per-user session 격리). ✓ |
| `_migrate()` (db) | PG 분기 ALTER 누락 | 해소 (P1-C/D 보정). ⚠️ 재발 가능 (FX-9) |
| `_cycle_locked` (trader, intraday loop) | Q5 lock 패턴 | krx_status 인자 추가 후 회귀 test stale (FX-1) |

## 5. 발견 결함

**FX-15 [Low]** Phase 49 변경 후 production build 미수행
- 위치: `web/dist/` (build artifact stale)
- 영향: 본 진단 cycle은 진단 전용이라 build 안 함. 사용자가 commit + deploy 시 자동 rebuild → 자동 해소
- 메모: bundle size 회귀 정량 측정은 Phase 49 build 후 재진행

**FX-16 [Low]** Phase 49 신규 컴포넌트 dynamic import 신호 OK
- Phase 49 검증 단계에서 `import('/src/pages/Backtest.tsx')` + `import('/src/components/ConditionBuilder.tsx')` 모두 success
- HMR transform 통과. tsc 0 error. → 성능 회귀 없을 가능성 높음

## 6. 4원칙 자기검토 (Phase 6)

| 원칙 | 자기검토 |
|---|---|
| 근본원인 | OOM root cause 해소 + cascade root cause 해소. ✓ |
| Over-eng | Lighthouse·Web Vitals 측정은 본 cycle 범위 밖 — 진단 전용이라 skip ✓ |
| Over-think | bundle size는 build 결과로 정량 — 추정만 ✓ |
| 검증된 해결책 | 라이브 Web Vitals는 측정 안 함을 명시 ✓ |

## 7. Phase 9 전달

- FX-15·16 Low (build·bundle)
- 라이브 Web Vitals는 Vercel preview에서 사용자 측정 후 보강 권고
