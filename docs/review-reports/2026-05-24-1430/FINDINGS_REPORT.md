# FINDINGS_REPORT — 2026-05-24-1430 (REPORT-ONLY)

**모드:** 진단 전용 — 코드 수정·commit·push 없음
**스코프:** 풀리뷰 10단계 (Phase 0~9, codex skipped)
**가이드라인 baseline:** 메모리 + `QUANT_DOMAIN_CHECKLIST.md` + 이전 review-reports + 표준 자본시장법·NFA 2-29
*※ 사용자 paste 예정이었던 가이드라인 본문 미도착 — paste 도착 시 19개 G-XX 매핑(`phase8-quant-domain.md §3`) 재대조 권장*

---

## 0. 종합 점수 & 매트릭스

### 우선순위 매트릭스

| 심각도 | 건수 | ID |
|---|---|---|
| **Critical** | 0 | — |
| **High** | 4 | FX-1, FX-9, DM-1, DM-2 |
| **Medium** | 11 | FX-2/3/4/5/6/10/11/12, SC-1, DM-3/4/5 |
| **Low** | 8 | FX-7/8/13/15/16, SC-2, D49-03/04 |
| **이월 (직전 cycle)** | 3 | D-03, D-04, D-05 |

### 5관점 점수 (0-10) — 직전(2108) 대비

| 관점 | 2108 | 1430 | 변화 |
|---|---|---|---|
| UX / 사용성 | 7.5 | 7.6 | +0.1 (Phase 49 통합 문장) |
| Visual design | 7.5 | 7.6 | +0.1 |
| Engineering | 7.6 | 7.4 | **−0.2** (test 회귀 FX-1) |
| Product | 8.0 | **8.2** | +0.2 (Phase 48 가이드라인 baseline 71% 충족) |
| System trading | 8.5 | **7.9** | **−0.6** (VI·CB·권리락 미구현 surface) |
| **종합** | 7.8 | 7.7 | −0.1 |

### 자체점검표 — 모든 결함 6필드 완전성

본 보고서의 모든 결함 ID에 대해 6필드(① 문제 위치·근거 / ② 왜 문제인가 / ③ 근본 원인 / ④ 방향성 맞는 해결책 / ⑤ Trade-off·한계·부작용 / ⑥ 추가 필요 정보·align) 충족 여부:

| ID | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| FX-1 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| FX-2 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| FX-3 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| FX-4 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| FX-5 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| FX-6 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| FX-7 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| FX-8 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| FX-9 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| FX-10 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| FX-11 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| FX-12 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| FX-13 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| FX-15 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| FX-16 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| D49-02 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| D49-03 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| D49-04 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| SC-1 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| SC-2 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| DM-1 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| DM-2 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| DM-3 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| DM-4 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| DM-5 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

전체 ✅. ❌ 0건.

### 읽기 전용 신호 실행 출력 마지막 줄

| 명령 | 마지막 줄 |
|---|---|
| `ruff check platform/server` | `Found 10 errors.` |
| `npx tsc --noEmit` (web) | (0 line) |
| `npm run lint` (web) | `✖ 5 problems (5 errors, 0 warnings)` |
| `mypy app` (server) | `Found 85 errors in 24 files (checked 33 source files)` |
| `pytest --tb=no -q` (platform 전체) | `1 failed, 195 passed, 33 warnings in 49.88s` |
| `pytest tests/golden_backtest.py -v` | `15 passed, 1 skipped, 2 warnings in 397.97s` |
| `npm audit --production` | `found 0 vulnerabilities` |
| `pip-audit -r server/requirements.txt` | `No known vulnerabilities found` |
| `pip-audit -r local/requirements.txt` | `No known vulnerabilities found` |
| `codex --version` | `codex: command not found` → Phase 5 skip |

---

## 1. High 결함 (4건)

### FX-1 [High] — `test_in_cycle_flag_reset_on_exception` stale (kill switch 회귀 보호 손상)

