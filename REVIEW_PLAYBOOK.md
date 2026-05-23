# 전체 리뷰 플레이북

이 문서는 사용자가 `/풀리뷰` 또는 `/full-review` 트리거를 쓸 때 Claude가 따라야
할 **10단계 자동 실행 스크립트**다. 단계별 입력·출력·skill·시간 예산·실패 처리가
명시되어 있다. 중간에 사람이 개입할 필요가 없도록 설계됐다.

---

## 0. 트리거 인식

다음 문구 중 하나가 사용자 메시지에 등장하면 이 playbook을 시작한다:

- `/풀리뷰`, `/full-review`, `풀리뷰 실행`, `full review run`

다른 작업 중이었다면 먼저 그 작업을 마무리하거나 사용자에게 중단 확인을 받는다.

---

## 1. 5개 관점 → Phase 매핑

| 관점 | 어디서 검증되는가 |
|---|---|
| **UX / 사용성** | Phase 2 (design-review) + Phase 3 (qa) |
| **Visual design** | Phase 2 (design-review, DESIGN.md 기준) |
| **Engineering** | Phase 1 (health) + Phase 4 (review) + Phase 5 (codex) + Phase 6 (benchmark) |
| **Product** | Phase 9 통합 단계에서 Phase 8 결과와 종합 평가 |
| **System Trading 도메인** | Phase 7 (cso 보안) + Phase 8 (QUANT_DOMAIN_CHECKLIST + golden tests) |

---

## 2. 사전 조건

1. 작업 디렉토리: `platform/` (git repo root)
2. 환경: Windows PowerShell + bun + python 3.11+ + git
3. 옵션: `codex` CLI (Phase 5에서 사용, 없으면 자동 skip)
4. 사용자 입력 불필요 — 모든 결정은 6원칙으로 자동:
   - P1 완전성 우선 · P2 blast radius 안에서 expand · P3 단순한 쪽 · P4 중복 거부 · P5 명시적 > 영리함 · P6 행동 편향

---

## 3. 실행 흐름

### Phase 0 — 환경 점검 (5분)

**할 일:**
1. `git status` 확인. uncommitted 변경 있으면 사용자에게 stash/commit 묻고 진행.
2. `cd platform/web; bun run dev` 백그라운드 실행 (Phase 2·3 필요).
3. 결과 폴더 생성: `platform/docs/review-reports/$(date +%Y-%m-%d-%H%M)/`
4. `codex --version` 시도 → 성공 시 Phase 5 실행, 실패 시 Phase 5 skip 표시.
5. `tests/golden_backtest.py` baseline 파일 존재 여부 확인. 없으면 Phase 8에서
   생성 모드로 동작.

**출력:** `phase0-environment.md` — 환경 정보·skip 여부·dev 서버 URL.

**실패 시:** dev 서버 안 뜨면 STOP하고 사용자에게 보고. 그 외 환경 문제는
복구 시도 후 계속.

---

### Phase 1 — 코드 베이스라인 (10분)

**할 일:**
1. `/health` 실행 (lint·type·test·dead code 통합 점수).
2. server 측: `cd platform/server; ruff check . ; mypy app` 수동 실행.
3. web 측: `cd platform/web; bun run tsc --noEmit ; bun run lint` 수동 실행.
4. 점수와 결함 요약을 phase1에 기록. 새로 발견된 critical 결함은
   `phase9-summary` 우선순위 매트릭스에 입력.

**출력:** `phase1-health.md` — 영역별 점수표, top 결함 10개, 추세 (이전 리뷰
   대비 — `review-reports/` 안의 직전 폴더와 비교).

---

### Phase 2 — Visual & UX Design (30분)

