# Phase 4 — 코드 변경 리뷰

**스코프:** 직전 cycle(2108) 이후 commit 8건 + Phase 49 uncommitted (5 files, +518 -445).

## 1. Commit Summary

| 해시 | 분류 | 파일 | 핵심 | 평가 |
|---|---|---|---|---|
| `bd3571f` | fix | `db.py` (+14) | _migrate PG 분기에 P1-C/D 컬럼 ALTER 누락 보정 | ✅ IF NOT EXISTS 멱등. 검증 끝 |
| `a473126` | fix | `preview_engine.py` (+41 -41) | per-user session 격리 (cascade 차단) | ✅ user 목록만 light session으로 로드 + 각 user 독립 with-block. 회귀 없음 |
| `2b7e173` | fix | `data_fetcher.py` (+29 -29) | fetch_korean_stocks results dict 제거 (OOM root cause) | ✅ 시그니처 `dict→int` 변경, 호출자 main.py:258 반환 미사용이라 호환. 검증 끝 |
| `3245e87` | feat | (다파일) | P1-A/B/C/D + P2-A — 일시정지·KIS health·슬리피지·일일한도·로그보존 | ⚠️ P1-C/D PG ALTER 누락 → `bd3571f`로 후속 fix. **이 패턴이 재발 가능** (FX-9 참고) |
| `7c4bac3` | feat | (다파일) | P0-1~5 — 약관·자문아님·NFA·거래정지차단·KIS throttle | ✅ baseline 통과 |
| `a968f6a` | feat | (다파일) | 분할매수 N차 + 평단 가중평균 + Monitor 차수 표시 | 검증 끝 (cycle 완료) |
| `7c887d8` | feat | (다파일) | 매수액 수정자 (×배수 modifier) | 검증 끝 |
| `ec1ffeb` | feat | (다파일) | 사이징 4지 통합 (정률·정액·균등·ATR) | 검증 끝 |

## 2. Uncommitted (Phase 49)

| 파일 | +/− | 변화 |
|---|---|---|
| `Backtest.tsx` | +544/-445 | BuyTargetPanel 재작성·BuyTargetModal 신규·sentence-clause × 4·BuyPricePanel 신규·4-3 섹션 제거·useLimit state |
| `ConditionBuilder.tsx` | +321/-...전체 | OperandChip/OperandEditor 제거·SymbolChip/IndicatorChip 좌·우 공용 (+compatGroup)·RightOperand 신규·dead code(operandSummary 등) 정리 |
| `Strategies.tsx` | +2/-2 | "매수 대상" → "매수후보" 라벨 |
| `types.ts` | +6/-1 | ExecutionPolicy.use_limit 필드 + EXECUTION_DEFAULTS.use_limit=true |
| `index.css` | +90 | sentence-clause·buy-target-buttons·price-mode-row·kind-toggle 등 |

## 3. 결함

### High

**FX-9 [High]** PG 분기 마이그레이션 누락 패턴 — **회귀 가능**
- 위치: `server/app/db.py` `_migrate()` SQLite vs PostgreSQL 분기 두 갈래
- 패턴: 신규 컬럼 추가 시 SQLite 분기에만 ALTER 추가 → PG production DB 누락 → `column does not exist` cascade
- 직전 incident: P1-C/D 4컬럼 누락 → `bd3571f`로 fix
- 근본: 두 분기 수동 동기화 의존. SQLite 3.35+도 `IF NOT EXISTS` 지원 — **통합 가능**
- 방향성: 통합 헬퍼 `_alter_add_column_if_not_exists(table, col, type)` 만들어 두 분기 단일 path

### Medium