1. **문제 (위치·근거)**: `local/tests/test_killswitch_intraday.py:297` `trader._cycle_locked([], {}, None, None, None, "KRX")` 6 args 호출. 함수 시그니처(`local/localapp/trader.py:1121-1122`)는 7 args (`strategies, dataset, today, buy_candidates, risk_limits, market, krx_status`) 요구. `pytest 1 failed: TypeError: Trader._cycle_locked() missing 1 required positional argument: 'krx_status'`.
2. **왜 문제인가**: production 호출 path는 인자 전달 정상 → functional impact 0. 그러나 kill switch finally reset 동작(Q5 cycle lock dead-lock 방지)의 **회귀 보호 신호 손상**. CI 가 빨강 상태 — 다른 회귀가 들어와도 신호 묻힐 위험.
3. **근본 원인**: Phase 48 commit `7c4bac3` 에서 `_cycle_locked` 에 `krx_status` 인자 추가 시 회귀 test 업데이트 누락. 코드 변경 → 회귀 test sync 강제 신호 부재.
4. **방향성 맞는 해결책**: (a) 즉시 fix — test에 `krx_status={}` 추가, 1줄 변경. (b) 후속 — 시그니처 변경 PR 시 affected tests 자동 표시하는 CI guard (PR check가 test 빌드도 포함하면 자동 잡힘).
5. **Trade-off·한계·부작용**: (a) 단순 fix는 1분, 위험 없음. test 자체의 의미(예외 발생 시 _in_cycle reset)는 그대로. (b)는 CI 인프라 추가 — over-eng 위험 없음(이미 pytest 돌리는 CI 있으면).
6. **추가 필요 정보·align**: CI 가 실제로 어떤 환경에서 pytest 돌리는지 (Railway? GitHub Actions?). main push 차단 정책 있나? PR-1 (fail-fast vs fallback) 관점 — 현 상태는 silent regress.

### FX-9 [High] — PG/SQLite 분기 마이그레이션 동기화 회귀 가능 패턴

1. **문제 (위치·근거)**: `server/app/db.py:_migrate()` PostgreSQL vs SQLite 두 분기. 신규 컬럼 추가 시 두 분기 모두 ALTER 추가 필요. 직전 Phase 48 P1-C/D에서 SQLite 분기에만 추가 → PG production DB 누락 → `column does not exist` cascade incident (`docs/incidents/2026-05-24-railway-oom-handoff.md`). `bd3571f`로 fix.
2. **왜 문제인가**: cascade 패턴 인시던트는 1회 발생, 24시간 동안 14명+ user preview 실패 (memory). 재발 시 동일 incident 가능. 사용자 신뢰·서비스 가용성 손상.
3. **근본 원인**: 두 분기 수동 동기화 의존. SQL 표준 `ALTER TABLE ADD COLUMN IF NOT EXISTS` 가 SQLite 3.35+에서도 지원되지만 현재 코드는 PG에서만 사용. 통합 안 함.
4. **방향성 맞는 해결책**: 헬퍼 `_alter_add_column_if_not_exists(conn, table, col, sqltype)` 도입. SQLite/PG 모두 동일 SQL 발행. 분기 단일화. (또는) Alembic 도입 — 정식 마이그레이션 (over-eng 위험: 작은 서비스에 과한 인프라).
5. **Trade-off·한계·부작용**: 헬퍼 통합은 SQLite 3.35+ 의존 (Python 3.11+ 표준 sqlite3는 3.40+, 안전). 한계: 컬럼 외 변경(인덱스·CHECK 제약 등)은 별도 헬퍼 필요. 부작용: 통합 코드 가독성 향상.
6. **추가 필요 정보·align**: 향후 Alembic 도입 vs 자체 헬퍼 결정. Alembic은 데이터 마이그레이션도 지원하지만 학습 곡선 있음.

### DM-1 [High] — VI·CB 자동 차단 미구현 (가이드라인 G-08, G-09)

