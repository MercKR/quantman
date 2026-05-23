# Phase 0 — 환경 점검

- **일시**: 2026-05-23 01:04 (KST)
- **모드**: REPORT-ONLY (코드 수정·commit·push 없음). `/goal` 진단 전용 스니펫(8-A) 기준.
- **CWD**: `platform/` — git repo, branch `main`.

## Uncommitted 변경 (3 파일)
```
 M REVIEW_PLAYBOOK.md                   리뷰 스니펫(§8) 추가 — 본 리뷰 산출물 아님
 M web/src/components/ScreenerPanel.tsx  스크리너 KR/US 섹션 분리 작업 → Phase 4에서 리뷰
 M web/src/types.ts                      ScreenerPreset.market_group 필드 추가 → Phase 4
```
REPORT-ONLY 원칙상 stash/commit 하지 않고 그대로 두고 diff만 리뷰함.

## 도구 가용성
| 도구 | 상태 |
|---|---|
| python | 3.12.7 ✓ |
| node | v24.15.0 ✓ |
| pytest / ruff / mypy / pip-audit | 9.0.3 / 0.15.14 / 2.1.0 / 2.10.0 ✓ |
| **bun** | **미설치** → web `tsc --noEmit`·`lint`은 `npx tsc`·`npm run lint`로 대체 |
| **codex** | **미설치** → Phase 5 자동 skip |
| gstack 스킬(/health·/qa·/design-review·/review·/cso·/benchmark) | **미설치** → 각 Phase를 동등 수동 진단으로 수행 |

## 기준선·관측 한계
- **golden baseline**: `tests/golden_baseline.json` 존재 → 회귀 검증 모드로 동작.
- **이전 리뷰 폴더**: 없음 (이 폴더가 첫 `/풀리뷰` 산출물) → Phase 1·6 추세 비교 불가.
- **dev 서버**: `bun run dev`는 bun 미설치로 기동 불가. → **Phase 2(시각/UX)·Phase 3(사용자 플로우)의 브라우저 런타임 관측 불가**. 정적 분석(코드+DESIGN.md+CSS)으로 갈음하고, 런타임 검증이 필요한 항목은 결함 6번(추가 필요 정보)에 "관측 불가, 사용자 개입 필요"로 명시.

## 진단 방식 요약
gstack 스킬 부재로 Phase별 스킬 래퍼 대신 다음으로 수행:
- Phase 1: ruff·mypy·tsc·eslint·pytest 직접 실행 (읽기 전용 신호).
- Phase 2·3: 코드/DESIGN.md 정적 검토 (런타임 관측 불가 명시).
- Phase 4: `git diff` 리뷰.
- Phase 5: skipped (codex 없음).
- Phase 6: bundle·정적 분석 (Lighthouse/benchmark 런타임 측정 불가).
- Phase 7: 자격증명 격리 grep + pip-audit/npm audit.
- Phase 8: QUANT_DOMAIN_CHECKLIST 7카테고리 + golden test 회귀.
- 심층 코드 정독은 4개 영역(local·server·core·web) 병렬 서브에이전트로 수행, 본 진단자가 종합.