**할 일:**
1. `/design-review` 실행.
   - 기준: `platform/DESIGN.md`
   - 대상: 웹앱 7개 페이지 (Login, Pair, Dashboard, Monitor, Strategies, Backtest, Settings)
   - 체크: hierarchy, 일관성, spacing, typography, color tokens 준수, AI slop
     패턴, 빈 상태·로딩·에러 4가지 상태 정의 완전성, 모바일 반응형, 접근성
     (키보드 nav, 색맹 친화, focus indicator)
2. **즉시 수정 가능한 cosmetic은 그 자리에서 PR.** 사용자 승인 없이 commit
   가능 (color token 교체, spacing 조정, 누락된 빈 상태 추가 등).
3. **구조적 변경은 phase9에 deferred로 기록.** 페이지 재구성·새 컴포넌트 도입
   등은 사용자 결정 필요.

**출력:** `phase2-design.md` — 페이지별 점수 (0-10), 발견 결함 카테고리별,
   즉시 수정 commit hash 목록, deferred 목록.

**보조:** 페이지별 before/after screenshot은 `phase2-screenshots/` 하위에.

---

### Phase 3 — 사용자 플로우 (30분)

**할 일:**
1. `/qa` Standard tier 실행 (critical + high + medium).
2. 17개 시나리오 커버:
   - 신규 가입 → 로그인 → Google OAuth
   - 디바이스 페어링 (코드 입력 + 승인)
   - 첫 전략 생성 (ConditionBuilder)
   - 백테스트 실행 → 결과 확인 → 저장
   - 모의투자 모드 전환 → 자동매매 시작
   - 실시간 모니터링 (Dashboard·Monitor)
   - 위험 한도 설정 (Settings)
   - 페어링 해제 → snapshot stale 차단 확인 (Phase 42-3)
   - 로그아웃 → 재로그인 → 상태 복원
3. 발견 버그는 root cause 분석 후 수정. 수정 후 재검증 패스.

**출력:** `phase3-qa.md` — 시나리오별 pass/fail, 발견 버그 목록 (심각도·재현
   단계·수정 commit), QA 점수.

---

### Phase 4 — 코드 변경 리뷰 (15분)

**할 일:**
1. `/review` 실행 (직전 리뷰 이후 또는 main 기준 diff).
2. 체크: SQL 안전성, LLM trust boundary (있다면), 조건부 부작용, race condition,
   error handling 누락, dead code, naming consistency.

**출력:** `phase4-code-review.md` — diff 통계, 카테고리별 finding, 권장 수정.

---

### Phase 5 — Codex 독립 시선 (15분, 옵션)

**조건:** Phase 0에서 codex available 확인된 경우만.

**할 일:**
1. `codex review` 또는 `/codex review` 실행 (GPT 모델로 같은 diff 독립 리뷰).
2. Claude review와 비교 → consensus / disagreement 표 작성.
3. disagreement는 phase9에 surfacing.

**출력:** `phase5-codex.md` — Codex finding 목록, consensus table.

**Skip 시:** `phase5-codex.md`에 "skipped: codex CLI 없음" 한 줄 기록.

---

### Phase 6 — 성능 (15분)

**할 일:**
1. `/benchmark` 실행. 대상:
   - Production URL (Vercel)
   - 주요 페이지 5개: Dashboard, Monitor, Backtest, Strategies, Settings
2. Core Web Vitals (LCP·CLS·INP), bundle size, network waterfall 수집.
3. 직전 baseline 대비 회귀 확인. 회귀 >10% 시 critical 표시.

**출력:** `phase6-perf.md` — 페이지별 metric, 회귀 표, 권장 최적화.

---

### Phase 7 — 보안 (30분)

**할 일:**
1. `/cso` daily tier 실행.
2. 추가 grep 검증 (이 프로젝트 특수):
   ```powershell
   # 서버 코드에 KIS 자격증명 흔적 없어야
   Select-String -Path platform/server -Pattern "appkey|appsecret|account_number" -Recurse
   # 로컬앱 토큰이 평문 저장 안 되어야
   Select-String -Path platform/local -Pattern "open.*token.*['\"]w['\"]" -Recurse
   ```