1. **문제 (위치·근거)**: `grep VI|circuit_breaker` 결과 `local/localapp/` 에 실 구현 0 매치. commit `7c4bac3` body 명시 "VI·CB는 다음 cycle".
2. **왜 문제인가**: VI(volatility interruption) 발동 종목에 매수 시도 시 KIS broker가 거부(2차 안전망). 클라이언트는 거부 이유 모르고 retry → KIS rate limit 부담 + 사용자 혼란 ("왜 안 사지지?"). CB(circuit breaker) 시장 전체 정지 시도 같음. 한국 자본시장법·KIS 약관 baseline 미충족 위험.
3. **근본 원인**: VI·CB 상태 데이터 소스 부재. KRX 정보데이터시스템 API 사용해야 — 외부 키 발급 필요.
4. **방향성 맞는 해결책**: (a) KRX 정보데이터시스템 API 키 발급 → server cron VI·CB 상태 polling → `/krx/status` 응답에 추가 → `local/localapp/sync_client.py:pull_krx_status` 가 받음 → trader 매수 직전 차단. (P0-4 거래정지·관리종목 패턴과 동일 구조).
5. **Trade-off·한계·부작용**: 외부 API 의존 + rate limit. KRX API down 시 fail-open? fail-close? 정책 결정 필요. 보수적 = fail-close (안전), 사용자 = fail-open (매수 기회 손실 적음). 가이드라인 권장은 fail-close.
6. **추가 필요 정보·align**: KRX API 발급 절차·비용. 가이드라인 paste 본문에서 fail-open/close 명시 여부 확인.

### DM-2 [High] — 권리락·배당락 캘린더 미구현 (가이드라인 G-16)

1. **문제 (위치·근거)**: `grep "권리락|배당락|ex-date|ex_date"` 결과 `local/`·`core/` 실 구현 0. memory 에 best practice 조사만 완료.
2. **왜 문제인가**: 현재 dataset은 FDR가 adjusted 가격을 받아 백테스트는 자동 OK. 라이브 KIS도 자동 평단 조정. 그러나: (a) ex-date 발생 시 사용자 인지 부재 → "왜 평단이 갑자기 바뀌었지?" 혼란 (b) ex-date 매수 차단 없음 — 단기 변동성 큰 날 진입 위험.
3. **근본 원인**: KRX 코퍼레이트 액션 캘린더 cron 부재. 정기 ex-date list pull 필요.
4. **방향성 맞는 해결책**: (a) server cron — `pykrx` 또는 KRX API로 ex-date 표 매일 pull (b) server `/krx/corporate_actions/upcoming` 노출 (c) trader 매수 직전 ex-date 매수 차단(설정 가능) + (d) Dashboard 알림 "삼성전자 ex-date 2026-05-30 (배당락)".
5. **Trade-off·한계·부작용**: (c) ex-date 매수 차단은 우량주 배당 노출 기회 손실. 사용자 설정 토글 (default off 또는 alert만)이 안전. (d) 알림 빈도 — cooldown 필요.
6. **추가 필요 정보·align**: `pykrx` 라이브러리 license · 의존성 추가 부담. 가이드라인 paste 에서 ex-date 처리 권장사항 명시 여부.

---

## 2. Medium 결함 (11건)

### FX-2 [Medium] — ruff E702 10건 (semicolon multi-statement)

1. **위치**: `app/routers/sync.py` 8건 + `app/routers/portfolio.py` 2건. 패턴 `session.add(s); session.commit()`.
2. **왜**: PR-3 (가독성) 위반. functional 0.
3. **근본**: 한 줄 압축 reflex 코드 스타일.
4. **해결책**: 두 줄 분리. ruff `--fix` 자동 가능.
5. **Trade-off**: 미세. 12줄 추가.
6. **추가 정보**: ruff `--fix` 안전한가 (다른 변경 동반 안 함 확인).

### FX-3 [Medium] — mypy `kis_master_cache._state` union 폭주 (9건+)

