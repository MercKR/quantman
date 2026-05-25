# SUMMARY — 풀리뷰 2026-05-24-1430 (REPORT-ONLY)

**스코프:** 풀리뷰 10단계 (Phase 0~9, codex skipped)
**모드:** 진단 전용 — 코드 수정·commit·push 없음
**baseline:** 메모리 + `QUANT_DOMAIN_CHECKLIST.md` + 이전 review-reports + 표준 자본시장법·NFA 2-29
**가이드라인 paste:** 사용자 paste 예정이었으나 미도착 — 19개 항목 매핑 후 paste 도착 시 재대조 가능

---

## 한눈에 보기

| 카테고리 | 값 |
|---|---|
| Critical | 0 |
| High | **4** (FX-1, FX-9, DM-1, DM-2) |
| Medium | 11 |
| Low | 8 |
| 이월 | 4 |
| **종합 점수** | **7.7 / 10** (직전 7.8, −0.1) |
| 자동매매 가이드라인 baseline | **63% ✅ / 76% (⚠ 0.5 가중)** — 12/19 충족 + 3 부분 + 4 미구현 |
| 회귀 | golden test 15 pass ✓ · pytest 1 FAILED (test stale) |
| 자격증명 격리 | ✅ (server 0 매치, local keyring + ACL) |
| 의존성 audit | ✅ (npm + pip server·local 모두 0 vulnerabilities) |

---

## Phase 별 산출

```
2026-05-24-1430/
├── phase0-environment.md      환경·git 상태·Phase 매트릭스
├── phase1-health.md           ruff·tsc·eslint·mypy·pytest·audit 신호
├── phase2-design.md           DESIGN.md 정적 진단 + Phase 49 신규
├── phase3-qa.md               17 시나리오 + Phase 49 path tracing
├── phase4-code-review.md      8 commit + Phase 49 uncommitted diff 리뷰
├── phase5-codex.md            skipped (codex CLI not found)
├── phase6-perf.md             번들 사이즈·Railway·Vercel 정적
├── phase7-security.md         KIS 격리·JWT·audit
├── phase8-quant-domain.md     7 카테고리 + 19 가이드라인 baseline 매핑
├── FINDINGS_REPORT.md         결함 6필드 통합 (✅ 자체점검표 25/25)
└── SUMMARY.md                 본 문서

_sig_*.txt                     명령 출력 원본
```

---

## 5관점 점수 (0-10) — 직전(2108) 대비

| 관점 | 2108 | 1430 | 변화 | 비고 |
|---|---|---|---|---|
| UX / 사용성 | 7.5 | **7.6** | +0.1 | Phase 49 통합 문장 sentence |
| Visual design | 7.5 | **7.6** | +0.1 | sentence-clause·BuyTargetModal 일관성 |
| Engineering | 7.6 | **7.4** | −0.2 | **test 회귀** (FX-1) |
| Product | 8.0 | **8.2** | +0.2 | Phase 48 가이드라인 baseline 71% |
| System trading | 8.5 | **7.9** | −0.6 | **VI·CB·권리락 미구현 surface** |
| **종합** | **7.8** | **7.7** | −0.1 | — |

*점수 회귀는 결함 발견의 결과지 코드 품질 저하 아님 — 직전 cycle은 VI·CB·권리락 영역을 검증 범위에 포함 안 했음. 본 cycle은 자동매매 가이드라인 baseline 19개 항목 매핑으로 더 엄격하게 진단.*

---

## High 결함 4건 — 한 줄 요약

1. **FX-1** `test_in_cycle_flag_reset_on_exception` stale — kill switch 회귀 보호 손상 (1줄 fix)
2. **FX-9** PG/SQLite 분기 마이그레이션 통합 — 직전 cascade incident 재발 방지
3. **DM-1** VI·CB 자동 차단 미구현 — KRX 정보데이터시스템 API 필요 (외부 의존)
4. **DM-2** 권리락·배당락 캘린더 미구현 — `pykrx` 또는 KRX API 필요

---

## 권장 다음 Phase (ROI 순)