3. 종속성: `bun audit`, `pip-audit -r platform/server/requirements.txt`,
   `pip-audit -r platform/local/requirements.txt`.

**출력:** `phase7-security.md` — vulnerability 목록 (CVSS·영향·수정),
   자격증명 격리 검증 결과, supply chain risk.

---

### Phase 8 — System Trading 도메인 (45분)

**할 일:**
1. `platform/docs/QUANT_DOMAIN_CHECKLIST.md` 열어 7개 카테고리 항목별 검증:
   - 백테스트 정확성 (look-ahead, 슬리피지, 배당, 분할)
   - 시그널 → 주문 idempotency
   - 모의 ↔ 실전 일관성
   - 리스크 관리 (kill switch, drawdown, 단일 종목 한도)
   - KIS ↔ ledger 정합성
   - 자격증명 분리
   - 한국 시장 특수성 (시간, 휴장, 호가)
2. **백테스트 골든 테스트 실행:**
   ```powershell
   cd platform; pytest tests/golden_backtest.py -v
   ```
   - baseline 없으면 생성 모드 (첫 실행은 baseline commit 권유).
   - baseline 있으면 회귀 검증. 차이 발생 시 tolerance 내인지 확인.
3. 항목별 검증 결과를 ✅/⚠️/❌로 기록. ❌는 phase9에 critical로.

**출력:** `phase8-quant-domain.md` — 체크리스트 항목별 결과, golden test 결과,
   발견된 도메인 결함.

---

### Phase 9 — 통합 SUMMARY (10분)

**할 일:**
1. Phase 1~8 결과 종합. `SUMMARY.md` 작성.
2. 우선순위 매트릭스:

| 심각도 | 정의 | 권장 대응 |
|---|---|---|
| Critical | 자산 손실·보안 침해·서비스 다운 직접 원인 | 즉시 fix (별도 PR) |
| High | 사용자 신뢰 손상·핵심 기능 부분 고장 | 다음 phase 안에 처리 |
| Medium | UX 마찰·성능 저하·코드 품질 | backlog 우선순위 상위 |
| Low | 코스메틱·미세 개선 | backlog |

3. 5개 관점별 0-10 점수 + 직전 리뷰 대비 변화.
4. 권장 다음 phase 3개 (가장 ROI 큰 작업).
5. Codex disagreement·user challenge가 있으면 별도 섹션으로 surface (둘 다
   "사용자가 결정해야 함" 표시).

**출력:** `SUMMARY.md`

---

## 4. 산출물 구조

```
platform/docs/review-reports/2026-05-22-1400/
├── SUMMARY.md
├── phase0-environment.md
├── phase1-health.md
├── phase2-design.md
├── phase2-screenshots/
├── phase3-qa.md
├── phase4-code-review.md
├── phase5-codex.md           (skip 시에도 한 줄 남김)
├── phase6-perf.md
├── phase7-security.md
└── phase8-quant-domain.md
```

직전 리뷰 폴더는 `phase1` (health)·`phase6` (perf)에서 회귀 비교 base로 사용.

---

## 5. 중단·재개

- 사용자 STOP/PAUSE 시 현재 phase까지 완료하고 멈춤. SUMMARY.md에 "[INCOMPLETE
  — paused at Phase N]" 표시.
- 재개는 `/풀리뷰 resume` → 마지막 SUMMARY.md 읽고 미완료 phase부터.

---

## 6. 시간 예산

| Phase | 예산 | 누적 |
|---|---|---|
| 0 환경 | 5분 | 5분 |
| 1 health | 10분 | 15분 |
| 2 design | 30분 | 45분 |
| 3 qa | 30분 | 1h 15분 |
| 4 review | 15분 | 1h 30분 |
| 5 codex | 15분 | 1h 45분 (skip 시 1h 30분) |
| 6 perf | 15분 | 2h |
| 7 security | 30분 | 2h 30분 |
| 8 quant domain | 45분 | 3h 15분 |
| 9 summary | 10분 | 3h 25분 |