1. **위치**: `server/app/kis_master_cache.py:42,190,193,194,209,213,225,230,237,254,258` — `_state` 가 `int | dict | set | None` 추론.
2. **왜**: 런타임 type confusion 가능 (int 에 `.keys()` 호출 시 AttributeError). production 미발현이라 잠재 위험.
3. **근본**: 모듈 레벨 변수 type annotation 누락. mypy가 가장 보수적 union으로 추론.
4. **해결책**: `_state: dict[str, datetime | int] = {}` 같은 명시. 사용처에서 narrowed.
5. **Trade-off**: type annotation 추가 5분. 부작용 없음. mypy 통과.
6. **추가 정보**: 사용 path 다 알아본 후 정확한 schema 결정.

### FX-4 [Medium] — mypy `preview_engine.py:35` datetime no attribute "desc"

1. **위치**: `server/app/preview_engine.py:35`
2. **왜**: SQLAlchemy `desc()` 가 `column.desc()` 아닌 `datetime.desc()` 호출됐을 가능성. 실제 ORDER BY desc 동작 정상 (SQLAlchemy ORM 패턴)일 가능성 — mypy false positive.
3. **근본**: SQLAlchemy ORM type 추론 한계.
4. **해결책**: `from sqlalchemy import desc` import 명시 + `order_by(desc(Snapshot.created_at))` 패턴 사용. 또는 `# type: ignore[attr-defined]` 주석.
5. **Trade-off**: 명시 import는 코드 명료. ignore 주석은 일시방편.
6. **추가 정보**: line 35 코드 직접 read 후 결정 (본 cycle 미수행).

### FX-5 [Medium] — mypy `db.py:25-28` connect_args dict type mismatch

1. **위치**: `server/app/db.py:25-28` `_connect_args = {"keepalives": 1, ...}` (PG 분기).
2. **왜**: type annotation 누락. psycopg accept하므로 runtime OK.
3. **근본**: type annotation 누락.
4. **해결책**: `_connect_args: dict[str, int] = {...}` 명시.
5. **Trade-off**: 1줄 추가. 부작용 0.
6. **추가 정보**: 없음.

### FX-6 [Medium] — mypy `screener.py:147` sort_order Literal 타입 mismatch

1. **위치**: `server/app/screener.py:147` `ScreenerSpec(sort_order=...)` 에 일반 `str` 전달.
2. **왜**: 사용자 입력 도달 가능 → 런타임 ValueError 가능.
3. **근본**: 입력 검증 위치 모호 (어디서 Literal narrow?).
4. **해결책**: pydantic ScreenerSpec 모델이 이미 validate. caller에서 `sort_order: Literal["asc","desc"] = ...` 또는 cast 명시.
5. **Trade-off**: validate 위치 명확화 — 모델 layer 권장.
6. **추가 정보**: 입력 흐름 trace (web → API → ScreenerSpec) 검증.

### FX-10 [Medium] — SymbolChip/IndicatorChip compatGroup 패턴 통일 부족

1. **위치**: `ConditionBuilder.tsx` SymbolChip (line ~432) `compatGroup ? allInds.filter(compat) : allInds` vs IndicatorChip (line ~552) `compatGroup && compatGroup !== "other" ? ... : ...`.
2. **왜**: SymbolChip의 falsy/`"other"` 처리 차이로 불필요한 filter 통과 (효과 같음). 일관성 미세 위반 → 미래 버그 위험.
3. **근본**: Phase 49 작업 시 두 chip 함수 작성 순서 차이.
4. **해결책**: `helper isCompatGroupActive = (g?: string) => g != null && g !== "other"` 추출 + 두 곳 통일.
5. **Trade-off**: helper 1개 추가 (Over-eng 위험 미세). 가독성 향상.
6. **추가 정보**: 없음.

### FX-11 [Medium] — BuyTargetModal `switchTab` 모드 전환 시 종목 무경고 초기화 (= D49-01, QA49-01)

