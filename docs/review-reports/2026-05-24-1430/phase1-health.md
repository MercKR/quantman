# Phase 1 — Code Health 신호

## 1. 영역별 점수 (0-10) — 직전 리뷰(2026-05-23-2108) 대비

| 영역 | 2108 | 1430 | 변화 | 근거 |
|---|---|---|---|---|
| server lint (ruff) | 7 | **8** | +1 | 17 → 10 errors (모두 E702 semicolon multi-stmt) |
| server type (mypy) | 5 | **5** | 0 | 86 → 85. 대부분 stub missing(pandas/quant_core/apscheduler). 구조적 회귀 미해소 |
| web type (tsc) | 10 | **10** | 0 | 0 errors ✓ |
| web lint (eslint) | 7 | **8** | +1 | 6 → 5. react-hooks/refresh 영역 |
| pytest 단위 | 10 | **5** | −5 | 195 passed / 1 **FAILED** (회귀 test stale) |
| golden 백테스트 | 10 | **10** | 0 | 15 passed / 1 skipped ✓ |
| dep audit | 9 | **10** | +1 | npm + pip(server·local) 모두 0 vulnerabilities |
| **종합** | **7.6** | **7.7** | +0.1 | test FAILED 가중치 반영 |

## 2. Top 결함 (Phase 9 FINDINGS_REPORT.md에서 6필드로 확장)

### Critical / High

**FX-1 [High]** `local/tests/test_killswitch_intraday.py::test_in_cycle_flag_reset_on_exception` 실패
- 호출 `trader._cycle_locked([], {}, None, None, None, "KRX")` — 6 args. 함수 시그니처(`local/localapp/trader.py:1121-1122`)는 7 args 요구(`strategies, dataset, today, buy_candidates, risk_limits, market, krx_status`).
- 원인: Phase 48에서 `krx_status` 인자 추가 시 회귀 test 업데이트 누락.
- 영향: production 호출처(`_cycle`)는 인자 전달 정상 → functional impact 0. 그러나 **kill switch finally reset 동작의 회귀 보호 신호 손상**. CI 가 redgreen 으로 stale.

### Medium

**FX-2 [Medium]** ruff E702 10건 — `app/routers/sync.py` 8건 + `app/routers/portfolio.py` 2건
- 패턴: `session.add(s); session.commit()` 한 줄 다중 statement.
- functional impact 없으나 PR-3 (Over-thinking 코드 위반). 한 줄 압축이 짧지 않고 가독성 손해.

**FX-3 [Medium]** mypy `kis_master_cache.py` — `_state` 변수 type union 폭주
- `_state` 가 `int | dict | set | None` 으로 추론 → 9개 union-attr error + 7개 arg-type error. type annotation 누락이 원인.
- 잠재적 런타임 type confusion (dict 메서드 호출 가능 / int 호출 시 AttributeError).

**FX-4 [Medium]** mypy `app/preview_engine.py:35` — `datetime` no attribute `desc`
- ORM ordering `desc()`를 `datetime` 컬럼에 호출. SQLAlchemy 패턴이라 실제 동작은 OK일 가능성 — 그러나 type-narrow 안 되는 신호. 코드 read 후 확정.

**FX-5 [Medium]** mypy `app/db.py:25-28` — `connect_args` dict type mismatch
- PostgreSQL keepalive 옵션 `keepalives: 1`(int)를 `dict[str, bool]` 예상에 전달. functional 정상 (psycopg 받음). type-annotation 명시 보강 권장.

**FX-6 [Medium]** mypy `app/screener.py:147` — `sort_order` `Literal['asc','desc']` 에 일반 `str` 전달
- 입력 검증 없는 사용자 입력 도달 가능성 → 런타임 ValueError 가능. **입력 validate가 어디서 되는지** 확인 필요.

### Low

**FX-7 [Low]** eslint `react-hooks/set-state-in-effect` 2건
- `web/src/auth.tsx:20` (`api.me().then((u) => setEmail(u.email))`)
- `web/src/pages/Backtest.tsx:1223` (`CapitalInput` useEffect 안 setDraft)
- 직전 review에서도 식별. 위치 일부 변경(라인 number drift)이지 동일 패턴.
- 회귀 위험은 낮으나 React strict mode·cascading render 우려.

**FX-8 [Low]** eslint `react-refresh/only-export-components` 3건
- `SymbolPicker.tsx:8,20` + 어느 다른 파일.
- HMR 동작에 영향(개발 편의). Production 동작 무영향.

## 3. 실행 신호 — 출력 마지막 줄

| 명령 | 결과 |
|---|---|
| `ruff check platform/server` | `Found 10 errors.` (E702 ×10) |
| `npx tsc --noEmit` (web) | (0 lines = pass) |
| `npm run lint` (web) | `✖ 5 problems (5 errors, 0 warnings)` |
| `mypy app` (server) | `Found 85 errors in 24 files (checked 33 source files)` |
| `pytest --tb=no -q` (platform 전체) | `1 failed, 195 passed, 33 warnings in 49.88s` |
| `pytest tests/golden_backtest.py -v` | `15 passed, 1 skipped, 2 warnings in 397.97s` |
| `npm audit --production` | `found 0 vulnerabilities` |
| `pip-audit -r server/requirements.txt` | `No known vulnerabilities found` |
| `pip-audit -r local/requirements.txt` | `No known vulnerabilities found` |
| `codex --version` | `codex: command not found` → Phase 5 자동 skip |

## 4. 진단 요약

- **회귀**: 1건 (test_in_cycle_flag_reset_on_exception, krx_status 누락). 코드 자체는 안전, **test 만 stale**.
- **무회귀**: golden test 15건 pass — 백테스트 엔진 안정.
- **공급망**: 모두 clean.
- **타입 안전성**: mypy 85건 중 stub missing 약 40건 제외 ~45건이 진짜 시그널. 직전 cycle 대비 미해소 + 신규 1~2건 추정 (kis_master_cache, db.py 등).
- **lint**: 전체 트렌드는 개선 (서버 17→10, 웹 6→5).

## 5. 다음 단계로 전달

- Phase 4 코드 리뷰에 **Phase 49 uncommitted 변경 + Phase 47~48 + Railway fix 3건**의 diff 정밀 분석 위임.
- Phase 7 보안에 mypy `kis_master_cache.py` `_state` union 안전성 검증 위임.
- Phase 8 도메인에 golden test 외 **kill switch real-path 검증** (test_in_cycle_flag_reset_on_exception 수정 후 다시 돌릴 것) 권고.