실제 소요는 결함 많을수록 증가 (수정·재검증 cycle).

---

## 7. 환경 caveat

- **gstack preamble 에러 무시.** Windows 환경에서 bash 명령 일부 실패해도 본
  작업 진행에 영향 없음.
- **dev 서버 안 뜨면 Phase 2·3 skip 불가** — 반드시 사람이 개입해서 해결.
- **codex CLI 없으면 Phase 5 skip** — 자동, 사람 개입 불필요.
- **CWD가 `platform/`이어야** — git 기반 skill들 (review, ship, health)
  정상 동작 조건.
- **Vercel preview URL이 있으면 Phase 6은 preview 기준** — production 보호.
- **Postgres 연결 안 되면 Phase 1·7 일부 검증 skip** (Railway down 시).

---

## 8. `/goal` 원클릭 스니펫

`/goal`(Claude Code v2.1.139+, 신뢰 워크스페이스 필요)로 위 플레이북을 사람 개입 없이
완주시킨다. 평가자(Haiku)는 transcript만 보므로, 모든 종료 조건을 "실제 출력으로 증명"
하도록 강제했다. auto mode와 함께 쓰면 완전 무인 실행. 사용 전 `cd platform/web; bun run dev`로
dev 서버를 먼저 띄워둘 것(Phase 2·3 필요). 중간 점검 `/goal`, 중단 `/goal clear`.

### 8-A. 진단 전용 (REPORT-ONLY) — 수정·커밋 없이 모든 문제를 상세 보고

각 결함은 6필드를 모두 채운다: ①문제 사항(위치·근거) ②왜 문제인가(영향)
③근본 원인(구조적) ④방향성에 맞는 해결책(CLAUDE.md/DESIGN.md/도메인 원칙 부합)
⑤Trade-off·한계·예상 부작용 ⑥추가 필요 정보·align 해야 할 사항.

```text
/goal REVIEW_PLAYBOOK.md의 /풀리뷰 10단계(Phase 0~9)를 진단 관점으로 완주하되,
어떤 코드도 수정·커밋·push 하지 말고 발견한 모든 문제를 상세히 "보고"만 하라.

[작업 지시] CWD는 platform/. REPORT-ONLY 모드. Phase별 분석을 실행하되 소스 파일을
편집하거나 커밋하지 않는다. /qa 대신 /qa-only를 쓰고, design-review·review·cso 등은
분석 결과만 수집한다(자동 수정 금지). lint·type·golden test·audit 같은 읽기 전용
명령은 실행해 신호를 수집한다(코드 변경 아님). 결과는
platform/docs/review-reports/<오늘날짜-HHMM>/FINDINGS_REPORT.md 에 누적 기록한다.

[보고 형식] 발견한 모든 결함을 아래 6필드를 전부 채워 기록한다. 하나라도 비면 미완료:
  1.문제 사항(위치·근거)  2.왜 문제인가(영향)  3.근본 원인(구조적)
  4.방향성에 맞는 해결책(CLAUDE.md/DESIGN.md/도메인 원칙 부합)
  5.Trade-off·한계·예상 부작용  6.추가 필요 정보·align 해야 할 사항
심각도(Critical/High/Medium/Low)와 결함 ID를 붙인다.

[완료 조건 — 전부 충족 시에만 done. 각 항목을 대화에 실제 출력으로 증명할 것]
1. FINDINGS_REPORT.md가 review-reports/<오늘날짜> 폴더에 작성됨(경로 출력).
2. Phase 0~9가 모두 진단됨(codex 미설치면 "skipped" 한 줄로 갈음 허용).
   각 phase 커버 여부를 나열해 증명.
3. 읽기 전용 신호 수집 완료: `cd platform; pytest tests/golden_backtest.py -v`,
   server `ruff check .`·`mypy app`, web `bun run tsc --noEmit`·`bun run lint`를
   실행하고 각 출력 마지막 줄을 붙여넣어 증명(통과 여부와 무관, 결과를 결함으로 기록).
4. 자체 점검표 출력: 모든 결함 ID에 대해 6필드(1~6)가 채워졌는지 ✅/❌ 표로 제시.
   ❌가 하나라도 있으면 done 아님.
5. 우선순위 매트릭스(Critical/High/Medium/Low 건수)와 5개 관점별 0-10 점수를
   FINDINGS_REPORT.md에 포함하고 카운트를 출력.

[제약 — 위반 시 done 아님]
- 소스 코드 편집·git commit·git push 일절 금지. 산출물은 review-reports 폴더의
  보고 문서(.md)에만 쓴다.
- 추측으로 단정하지 말 것. 근거가 부족한 항목은 결함 6번(추가 필요 정보)에 명시.
- Phase 2·3용 dev 서버(`cd platform/web; bun run dev`)가 안 뜨면 그 Phase는
  "관측 불가, 사용자 개입 필요"로 보고하고 계속 진행(무한 재시도 금지).
- 한글 출력 스크립트는 UTF-8 명시(cp949 모지바케 방지).

[안전장치] 40턴을 넘기거나 같은 Phase에서 3턴 연속 진전이 없으면 멈추고
FINDINGS_REPORT.md에 "[INCOMPLETE — blocked at Phase N]"로 현황을 남긴 뒤 보고하라.
```