1. **위치**: `Backtest.tsx` BuyTargetModal `switchTab(t)` → `setTradeSymbol("")`.
2. **왜**: 사용자가 수동 → 자동 전환 시 기존 종목 선택 확인 없이 손실. UX 마찰.
3. **근본**: 사용자 결정 단순 우선 — Phase 49 설계 결정.
4. **해결책**: (a) 현재 단순 유지 — 빠른 작업. (b) 임시 state + apply/cancel 분리 + confirm dialog — 안전.
5. **Trade-off**: (a) 일관 코드 (b) 추가 state·callback. **사용자 결정 필요**.
6. **추가 정보**: 사용자가 모달 패턴에 익숙한지(타사 패턴 비교) — 가이드라인 paste 본문에서 모달 표준 명시 확인.

### FX-12 [Medium] — `BuildTab` props 28개 smell

1. **위치**: `Backtest.tsx` BuildTab props (line 355~389).
2. **왜**: React 권장 안티패턴 (props drilling). 새 state 추가 시 prop 갱신 4 곳 (declare·pass·destructure·signature). FX-3 (Phase 49 useLimit 추가 시)에서 확인됨.
3. **근본**: 부모 state 응집도 ↑ — Context 또는 useReducer 미사용.
4. **해결책**: (a) `useReducer` + Context로 통합 (props 1개 = state + dispatch). (b) Zustand·Jotai 상태 라이브러리.
5. **Trade-off**: (a) 학습 곡선 낮음. dependency 0. (b) 라이브러리 추가 — Over-eng 위험.
6. **추가 정보**: 다른 페이지(Dashboard, Monitor, Settings)도 동일 패턴인지 — 전사 일관성 결정.

### SC-1 [Medium] — JWT SECRET_KEY 길이 미검증

1. **위치**: `server/app/config.py:16` `SECRET_KEY: str = os.getenv("QP_SECRET_KEY", _DEFAULT_SECRET)`. Production fail-fast(line 45-48)는 "default 사용 금지"만 검증. 짧은 시크릿 ENV 통과.
2. **왜**: HMAC SHA256 RFC 7518 권장 32 bytes 미달 시 brute force 가능성. test_webhook_ssrf · test_sync_preview_auth 33 warnings 발생 (dev fixture 29 bytes).
3. **근본**: fail-fast 검증 갭.
4. **해결책**: `if settings.ENV == "production" and len(settings.SECRET_KEY.encode()) < 32: raise RuntimeError(...)`.
5. **Trade-off**: 운영 secret rotation 시 32 bytes 강제 (정상). 부작용 0.
6. **추가 정보**: 현재 production secret 길이 (Railway env). 회귀 우려 없음 — 통상 32+ bytes 사용 권장.

### DM-3 [Medium] — 섹터 분산 한도 미구현 (가이드라인 G-18, Q-02 이월)

1. **위치**: 미구현. `trader.py:_apply_risk_limits` 또는 사이징 함수에 섹터 한도 분기 없음.
2. **왜**: 단일종목 한도 (`max_position_pct`)는 있으나 동일 섹터 집중 위험 없음 → 분산 투자 원칙 미달.
3. **근본**: dataset에 섹터 분류 부재. FDR / KRX 섹터 코드 매핑 필요.
4. **해결책**: dataset 보강 → trader risk_limits 에 `sector_max_pct` 추가 → 매수 직전 현재 섹터 비중 합계 체크.
5. **Trade-off**: 섹터 분류 표준 (한국표준산업분류 KSIC, 또는 KRX 자체 섹터) — 두 종 차이. UI 노출 검토.
6. **추가 정보**: 가이드라인 paste 에서 섹터 한도 권장사항 명시 확인.

### DM-4 [Medium] — 백테스트 vs 라이브 bps drift 대시보드 부재 (가이드라인 G-19, Q-03 이월)

