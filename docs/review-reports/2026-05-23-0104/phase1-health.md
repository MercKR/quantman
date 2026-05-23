# Phase 1 — 코드 베이스라인 신호 (읽기 전용)

모든 명령을 실제 실행하고 마지막 줄을 캡처. (gstack `/health` 부재 → 직접 실행)

| 신호 | 명령 | 결과(마지막 줄) | 판정 |
|---|---|---|---|
| 백테스트 골든 | `pytest tests/golden_backtest.py -v` | `15 passed, 1 skipped, 30 warnings in 193.98s` | ✅ 통과(단, log 경고) |
| 전체 테스트 | `pytest tests/ -q` | `40 passed, 2 warnings in 11.07s` | ✅ 통과 |
| server lint | `ruff check .` (server) | `Found 21 errors. [*] 1 fixable` | ❌ 21건 |
| server type | `mypy app` (server) | `Found 80 errors in 22 files (checked 31 source files)` | ⚠️ 다수 노이즈+일부 실질 |
| web type | `npx tsc --noEmit` (web) | (출력 없음) → exit 0 | ✅ 무오류 |
| web lint | `npm run lint` (web) | `✖ 10 problems (10 errors, 0 warnings)` | ❌ 10건 |

## 해석

### golden 경고 (도메인 lead → Phase 8에서 추적)
30건 경고 중 `RuntimeWarning: divide by zero encountered in log`, `invalid value encountered in log`.
→ log-수익률/Sharpe/변동성 계산에서 0·음수에 log() 적용 의심. 테스트는 통과하나 보고 지표 손상 가능 → core 에이전트가 추적.

### ruff 21건 (server)
대부분 `app/technical_cache.py`의 **E701**(한 줄에 다중 statement — `if ...: continue`). 1건 자동수정 가능.
가독성·정적분석 방해 이슈로 기능 버그는 아님 → Medium(코드 품질).

### mypy 80건 (server) — 분류 필요
- **노이즈(도구 설정)**: `quant_core` import-not-found(서버가 형제 패키지 `core/quant_core`를 import하나 mypy path 미설정), `pandas`/`apscheduler` stub 미설치. → 런타임 버그 아님.
- **실질 후보**: `int | None` → `int` 인자 불일치 다수(SQLModel `.id`가 commit 전 None) — 대부분 런타임엔 안전하나 타입 안전성 공백. `portfolio.py:79` unary minus on object, `backtest.py:128-129` tuple 비인덱싱 — 실 버그 가능 → server 에이전트가 검증.
- **SQLAlchemy 친화 오탐**: `"datetime" has no attribute desc/asc`, `"str" has no attribute in_` — 매핑 컬럼 메서드를 mypy가 못 봄. 런타임 정상.

### web lint 10건
- `Login.tsx:37` — `Unexpected any` (타입 안전성).
- `Monitor.tsx:54`, `Strategies.tsx:52·65`, `ScreenerPanel.tsx:~1035` — **react-hooks/set-state-in-effect**(effect 본문에서 동기 setState → cascading re-render). 성능·정확성 안티패턴 → web 에이전트가 영향 평가.
- tsc는 무오류이므로 타입 깨짐은 아님.

## 추세
이전 리뷰 폴더 없음 → 추세 비교 불가(첫 산출물). 다음 회차부터 비교 가능.