**FX-10 [Medium]** Phase 49 `ConditionBuilder.tsx` — SymbolChip의 compatGroup 처리에서 falsy/`"other"` 두 케이스 혼동 가능
- 위치: SymbolChip (line ~432) `compatGroup ? allInds.filter(compat) : allInds`
- 문제: `compatGroup = "other"`이면 truthy → filter 호출. filter 내부 `compat` 함수는 `compatGroup === "other"` 시 항상 true → 결과 같음. **불필요한 filter 통과**.
- 비효율 미세. 결함은 아니나 `compatGroup && compatGroup !== "other"` 패턴이 IndicatorChip(line ~552)과 일관 안 됨.
- 통일 권장.

**FX-11 [Medium]** Phase 49 `BuyTargetModal.switchTab` — 모드 전환 시 종목 무경고 초기화 (QA49-01 동치)
- 위치: BuyTargetModal `switchTab(t)` → `setTradeSymbol("")`
- 의도된 단순 동작이나 confirm 없이 작업 손실. UX 마찰.

**FX-12 [Medium]** `web/src/pages/Backtest.tsx` BuildTab props 28개 → smell
- 위치: BuildTab props (line 355~389)
- 28개 props 시그니처. React 권장 안티패턴 (props 폭주). 향후 상태를 (a) Context (b) useReducer 로 통합 후보.
- 단, 일관성 있게 모두 state setters라 functional impact 없음. backlog.

### Low

**FX-13 [Low]** `Backtest.tsx` BuildTab 호출 props에서 setRule만 별도 (`setRule: (k, p) => void`)
- 다른 props는 setter 직결, setRule은 `setExits` wrapper.
- 일관성 미세 위반.

**FX-14 [Low]** Phase 49 dead code 정리 후 lint warning 없음
- `operandSummary`/`affineSuffix`/`indLabel` 제거 ✓. unused import 잔재 없음 ✓.

## 4. 누락 확인

- **Phase 48 P0-4 (거래정지·관리종목 자동 차단)** — `trader.py` 매수 직전 is_halt/is_managed 체크. KIS broker 거부 2차 안전망. **VI·CB는 미구현** (commit body 명시: "VI·CB는 다음 cycle").
- **권리락·배당락 캘린더** — 미구현. memory에 best practice 조사만 완료.
- **외부 로펌 약관 재검수** — 코드 작업 아님.

## 5. SQL safety / Race condition / Error handling

| 항목 | 결과 |
|---|---|
| SQL injection | ORM (SQLModel/SQLAlchemy) — 위험 없음 |
| Race condition | Q5 _in_cycle lock (intraday loop) + per-user session 격리 (preview cron) — 회귀 없음. **단 FX-1 (test_killswitch_intraday stale)로 실제 검증 신호 손상** |
| Error handling | preview_engine `refresh_all_users_preview` `webhook_sent` 미사용 변수 보임. unused (위 코드 read 확인 필요). PR-2 후보 |
| Race in BuyTargetModal | 모달 안 setState 비동기 + 부모 state 갱신 — React 18 batch로 안전 ✓ |

## 6. 4원칙 자기검토 (Phase 4)

| 원칙 | 자기검토 |
|---|---|
| 근본원인 | FX-9 (PG 분기 누락) — 통합 헬퍼로 근본 해결 후보. backlog ✅ |
| Over-eng | BuildTab props 28개 — 부차 표면 의심. backlog FX-12 ✅ |
| Over-think | switchTab confirm 미도입은 단순 우선 (사용자 결정 surface) ✅ |
| 검증된 해결책 | mypy + ruff + eslint + pytest로 diff 신호 수집. FX-1로 회귀 보호 신호 손상 명시 ✅ |

## 7. Phase 9 전달

- **FX-9** PG/SQLite 분기 마이그레이션 통합 — 회귀 방지 (High)
- **FX-10** SymbolChip/IndicatorChip compatGroup 패턴 통일 (Medium)
- **FX-11** switchTab confirm (Medium, 사용자 결정)
- **FX-12** BuildTab props Context/useReducer 통합 (Medium backlog)
- **FX-13~14** Low