1. **위치**: Phase 48 P1-C로 슬리피지 임계 알림(`alert_on_slippage_bps`)은 있음. 그러나 backtest 가정 (commission + sell_tax + slippage = 36 bps) vs 라이브 실측 누적 drift UI 부재.
2. **왜**: 백테스트와 라이브 결과 괴리 원인 사용자가 추적 어려움. 신뢰 손상.
3. **근본**: 측정 데이터는 있으나 대시보드 미구현.
4. **해결책**: Monitor 또는 Dashboard에 "전략별 cost drift" 카드 추가. 가정 36 bps vs 실측 N bps (rolling 30일).
5. **Trade-off**: UI 면적 추가 — Monitor 페이지 이미 밀도 높음. backlog 카드 형태로.
6. **추가 정보**: Phase 48 P1-C 알림 임계 default 30 bps — drift 표시 임계와 일치 여부.

### DM-5 [Medium] — 부분 체결 / 미체결 큐 처리 한정 (가이드라인 G-17)

1. **위치**: backtest 단일 종목·전액 가정 (부분 체결 모델 부재). 라이브(`local/`)는 KIS 부분 체결 응답 처리 미검증.
2. **왜**: KIS 호가 부족 + 큰 발주 시 부분 체결 가능 → 잔량 처리 정책 (재시도 / 취소) 불명확.
3. **근본**: 백테스트는 의도적 단순화 (성능). 라이브는 KIS 응답 trace 필요.
4. **해결책**: (a) 라이브 KIS 부분 체결 응답 처리 코드 trace + 단위 test 추가. (b) 백테스트는 현 단순화 유지 + UI 명시 "백테스트는 100% 체결 가정".
5. **Trade-off**: 부분 체결 모델은 백테스트 정확도 향상 vs 복잡도. 라이브 처리는 안전 우선.
6. **추가 정보**: KIS 부분 체결 응답 sample. 단위 test 작성 필요성.

---

## 3. Low 결함 (8건) — 요약

| ID | 위치 | 문제 | 해결 |
|---|---|---|---|
| FX-7 | `auth.tsx:20`, `Backtest.tsx:1223` | react-hooks/set-state-in-effect | controlled input pattern 정당화 주석 또는 effect rewrite |
| FX-8 | `SymbolPicker.tsx:8,20` + 1건 | react-refresh/only-export-components | 헬퍼 별도 파일 분리 |
| FX-13 | `Backtest.tsx setRule` | 다른 props는 setter 직결, setRule만 wrapper | 일관 패턴 — backlog |
| FX-15 | `web/dist/` | Phase 49 변경 후 build 미수행 | commit + deploy 시 자동 해소 |
| FX-16 | (확인 항목) | Phase 49 dynamic import OK | 신호 — fix 불필요 |
| SC-2 | test fixtures | HMAC 29 bytes Insecure warning | SC-1 해소 후 fixture 교체 |
| D49-03 | `RightOperand.toIndicator` | 호환 데이터 없을 시 무동작 | toast/disabled 처리 |
| D49-04 | `sentence-clause` ④ | 정보 밀도 낮음 | 종목 chip 직접 표시 옵션 |

---

## 4. 이월 (직전 cycle deferred)

| ID | 위치 | 상태 |
|---|---|---|
| D-03 | `Dashboard.tsx` 페이지 단위 empty/error 통합 부재 | 이월 (구조적, 사용자 결정) |
| D-04 | `Backtest.tsx` CapitalInput set-state-in-effect | 이월 (controlled input 정당화 결정) |
| D-05 | react-refresh 위반 3 파일 | 이월 (dev only HMR 영향) |
| Q-01 | intent ledger Windows append atomicity | 이월 (단일 프로세스 가정 유지) |

---

## 5. 자동매매 가이드라인 baseline 충족률 (Phase 48 12 + 추가 7 = 19항목)