### #1 회귀 보호 인프라 — **즉시**
- FX-1 (1분): test 인자 추가
- FX-9 (1시간): PG/SQLite ALTER 헬퍼 통합

### #2 자동매매 가이드라인 baseline 완전 충족 — **외부 API 게이트**
- DM-1 VI·CB
- DM-2 권리락·배당락
- 사용자 결정: KRX API 발급 + `pykrx` 의존성

### #3 코드 health 정리 — **저비용**
- FX-2 ruff `--fix` (자동)
- FX-3·5 mypy type annotation 5건
- SC-1 JWT 길이 fail-fast 검증

---

## 사용자 결정 필요 항목

| 항목 | 결정 |
|---|---|
| Phase 49 uncommitted 변경 commit 시점 | 사용자 |
| FX-11 모달 모드 전환 confirm dialog | 사용자 결정 (UX) |
| FX-12 BuildTab props Context 리팩 | 사용자 결정 (코드 구조) |
| DM-1 KRX API 발급 + fail-open/close 정책 | 사용자 결정 (외부 의존) |
| DM-2 `pykrx` 추가 + ex-date 매수 차단 default | 사용자 결정 |
| DM-3 섹터 분류 표준 (KSIC vs KRX) | 사용자 결정 |
| 가이드라인 paste 본문 도착 | 사용자 액션 — 도착 시 G-XX 매핑 재대조 |

---

## 직전 review 비교 — 회귀 / 신규

### 회귀 (1건)
- **FX-1** `test_in_cycle_flag_reset_on_exception` — Phase 48 시그니처 변경 후 test 미동기. functional 0, 회귀 보호 신호 손상.

### 신규 surface (4건)
- **FX-9** PG/SQLite 마이그레이션 분기 통합 — 직전 cascade incident 원인 일반화
- **DM-1·DM-2** VI·CB·권리락·배당락 — 자동매매 가이드라인 baseline 정밀 매핑 결과
- **SC-1** JWT length 검증 fail-fast 갭

### closed (직전 deferred 중)
- 없음. D-03/04/05/Q-01은 그대로 이월.

### 안정성 신호
- golden test 15 passed (회귀 0)
- npm + pip-audit 0 vulnerabilities
- Railway OOM·cascade 해소 후 production 안정 (Fix #1·A·B 모두 SUCCESS 12:42)

---

## 한계 / 검증 불가

| 항목 | 사유 |
|---|---|
| 17 시나리오 중 9건 KIS 실호출 시나리오 | 자격증명 격리 정책 — 사용자 manual 검증 필요 |
| Phase 49 UI 라이브 동작 (모달·sentence·chip·시장가 토글) | 인증 wall — dev 서버 로그인 안 함 |
| Vercel preview Web Vitals (Lighthouse) | 본 cycle 진단 범위 밖 — 사용자 측정 권장 |
| 가이드라인 paste 본문 1:1 매핑 | paste 미도착 — 19항목 매핑 후 paste 도착 시 재대조 |

---

## 4원칙 자기검토 (cycle 전체)

| 원칙 | 검토 |
|---|---|
| 근본원인 | FX-1·FX-9·SC-1 모두 근본 후보로 surface. silent fallback / except pass 신규 위반 0. ✅ |
| Over-eng | Alembic, Context, Zustand 등 큰 인프라는 모두 사용자 결정 게이트. backlog 분류. ✅ |
| Over-think | 19 baseline 매핑 단일 표, 7 카테고리 단일 표, 5 관점 단일 점수표. 결함 ID는 중복(FX-11=D49-01=QA49-01) 통합 명시. ✅ |
| 검증된 해결책 | 모든 결함은 명령 출력·grep·코드 inspection 근거. 추측 단정 0. **인증 wall + KIS 실호출 검증 불가 명시**. ✅ |

---

**상태:** ✅ 정상 종료 (REPORT-ONLY, 코드 수정·commit·push 0건)

**다음 액션:** 사용자 검토 → 권장 Phase #1 (FX-1 즉시 fix + FX-9 통합) 수정 cycle 진행 합의 시 별도 task.