### 8-B. 진단 전용 경량 (엔지니어링·도메인만)

```text
/goal platform/에서 코드 수정 없이 진단만 하라. /health, /review(분석만), /cso daily,
그리고 읽기전용 명령(`pytest tests/golden_backtest.py -v`, ruff·mypy·tsc·bun lint)을
실행해 신호를 수집하고, 발견한 모든 Critical/High/Medium 결함을 6필드(문제/왜/근본원인/
방향성맞는해결책/trade-off·부작용/추가필요정보)로 FINDINGS_REPORT.md에 기록하라.
완료 조건: 보고서 경로 출력 + 모든 결함의 6필드 채움 여부 ✅/❌ 자체점검표 + 명령
출력 마지막 줄들 + 심각도별 건수. 코드 편집·commit·push 금지. 25턴 넘으면 현황 보고.
```

### 8-C. 수정형 (참고 — 결함을 즉시 고치고 커밋)

보고가 아니라 실제 수정까지 자율로 돌릴 때. Critical은 즉시 수정 커밋, High는 수정
또는 "구조변경=사용자결정"으로 deferred, Medium/Low는 backlog 기록.

```text
/goal REVIEW_PLAYBOOK.md의 /풀리뷰 10단계(Phase 0~9)를 끝까지 완주하고 발견된 결함을 처리하라.
CWD는 platform/. Critical은 즉시 수정 커밋, High는 수정 또는 deferred(사용자결정) 기록,
Medium/Low는 backlog 기록. 완료 조건(각 항목을 출력으로 증명): ①SUMMARY.md 작성(경로 출력)
②Phase 0~9 모두 실행(codex 없으면 skipped 갈음) ③`cd platform; pytest tests/golden_backtest.py -v`
exit 0 ④server ruff·mypy, web tsc·lint 통과 ⑤우선순위 매트릭스 Critical=0, High는 전부
수정 또는 deferred(사용자결정). 제약: git push 금지(commit까지만), KIS 자격증명이 server·local
코드에 노출되면 Critical, dev 서버 안 뜨면 즉시 멈춰 보고(무한 재시도 금지), 한글 출력 UTF-8 명시.
40턴 초과 또는 같은 결함 3턴 무진전 시 멈추고 "[INCOMPLETE — blocked at Phase N]" 기록 후 보고.
```