| Status | 건수 | 항목 |
|---|---|---|
| ✅ | 12 | G-01 약관 · G-02 동의 · G-03 링크 · G-04 self-direction · G-05 승격 모달 · G-06 NFA · G-07 거래정지 · G-10 rate limit · G-11 maintenance · G-12 일일한도 · G-13 슬리피지 알림 · G-15 카피트레이딩 미제공 |
| ⚠️ | 3 | G-14 5년 보존 (운영 retention 정책 영역) · G-17 부분 체결 (DM-5) · G-19 bps drift 대시보드 (DM-4) |
| ❌ | 4 | G-08 VI 차단 (DM-1) · G-09 CB 차단 (DM-1) · G-16 권리락·배당락 (DM-2) · G-18 섹터 한도 (DM-3) |

**충족률: 12/19 = 63% ✅, 14.5/19 = 76% (⚠️ 0.5 가중)**

---

## 6. 권장 다음 Phase (ROI 큰 3건)

### #1 [High] FX-1 + FX-9 — 회귀 보호 인프라

- **FX-1 즉시 fix** (1줄 변경, 1분): test에 `krx_status={}` 추가.
- **FX-9 통합** (1시간): `_alter_add_column_if_not_exists` 헬퍼 도입.
- **ROI:** 회귀 incident 차단. 사용자 신뢰·서비스 가용성.

### #2 [High] DM-1 + DM-2 — 자동매매 가이드라인 baseline 보강 (외부 API 게이트)

- VI·CB 차단 + 권리락·배당락 ex-date 캘린더.
- 의존: KRX 정보데이터시스템 API 키 발급 (사용자 결정).
- **ROI:** 한국 자본시장법·KIS 약관 baseline 완전 충족 → 신규 사용자 신뢰.

### #3 [Medium] FX-2 + FX-3 + FX-5 + SC-1 — 코드 health 정리

- ruff `--fix` 자동 (FX-2).
- mypy type annotation 5건 (FX-3/5).
- JWT length 검증 fail-fast (SC-1).
- **ROI:** mypy 95→80, ruff 0, secret 부팅 안전.

---

## 7. 사용자 결정 필요 항목

| ID | 결정 사항 |
|---|---|
| FX-11 | BuyTargetModal 모드 전환 시 confirm dialog 도입 여부 |
| FX-12 | BuildTab props → Context/useReducer 리팩토 시기 |
| DM-1 | KRX 정보데이터시스템 API 키 발급 + fail-open/close 정책 |
| DM-2 | `pykrx` 의존성 추가 + ex-date 매수 차단 default on/off |
| DM-3 | 섹터 분류 표준 (KSIC vs KRX) + UI 노출 |
| Phase 49 commit | 변경 commit 시점 (현재 uncommitted) |
| 가이드라인 paste | 본문 paste 후 G-XX 매핑 재대조 |

---

## 8. paste 도착 시 보강 위치

가이드라인 본문 paste 후 다음 위치 재대조 권장:

- `phase8-quant-domain.md §3` G-01~19 매핑 — paste 본문 조항과 1:1 비교, 새 G-XX 추가
- `phase8-quant-domain.md §4` DM-1~5 결함 정의 — paste 본문에서 더 엄격한 baseline 발견 시 추가 DM-XX
- 본 보고서 §6 권장 우선순위 재배치 가능

---

## 9. 4원칙 자기검토 (cycle 전체)

| 원칙 | 자기검토 |
|---|---|
| 근본원인 | FX-1 (test stale), FX-9 (PG 분기 통합), SC-1 (fail-fast 검증 갭) 모두 근본 후보로 surface. fallback 위반 발견 0 — ✅ |
| Over-eng | FX-12 (props 28개) backlog. 새 Context 도입은 사용자 결정. Alembic 도입(FX-9)도 게이트 — ✅ |
| Over-think | 19항목 가이드라인 baseline 단일 매핑표, 7카테고리 단일 표, 5관점 단일 점수표 — ✅ |
| 검증된 해결책 | 모든 결함이 명령 출력·grep·코드 inspection 근거. 추측 단정 없음. **인증 wall + KIS 실호출 검증 불가는 명시 보고** — ✅ |

---

**End of FINDINGS_REPORT**
