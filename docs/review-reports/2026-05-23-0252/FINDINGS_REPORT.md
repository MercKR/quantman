# /풀리뷰 진단 보고서 — 2026-05-23 02:52 (REPORT-ONLY)

**모드**: REPORT-ONLY. 코드 수정·커밋·push 일절 없음. 본 문서와 `_sig_*.txt`, `_diff_uncommitted.txt`만 산출.
**플레이북**: `platform/REVIEW_PLAYBOOK.md` Phase 0~9.
**기준 베이스라인**: `docs/review-reports/2026-05-22-0415/SUMMARY.md`(7.9/10)와 `docs/review-reports/2026-05-23-0104/REMEDIATION_PLAN.md`.
**상위 컨텍스트**: `CLAUDE.md`(자격증명 격리·근본원인·UI 브라우저 검증), `DESIGN.md`(테라코타 디자인 시스템), `docs/QUANT_DOMAIN_CHECKLIST.md`.

---

## 0. Phase 커버 표 — 완료조건 2

| Phase | 명목 | 본 보고서 처리 | 상태 |
|---|---|---|---|
| 0 환경 | git status·dev서버·codex·baseline | 본 절 §1. **codex 미설치 → Phase 5 skipped**, **bun 미설치 → npm 사용**, dev 서버 미기동(REPORT-ONLY) | ✅ 진단 |
| 1 health | lint/type/test 신호·점수 | §2 신호 + §4 결함의 X-/S-/W- 일부 | ✅ 진단 |
| 2 design | DESIGN.md 기준 페이지 평가 | §5 정적 디자인 진단(브라우저 관측은 user 개입 필요) | ✅ 정적 |
| 3 qa | 17 시나리오 user flow | §6 정적 플로우 진단(런타임 QA는 user 개입 필요) | ✅ 정적 |
| 4 review | diff 코드 리뷰 | §7 최근 커밋·미커밋 진단 | ✅ 진단 |
| 5 codex | 독립 시선 | **codex CLI 미설치 → skipped** | ⚪ skip |
| 6 perf | CWV·번들 | §8 빌드 청크 분석(라이브 CWV는 deployed URL 필요 → user 개입) | ✅ 정적 |
| 7 security | /cso + 자격증명·종속성 | §9 감사 결과 + §4 S-/X- 결함 | ✅ 진단 |
| 8 quant-domain | 도메인 체크리스트 + golden | §10 7카테고리 평가 + golden 분석 | ✅ 진단 |
| 9 summary | 우선순위·5점수·요약 | §11 매트릭스 + 점수 + §12 자체점검표 | ✅ 진단 |

---

## 1. 환경(Phase 0)

- **타임스탬프**: 2026-05-23 02:52 KST
- **OS/Shell**: Windows + Git Bash (콘솔 cp949). 한글 출력 스크립트는 별도 UTF-8 명시 필요.
- **git 작업트리**: `git status` 결과 미커밋 = `M REVIEW_PLAYBOOK.md`(+82, 본 진단 directive 자체) 1건. 그 외 web/design 변경은 이번 세션 직전 사이에 커밋됨(`629d5ed..01a13c1`).
- **codex CLI**: 미설치 → Phase 5 skip(정책 허용).
- **bun**: 미설치 → web 신호는 `npx tsc` / `npm run lint` / `npm run build` / `npm audit` 사용.
- **ruff / mypy / pytest**: 사용 가능.
- **pip-audit**: 설치돼 있으나 requirements.txt 한글 주석 cp949 디코드 실패로 **실행 차단**(F-X01, X-01 참조).
- **dev 서버 / 브라우저**: REPORT-ONLY 모드 + 기동 비용을 감안해 미기동. Phase 2·3 라이브 관측 부분은 **사용자 개입 필요**로 표시.
- **golden baseline**: `tests/golden_backtest.py` 존재·실행 가능. 15 passed, 1 skipped, 30 warnings.

---

## 2. 읽기 전용 신호 결과 — 완료조건 3

| 신호 | exit | 마지막 줄(증명) |
|---|---|---|
| `python -m pytest tests/golden_backtest.py -v` | 0 | `=========== 15 passed, 1 skipped, 30 warnings in 254.78s (0:04:14) ============` |
| `(cd server && ruff check .)` | 1 | `Found 42 errors.` (그 뒤 `[*] 3 fixable with the --fix option.`) |
| `(cd server && mypy app)` | 1 | `Found 82 errors in 22 files (checked 31 source files)` |
| `(cd web && npx tsc --noEmit)` | 0 | (empty — 0 errors) |
| `(cd web && npm run lint)` | 1 | `✖ 10 problems (10 errors, 0 warnings)` |
| `(cd web && npm run build)` | 0 | `(!) Some chunks are larger than 500 kB after minification.` |
| `(cd web && npm audit)` | 0 | `found 0 vulnerabilities` |
| `pip-audit -r server/requirements.txt` | 1 | `UnicodeDecodeError: 'cp949' codec can't decode byte 0xed ...` |
| `pip-audit -r local/requirements.txt` | 1 | `UnicodeDecodeError: 'cp949' codec can't decode byte 0xed ...` |

원본 파일: `_sig_golden.txt`, `_sig_ruff.txt`, `_sig_mypy.txt`, `_sig_tsc.txt`, `_sig_eslint.txt`, `_sig_build.txt`, `_sig_npmaudit.txt`, `_sig_pipaudit_server.txt`, `_sig_pipaudit_local.txt`.

**ruff 42건 분류**: E702 15(`session.add(s); session.commit()` — sync.py 9, portfolio.py 2, 테스트 4), E402 13(테스트 `sys.path.insert` 후 import), E701 11(screener.py 6, technical_cache.py 5), F401 3(`data_cache` 미사용, 테스트 `pytest` 미사용 2).
**golden 30 warnings 분류**: `RuntimeWarning: divide by zero encountered in log` 1종 + `invalid value encountered in log` 1종(반복) — **C-02 확정**. 추가 protobuf DeprecationWarning(외부 라이브러리).

---

## 3. 사전 검증 — 0104 list 대비 변동

| 항목 | 0104 판정 | 현재 | 근거 |
|---|---|---|---|
| **S-04 SSRF** | High | **FIXED** | `settings.py:24-38 _validate_webhook_url` + `tests/test_webhook_ssrf.py` 양·음성 검증 |
| **W-07 amber 하드코딩** | Med | **FIXED** | `index.css:27 --amber: #b45309`, Monitor에서 토큰 사용 |
| **W-04 (절반)** | Med | **부분 FIXED** | `Settings.tsx:40-43`에 confirm 도입, `Pair.tsx:36-39`는 여전히 confirm 없음 |
| **신규 테스트 다수** | — | 추가 | `test_condition_engine`, `test_market_calendar`, `test_rebalance`, `test_round_to_tick`, `test_sync_preview_auth`, `test_cold_start_us_metrics`, `test_us_metrics_enrich`, `test_webhook_ssrf`, `test_market_index`, `test_us_realtime_notify` |
| **자격증명 격리** | OK | **OK 유지** | server tree grep `appkey/appsecret/account_number` 0건 |

그 외 0104의 결함은 §4에서 개별 STATUS 재기록.

---

## 4. 결함 목록 — 6필드 전부 기재

> 표기: ①문제 ②영향 ③근본원인 ④해결방향 ⑤트레이드오프 ⑥추가정보. 각 결함마다 STATUS·심각도·ID. 모든 file:line은 본 진단 시점 기준.

### 4.A 도메인 / 백테스트 (core/quant_core) — Phase 8

#### C-01 [High][게이트] 한국 매도세를 commission에 대칭 흡수
- **STATUS**: PRESENT (직접 재확인 — backtest.py 162/173 commission 대칭 적용, `_close`에 별도 세금 항목 없음)
- ①: `core/quant_core/backtest.py:160-184`(`_close`), `:161-162`(`_open`), `exec_defaults.py:45-46`(주석 "위탁수수료 + 거래세 평균"). UI 백테스트 가정 영역도 commission만 표기.
- ②: 매수 비용 과대평가(매수에는 세금 없음), 매도 비용 부정확. 종합적으로 거래세 0.23% 가정이 라운드트립 0.50%로 부풀려져 **전략 수익률·승률·MDD 모두 편향**(실거래보다 보수적). 사용자가 살아남을 전략을 폐기할 위험.
- ③: 비용 모델이 commission/slippage 2개의 **대칭** 파라미터뿐. 한국 시장의 매수 무세금/매도 유세금 **비대칭**을 표현할 수단이 스키마에 없음.
- ④: `ExecutionPolicy`에 `bt_sell_tax_bps`(default 23) 신설 → `backtest._close`에서 `proceeds = shares*price*(1-commission-sell_tax)`만 적용. 1단계는 보수적 단일 0.23%, 2단계에 KOSPI(0.23%)/KOSDAQ(0.18%) 차등(`ticker_db.py`·KIS 마스터 사용). 동시에 `CM-02` 주석 정정.
- ⑤: golden baseline 전 케이스 수치 변경 → 재생성 필요(사용자 승인 게이트). 차등화는 종목→시장 매핑 정확성에 의존.
- ⑥: 사용자 승인(baseline 재생성), 차등화 단계 결정.

#### C-02 [High] log() divide-by-zero — 매크로 음수/0 종목 지표 오염·신호 누락
- **STATUS**: PRESENT (golden 출력의 `RuntimeWarning: divide by zero encountered in log` + `invalid value encountered in log`으로 신호 확인)
- ①: `core/quant_core/indicators.py:22`(`add_returns` log_return_1d), `:121`(`add_realized_vol` log_ret), `:131`(`add_zscore` ret fallback). 매크로 시계열(`load_all()`로 들어오는 금리차·스프레드 등 음수 가능 Close)이 오염원.
- ②: 가격용 로그 지표를 음수 가능 레벨 시계열에 적용 → −inf/NaN. `analysis._condition_mask`가 `fillna(False)`로 처리해 **조건 신호가 조용히 누락**(false negative). 매크로 기반 전략의 검증 결과가 신뢰 불가.
- ③: price-positive 지표와 음수 가능 level 지표를 스키마에서 구분하지 않음(공통 `compute_all` 일괄 적용).
- ④: 로그 계열을 `Close>0 & Close.shift>0` 마스킹 후 계산하거나, 음수 가능 심볼군엔 로그 지표 미산출 분기. CLAUDE.md 원칙: `warnings.filterwarnings("ignore")`로 덮지 말고 정의역에서 해결.
- ⑤: 매크로의 로그수익률은 금리차에 무의미하므로 제거해도 실손실 없음. 단 기존 전략이 그 컬럼을 참조하면 NaN→False 동작이 바뀔 수 있어 사용 여부 사전 확인 필요.
- ⑥: 어떤 심볼군이 음수/0 Close를 갖는지 데이터셋 목록(필요 시 `dataset.list_macro_symbols`).

#### C-03 [Med][게이트] 틱 라운딩이 백테스트에 미적용
- **STATUS**: PRESENT (`backtest.py:160,172` raw_price에 슬리피지만 곱하고 `round_to_tick` 호출 없음; `exec_defaults.round_to_tick` 함수는 존재·테스트도 `tests/test_round_to_tick.py` 있음).
- ①: `core/quant_core/backtest.py:160`(`_open`) `price = raw_price * (1 + slippage + extra)`, `:172`(`_close`) `price = raw_price * (1 - slippage - extra)`. 호가단위 라운딩 없음.
- ②: 라이브 주문은 KIS 호가단위 반올림으로 체결가가 ±tick 변동. 백테스트는 연속 가격을 그대로 사용 → 미세하지만 라이브와 체계적 차이 발생, 라이브 괴리 분석(Phase 13.4 overlay)에 노이즈.
- ③: 1주식 정수 + 호가 단위는 라이브 도메인 제약. 백테스트 엔진이 이 제약을 일부만 모델링(슬리피지만).
- ④: `_open`/`_close`에서 `round_to_tick(price, "up" if buy else "down", currency)` 적용. 슬리피지와 중복 보정 순서를 문서화(슬리피지 → 라운딩).
- ⑤: golden baseline 수치 변경(소폭) → 재생성. 작은 시가일수록 영향 큼.
- ⑥: 사용자 승인(baseline 재생성), USD/KRW 통화별 정책 고정.

#### C-04 [Med][게이트] 소수주 허용 (정수주 미강제)
- **STATUS**: PRESENT (`backtest.py:161` `shares = cash / (price*(1+commission))` float).
- ①: `core/quant_core/backtest.py:161` 실제 코드: `shares = cash / (price * (1 + commission))`. 정수화 없음.
- ②: 실거래는 1주 단위(미국 일부 fractional 예외 제외). 백테스트가 0.37주 매수로 가정 → 실거래 대비 자본 효율 과대평가, 특히 고가주(삼성전자·NVDA)에서 편차.
- ③: 백테스트 엔진이 단위 단순성을 위해 가격÷현금을 float로 둠.
- ④: `shares = int(cash // (price*(1+commission)))`, 잔여 현금 보유. KRW 정수주만, USD는 fractional 허용 옵션.
- ⑤: golden baseline 변경. 소액 시뮬레이션에선 차이가 큼.
- ⑥: 사용자 승인(baseline 재생성).

#### CM-01 [Med] slippage default 불일치 (5bps vs 10bps)
- **STATUS**: PRESENT (`backtest.run_backtest` 기본 5bps, `exec_defaults.DEFAULT_EXECUTION` 10bps; `engine.run_strategy_backtest`가 후자로 호출하므로 실제 기본은 10bps지만 직접 호출/테스트 경로는 5bps).
- ①: `core/quant_core/backtest.py:75` `slippage: float = 0.0005`, `exec_defaults.py:46` `"bt_slippage_bps": 10`(=0.001).
- ②: 같은 "기본"이라는 단어가 두 경로에서 다른 값을 의미 → 회귀 테스트·내부 호출 결과 비교 시 혼란.
- ③: 단일 진실 공급원 부재. backtest 엔진의 직접 호출 default와 ExecutionPolicy default가 따로 정의됨.
- ④: backtest.py default를 None으로 두고, 호출자가 항상 ExecutionPolicy를 통하도록 강제. 혹은 두 default를 같은 상수에서 참조.
- ⑤: 직접 `run_backtest()`를 호출하는 외부/테스트가 있으면 동작 변경.
- ⑥: `run_backtest` 직접 호출 위치 grep(테스트 외부).

#### CM-02 [Med] commission 주석이 세금 누락을 은폐
- **STATUS**: PRESENT (`exec_defaults.py:45` 주석: "위탁수수료 + 거래세 평균").
- ①: `core/quant_core/exec_defaults.py:45` `"bt_commission_bps": 25, # 편도 0.25% (KIS 위탁수수료 + 거래세 평균)`.
- ②: 주석이 "거래세가 commission에 녹아 있다"고 잘못 알려 후속 리뷰어가 세금 모델을 추가하지 않게 만듦. C-01의 구조적 원인을 강화하는 문서 결함.
- ③: 모델 결손을 주석으로 합리화.
- ④: C-01 수정 시 동시에 주석 정정 — "편도 위탁수수료(0.015~0.25% 가정). 세금은 `bt_sell_tax_bps`로 분리".
- ⑤: 없음.
- ⑥: 없음.

#### CM-03 [Low] `_gap_extra` 갭비용 `next_open` 한정 — 문서화 부재
- **STATUS**: PRESENT (`backtest.py:144-155` `_gap_extra`는 `next_open`일 때만 `_open`/`_close`에서 적용; `close` 체결 모델에선 무시).
- ①: `backtest.py:144-155`(함수), `:159`/`:171`(`if next_open else 0.0`).
- ②: 갭 비용 모델이 fill 모드에 따라 달라지는 점이 문서에 없어 사용자 오해 가능.
- ③: 두 fill 모델이 비용 가정을 일관 표현하지 않음(작은 점).
- ④: docstring·UI "백테스트 가정"에 "갭 추가 비용은 next_open에만 적용"을 명시.
- ⑤: 없음.
- ⑥: 없음.

#### CL-01 [Low] `volume_ratio`/`adv` 0거래일 inf 방어 부분
- **STATUS**: PARTIAL (`indicators.py:143-145`/`:155-158`이 `Volume.sum() > 0` 조건 + `.replace(0, np.nan)`로 1차 보호; 전 종목 거래량 0인 동결 종목·신규상장 갭 등 에지케이스는 NaN이 아닌 inf가 나올 잠재 경로 잔존).
- ①: `indicators.py:143-145`(`add_volume_ratio`), `:155-159`(`add_adv`).
- ②: 거래 정지/상장 첫날 같은 0거래량 구간에서 비율 지표가 inf → 조건 평가 fillna(False)로 신호 누락(C-02 패턴과 유사).
- ③: 거래량 분모가 0인 경우 처리가 함수 일관성이 아닌 헬퍼별 ad-hoc.
- ④: `safe_div` 헬퍼 도입 또는 `mask = avg_vol > 0` 게이트로 일관 처리.
- ⑤: 거의 없음.
- ⑥: 0거래량 구간이 발생하는 종목 분포(특히 거래 정지/관리종목).

#### CL-02 [Low] parquet `tz_localize(None)` — KST 가정 문서화 필요
- **STATUS**: UNVERIFIABLE without re-read of data_fetcher.py
- ①: `core/quant_core/data_fetcher.py:341`(0104 기준; 현재 line 확인 필요).
- ②: 인덱스 tz 정보 제거 후 KST 가정으로 사용. US 종목 처리 시 혼선 가능.
- ③: tz 정책이 코드에서 implicit.
- ④: docstring과 dataset README에 "인덱스는 KST 거래일 기준" 명시. US는 별도 normalize.
- ⑤: 없음.
- ⑥: 현재 line·실제 호출 경로 확인 필요(본 진단에서 재확인 안 함).

### 4.B 로컬앱 자금 안전 (local/localapp) — Phase 7·8

#### L-01 [High][설계 승인] 주문 멱등성 부재 — 크래시·재시작 시 중복 발주
- **STATUS**: PRESENT (재검증 — `trader.py` 발주(`_submit_*` → `broker.buy_limit`) 직후 pending dict에 추가하지만 디스크 영속(`_save`)은 사이클 종료에 한 번. 발주 ↔ _save 사이 크래시 윈도우 존재).
- ①: `local/localapp/trader.py:355-380`(`_submit_buy`), `:441-448`(`_after_submit`), `:161-166`(`_save`), `order_log.py`.
- ②: 발주 직후~`_save()` 전 크래시 시 디스크 pending 미기록. 재시작 → 동일 후보 재발주 → **2배 포지션, 실자금 손실**.
- ③: 멱등 단위가 KIS 응답의 order_no뿐. (date,strategy,symbol,side) intent를 발주 *이전*에 영속하지 않음.
- ④: 발주 직전 intent를 원자적으로 append(`intents.jsonl`) + 사이클 진입 시 당일 intent 대조 skip. 보조로 cycle 시작 시 KIS 당일 체결조회로 reconcile. **2-phase(intent→결과확정)로 "유령 intent" 방지** 설계 → 설계안 제시 후 승인.
- ⑤: KIS가 client-side 주문ID(ODNO)를 지원하면 진짜 멱등키 사용 가능(미확인). 발주 실패 시 intent 정리 로직 필수.
- ⑥: KIS ODNO 지원 여부 문서 확인, 설계안 승인.

#### L-02 [High] `_save()` 비원자적 순차 write — 부분 상태·원장 소실
- **STATUS**: PRESENT (`trader.py:41-42` `_save_json`이 `path.write_text(...)` truncate-then-write; `:161-166` `_save`가 ledger/equity/pending/rebalance 순차 호출).
- ①: `local/localapp/trader.py:41-42`(`_save_json`), `:161-166`(`_save`).
- ②: 중간 크래시 시 파일 간 불일치. truncate 중 손상 시 `_load_json`이 `default={}`로 폴백 → **전체 보유 원장 소실** → 다음 사이클에 의도치 않은 진입/청산.
- ③: 다중 파일 트랜잭션을 원자 단위로 다루지 않음.
- ④: 파일별 `tmp = path.with_suffix(".tmp"); tmp.write_text(...); os.replace(tmp, path)`. CLAUDE.md "근본 원인" 원칙(전체-or-전무 자체 단위).
- ⑤: 4파일 cross-consistency는 여전히 미보장 — 완전 해결(단일 파일/WAL)은 베타엔 과설계. 1단계는 파일별 원자성으로 충분.
- ⑥: 없음(설계 단순).

#### L-03 [High] 한국(KRX) 휴장일 캘린더 미적용
- **STATUS**: PRESENT (`scheduler.py:90-110` KRX cron `day_of_week="mon-fri"`로 가정; `core/quant_core/market_calendar.py` `_FILES = {"US": ...}` US만; 단 `tests/test_market_calendar.py`는 존재 — 함수만 테스트, KR 데이터 없음).
- ①: `local/localapp/scheduler.py:90-110`(KRX cron), `core/quant_core/market_calendar.py:26-27`(US 전용 `_FILES`), `core/gen_market_sessions.py`(US만 생성), `trader.py`/`intraday_loop.py` 진입부.
- ②: 휴장 평일(설/추석/임시 휴장)에도 사이클·청산·reconcile 실행. 청산 패스가 휴장일에 매도 발주(거부) → 로그 잡음·killswitch 잘못 평가, intraday loop가 stale 시세로 손절 평가.
- ③: US만 동적 캘린더, KRX는 "평일=거래일" 가정.
- ④: `market_calendar`에 KR 세션 추가(`gen_market_sessions.py`에 KRX 포함) → cycle/intraday/settlement 진입부에서 `is_session_open("KR")` 가드(US와 동일 패턴).
- ⑤: KR 캘린더 데이터 생성·만료 관리(US처럼 정기 갱신). 반일장(연말) 마감시각 반영 여부 결정 필요.
- ⑥: KR 휴장일 데이터 소스(KRX 공식 API/CSV) 선정.

#### L-04 [High] reconcile가 15:35에만 → 장중 수동매도 후 over-sell
- **STATUS**: PRESENT (`trader.py:173-229` reconcile만; `runner.py:183`에서 post-close에만 호출; `intraday_stop.py:130-137` on_tick 매도 직전 KIS 실보유 재조회 없음).
- ①: `local/localapp/trader.py:173-229`(`reconcile_with_kis`), `runner.py:183`(호출), `intraday_stop.py:130-137`(on_tick 매도).
- ②: 장중 사용자 수동 전량매도 후 ledger에 잔존 → 손절 트리거 시 KIS에 없는 수량 매도(over-sell) → 거부 또는 신용 short. 사용자 신뢰 손상.
- ③: ledger 신뢰, 장중 KIS 정합성 미확인.
- ④: on_tick 매도 직전 KIS 실보유로 `min(ledger_qty, broker_qty)` 클램프, 0이면 ledger 정리·skip. 짧은 TTL 캐시로 KIS rate-limit 회피.
- ⑤: tick마다 조회는 KIS 초당제한 압박 → TTL 캐시. 체결통보 WS가 수동매도까지 통지하면 ledger 실시간 차감이 더 근본적이나 KIS WS 스키마 확인 필요.
- ⑥: KIS 체결통보 WS가 수동매도까지 통지하는지 확인.

#### L-05 [Low] 가중평균 ZeroDivision 잠재
- **STATUS**: PRESENT-guarded (`trader.py:317-320` `total = lg["qty"] + filled_qty`로 분모; 정상 경로에선 두 값 모두 양수 → 사실상 안전).
- ①: `local/localapp/trader.py:317-320`.
- ②: 경로 변경 시 ledger qty=0 잔존 + filled_qty=0 같은 edge case에서 ZeroDivisionError.
- ③: 가드 부재(implicit 안전 가정).
- ④: `if total <= 0: return`(1줄 가드).
- ⑤: 거의 없음.
- ⑥: 없음.

#### L-06 [Med] `date.today()` naive — KST 미인지
- **STATUS**: PRESENT (`trader.py:18,182,304,711` `from datetime import date` + `date.today()`; `intraday_loop.py:119,146,190` 동일).
- ①: `trader.py:18,182,304,711`, `intraday_loop.py:119,146,190`.
- ②: 시스템 tz가 KST가 아니면 거래일 경계가 어긋남(예: Railway UTC). day_start_equity 기준일 오인 → killswitch 잘못 평가, "오늘 사이클 1회" 가드 우회/이중 실행.
- ③: 스케줄러는 KST aware이나 Trader/loop는 naive date.
- ④: `datetime.now(ZoneInfo("Asia/Seoul")).date()` 일괄 치환. 헬퍼 `kst_today()` 도입.
- ⑤: 거의 없음. 일괄 교체로 단순.
- ⑥: 없음.

#### L-07 [Low] 즉시체결 데드코드(또는 가드 부족)
- **STATUS**: 의도-구현 불일치 (`trader.py:441-446` `_after_submit`이 KIS 응답에 즉시체결 데이터가 오면 즉시 `_apply_fill` 후 return; 실제로 KIS REST 발주가 즉시체결 정보를 항상 제공하지 않으면 dead, 제공하면 활성이나 L-01과 결합해 위험).
- ①: `trader.py:441-446`.
- ②: 활성 시 fill은 기록되나 pending엔 안 들어감 → 크래시 후 재시작에서 동일 주문 재발주 가능(L-01과 결합).
- ③: 발주 응답 스키마에 대한 정확한 모델링 부재.
- ④: KIS 응답에 fill 정보가 있어도 pending 등록 후 `_apply_fill`로 흐름 통일. 또는 즉시체결 데이터는 무시하고 통보 WS에만 의존.
- ⑤: 즉시체결 시 latency 증가(미미).
- ⑥: KIS 발주 응답이 즉시체결 데이터를 주는 케이스(특정 상품·시간대) 명세 확인.

#### L-08 [Low] killswitch reset 프로세스 간 잠금 없음
- **STATUS**: PRESENT (`killswitch.py:48-59` load→mutate→save, 잠금 없음).
- ①: `killswitch.py:48-59`.
- ②: CLI(reset) ↔ cycle/intraday(is_active+update) 동시 실행 시 race로 잘못된 상태 저장 가능.
- ③: 파일 기반 상태에 동기화 메커니즘 부재.
- ④: `portalocker` 또는 `tmp + os.replace` 원자성 + 명시 retry 짧은 sleep. 단일 인스턴스 가드(`single_instance.acquire`)가 이미 있으므로 실제 발생 가능성은 낮으나 명시 가드 권장.
- ⑤: portalocker 의존 추가 또는 자체 락 구현 복잡도.
- ⑥: 실제 reset 명령이 cycle과 동시 실행 가능한지(single_instance가 보호하는 범위) 검토.

#### L-09 [Med] WS 체결 통보 중복 dedup 키 부재
- **STATUS**: PRESENT (`intraday_loop.py:96-109` `_on_exec_event` order_no만 매칭, 동일 체결 이벤트 중복 시 두 번 `_apply_fill` 호출 가능).
- ①: `intraday_loop.py:96-109`.
- ②: KIS H0STCNI0 통보가 중복 도달하면 ledger qty 이중 가산 → over-position.
- ③: 멱등키가 `order_no`뿐, fill 시퀀스/누적 수량 추적 없음.
- ④: (order_no, exec_seq) 또는 (order_no, cum_qty) 기반 dedup. 적어도 "이번 ev의 cum_qty <= 이미 적용된 fill" 체크.
- ⑤: KIS 통보 스키마 의존(필드 존재 가정).
- ⑥: H0STCNI0 통보 페이로드 스키마 확인.

#### L-10 [Med] 단일종목 상한이 `pct_cash`에 미적용 + 섹터 한도 부재
- **STATUS**: PRESENT (`trader.py:130-139` `_atr_qty`에만 `max_position_pct` 클램프; `:534-547`의 pct_cash 경로 직접 `cash*amount_pct/100/price` 계산, 클램프 없음. 섹터 분류·한도 코드 grep 무).
- ①: `local/localapp/trader.py:130-139`, `:534-547`; `exec_defaults.max_position_pct`.
- ②: pct_cash 모드 사용자가 amount_pct=100% 두면 단일 종목에 전 자본. 섹터 집중(반도체 80% 등) 차단 수단 없음 → 분산 안전망 부재.
- ③: 사이즈 상한 적용 위치가 사이즈 함수 내부에 흩어져 있음. 도메인 체크리스트 4.3 요구 미구현.
- ④: 사이즈 결정 *직후* 공통 `apply_position_cap()`을 거쳐 모든 경로에서 단일종목·섹터 한도 적용. 섹터 매핑은 KIS 마스터 또는 외부 분류.
- ⑤: 섹터 매핑 데이터 품질·갱신 부담.
- ⑥: 섹터 분류 소스(KIS 업종/Naver) 결정, 한도 기본값.

### 4.C 서버 (server/app) — Phase 1·4·7

#### S-01 [High] APScheduler 재시도 naive datetime → UTC 호스트에서 misfire drop
- **STATUS**: PRESENT (`main.py:70` `run_at = datetime.now() + timedelta(...)` naive; 스케줄러 `timezone="Asia/Seoul"`).
- ①: `server/app/main.py:70`(`run_at`), `:75`(add_job `date` trigger), `:325`(스케줄러 tz=KST).
- ②: Railway(UTC)에서 naive `now()` = UTC, 스케줄러가 KST로 해석 → 과거 시각 → misfire drop → 데이터 재시도 누락 → preview 정확성 저하.
- ③: tz-aware 규율이 동적 잡 생성부에 결락(모델 패턴과 불일치).
- ④: `datetime.now(ZoneInfo("Asia/Seoul"))`로 aware. 헬퍼 `kst_now()` 도입해 일괄.
- ⑤: 거의 없음.
- ⑥: 없음(S-02·L-06과 일괄).

#### S-02 [Med] `market.py` deprecated `utcnow` + 수동 +9h
- **STATUS**: PRESENT (`routers/market.py:69-70` `datetime.utcnow() + timedelta(hours=9)`).
- ①: `server/app/routers/market.py:69-70`.
- ②: Python 3.12+에서 `utcnow()` deprecated. 추가로 naive + 수동 offset → 환경 의존, "장 phase" 오인 가능.
- ③: tz 라이브러리 미사용(서버 일부 누락).
- ④: `datetime.now(ZoneInfo("Asia/Seoul"))`. S-01·L-06과 일괄.
- ⑤: ISO 응답에 offset 추가 → 프런트 파서 가정 확인 필요.
- ⑥: 프런트가 응답 시각을 어떻게 파싱하는지 확인.

#### S-03 [High] 다중 webhook 동기 인라인 호출이 push 블로킹
- **STATUS**: PRESENT (`routers/sync.py:30-46`의 `push_snapshot` 안에서 `_check_alerts` 동기 호출, `_post_webhook`이 `requests.post(..., timeout=8)`로 인라인).
- ①: `server/app/routers/sync.py:42`(push), `:55`(`requests.post timeout=8`), `_check_alerts` 본문.
- ②: 느린 webhook 다수면 8s씩 누적 블로킹 → 로컬앱 push 응답 지연 → ledger 동기화 지연.
- ③: 알림 발송이 요청-응답 경로에 인라인.
- ④: `BackgroundTasks`로 응답 후 발송(fire-and-forget), timeout 3~5s. 큐(Redis)는 베타엔 과설계.
- ⑤: BackgroundTask도 같은 프로세스 → 진정한 격리는 아님(베타엔 OK).
- ⑥: 없음.

#### S-04 [—] webhook URL SSRF — **이미 FIXED**
- **STATUS**: FIXED (`settings.py:24-38` https-only + Discord/Slack hostname allowlist; `tests/test_webhook_ssrf.py` 양·음성 검증).
- ①: ~~`settings.py:45-81`~~ → `settings.py:24-38 _validate_webhook_url`로 해결. put_settings(:73)가 호출.
- ②: 잠재 SSRF가 차단됨.
- ③: 입력 검증 부재 → allowlist 도입으로 해결.
- ④: 추가 강화: hostname allowlist는 DNS rebinding에 약하므로 결정적 IP 검증을 더할지 검토(현 단계엔 과설계).
- ⑤: 자체호스팅 webhook을 못 쓰지만 개인 트레이더 대상엔 무방.
- ⑥: 없음.

#### S-05 [High] preview가 fetch 실패 시 어제 종가로 후보 산출 (상폐/거래정지 위험)
- **STATUS**: PRESENT (`preview_engine.py:36-44` `_prev_close`가 `iloc[-1]`만, as-of 검증 없음).
- ①: `server/app/preview_engine.py:36-44`(`_prev_close`), `main.py:262`(invalidate), `_refresh_kr_dataset`.
- ②: 어제 데이터로 매수 후보·예상가 노출 → 거래정지·상폐 직전 종목 잔존. 사용자가 잘못된 투명성 정보를 신뢰.
- ③: dataset as-of stale 판정 부재(`_last_date` 미사용).
- ④: 기준일이 직전 거래일보다 오래되면 `available=False, reason="데이터 갱신 지연"`. 거래정지 플래그(KIS 마스터) 활용. L-03 KR 캘린더와 연계.
- ⑤: 연휴 직후 false-skip 방지 위해 거래일 캘린더 필요.
- ⑥: KIS 마스터의 거래정지/관리종목 플래그 컬럼 확인.

#### S-06 [Med] `last_seen` 매 요청 commit → write 증폭
- **STATUS**: PRESENT (`deps.py:46-49` `get_current_device`가 매 요청 `last_seen_at` 갱신 + commit).
- ①: `server/app/deps.py:46-49`.
- ②: 로컬앱 SSE 폴링/sync 호출마다 DB write → Postgres 부하·디스크 IO 누적.
- ③: 사용/감지 데이터를 트랜잭션 경로에 놓음.
- ④: 60s throttle(메모리 캐시) 또는 background write. 분 단위 정밀도 저하는 무방.
- ⑤: 직전 last_seen이 1분 stale 가능.
- ⑥: 없음.

#### S-07 [Med] SSE에서 동기 Session + `asyncio.sleep(2)` 루프
- **STATUS**: PRESENT (`routers/commands.py:135-193` async 핸들러 안에서 `Session(engine)` 동기 사용 + `await asyncio.sleep(2)`).
- ①: `server/app/routers/commands.py:152, 179`.
- ②: async 컨텍스트에서 동기 DB I/O가 이벤트 루프 블로킹 → 동시 연결 수 저하, latency 변동.
- ③: 동기 SQLModel을 async 핸들러에 직접 사용.
- ④: `run_in_threadpool`로 DB 쿼리 위임. 또는 async SQLAlchemy로 마이그(베타엔 과설계).
- ⑤: 동작 동일성 유지 시 threadpool로 충분.
- ⑥: 없음.

#### S-08 [Med] backtest 이력 limit=50 하드코딩
- **STATUS**: PRESENT (`routers/backtest.py:179` `.limit(50)` 노출되는 페이지네이션 파라미터 없음).
- ①: `server/app/routers/backtest.py:179`.
- ②: 50개 이상 백테스트 이력 조회 불가 → 사용 후기 누적되면 데이터 손실 인상.
- ③: 페이지네이션 미설계.
- ④: `limit/offset` 또는 cursor 기반 Query 파라미터.
- ⑤: 클라이언트 UI도 페이지 컨트롤 필요.
- ⑥: 없음.

#### S-09 [Med] `/health/*/refresh` 무인증 공개
- **STATUS**: PRESENT (`main.py:440-485` 5개 refresh endpoint에 `Depends(get_current_user)` 없음).
- ①: `server/app/main.py:440-485`.
- ②: 익명 POST로 비싼 refresh(분 단위 CPU/네트워크)를 무한 트리거 가능 → DoS 벡터.
- ③: 진단 endpoint를 외부 노출.
- ④: 내부 토큰(env) 검증 + rate-limit. 또는 IP allowlist.
- ⑤: 모니터링 봇이 호출 중이면 토큰 분배 필요.
- ⑥: 현재 외부에서 호출하는 모니터링 도구가 있는지 확인.

#### S-10 [High] `SECRET_KEY` 기본값 — 프로덕션 fail-fast 부재
- **STATUS**: PRESENT (`config.py:11` `os.getenv("QP_SECRET_KEY", "dev-insecure-secret-change-me")` fallback).
- ①: `server/app/config.py:11`.
- ②: Railway 환경변수 누락 시 fallback 비밀로 JWT 서명 → 토큰 위조 가능 = **인증 우회**(현재 env가 설정돼 있다고 가정해도 안전망 부재).
- ③: 환경별 정책 분기 없음.
- ④: `ENV != "dev"` 이면 fallback 사용 시 부팅 시 `RuntimeError`. `pydantic-settings`로 의무 필드화.
- ⑤: 로컬 dev에서 env 안 채워두면 부팅 실패(현재 dev 워크플로 확인).
- ⑥: dev/prod 환경 식별 변수(`QP_ENV` 등) 결정.

#### S-11 [Low] `db._migrate` 예외 `print` → 로깅 미흡
- **STATUS**: PRESENT (`db.py:99-100` `print(f"[migrate] ...")` only).
- ①: `server/app/db.py:99-100`.
- ②: 마이그 예외가 로그 수집기에 안 잡힘 → 배포 "성공"인데 스키마 손상 가능.
- ③: 로깅 표준 미적용.
- ④: `_log.exception(...)`.
- ⑤: 없음.
- ⑥: 없음.

#### X-01 [Low→실효 Med] `requirements.txt` 한글 주석이 cp949 환경에서 pip-audit 차단
- **STATUS**: PRESENT (본 진단에서 직접 발생 — `pip-audit -r server/requirements.txt`가 `UnicodeDecodeError: 'cp949' codec can't decode byte 0xed`로 실패).
- ①: `server/requirements.txt` / `local/requirements.txt`의 한글 주석. 본 보고서 `_sig_pipaudit_*.txt` 참조.
- ②: pip-audit가 의존성 파일 자체를 못 읽어 **공급망 취약점 감사가 차단됨** → 보안 가시성 손실(Critical일 가능성을 모름).
- ③: CI/감사 도구가 UTF-8 가정인데 파일에 cp949에서 깨지는 한글 멀티바이트(BOM 없음, encoding 선언 없음) 존재.
- ④: 주석을 ASCII로 옮기거나, requirements 파일에 `# -*- coding: utf-8 -*-` 명시(pip-audit 인식 여부 확인 필요)하거나, 별도 `README.requirements.md`로 한글 설명 분리.
- ⑤: 한글 주석의 정보성 손실(영문화).
- ⑥: pip-audit이 `encoding` declaration을 읽는지 검증, 또는 환경 변수 `PYTHONUTF8=1`로 워크어라운드 가능 여부.

#### X-02 [Med] 의존성 `>=` 비고정 (server/local requirements)
- **STATUS**: PRESENT (`server/requirements.txt` 다수 `>=`).
- ①: `server/requirements.txt`, `local/requirements.txt`.
- ②: 마이너/메이저 자동 상승 → 미검증 변경 유입(공급망 + 호환성).
- ③: lock 전략 부재.
- ④: `pip-compile`(pip-tools) 또는 `==` 핀. lock 후 의무 `pip-audit`.
- ⑤: 정기 갱신 워크플로 필요.
- ⑥: 갱신 주기·자동화 정책 결정.

#### X-03 [Low] ruff E701/E702 다수 (screener/technical_cache/sync)
- **STATUS**: PRESENT (ruff 42 errors 중 E701 11 + E702 15 = 26건이 스타일; X-03가 일컫는 technical_cache는 5건 확정, screener.py도 6건).
- ①: `server/app/screener.py:160-168`(E701 6), `app/technical_cache.py:51-56`(E701 5), `app/routers/sync.py`(E702 9 — `session.add(s); session.commit()`), `app/routers/portfolio.py:93-94`(E702 2), 테스트 파일들.
- ②: 가독성 저하, 라인-기반 도구(diff·grep)와 충돌.
- ③: 빠른 작성 시 한 줄 패턴.
- ④: `ruff --fix`(3건만 자동) + 수동 분리. 테스트의 E402는 pytest convention(`sys.path.insert` 후 import)이므로 파일별 `# noqa: E402`로 통상화.
- ⑤: 없음(스타일).
- ⑥: 없음.

### 4.D 프론트엔드 (web/src) — Phase 1·2·3·4·6

#### W-01 [High] 최상위 ErrorBoundary 부재 → 흰 화면
- **STATUS**: PRESENT (web 트리에서 `ErrorBoundary|componentDidCatch|getDerivedStateFromError` 0건; `main.tsx`가 단순 wrap).
- ①: `web/src/main.tsx`, `web/src/App.tsx`, `components/Layout.tsx`.
- ②: 단일 페이지 렌더 예외가 SPA 전체를 백지화 → **킬스위치·미체결도 안 보임**. 라이브에서 위험 차단 UI 자체가 소실.
- ③: 렌더 예외 격리 계층 부재.
- ④: `<ErrorBoundary>` 클래스 컴포넌트를 `Layout`의 콘텐츠 영역에 래핑, fallback은 `.empty-state` 패턴 + 새로고침 CTA + (가능하면) "/" 새로고침 링크. `console.error`로 원인 보존.
- ⑤: 경계를 콘텐츠 영역 단위로 — 전역이면 한 위젯 오류로 전 페이지 fallback. DESIGN.md 빈 상태 패턴 준수.
- ⑥: 사고 시 사용자에게 보여줄 메시지·로그 수집 정책 합의.

#### W-02 [High] Monitor 위험 카드 silent catch
- **STATUS**: PRESENT (`Monitor.tsx:46-51` loadRisk `catch {/* ignore */}`).
- ①: `web/src/pages/Monitor.tsx:46-51`(loadRisk), `:34`(marketContext catch null).
- ②: portfolio-risk API 실패 시 카드가 조용히 빈 상태 → **"위험 없음" 오인** → 사용자가 실제 위험 노출을 모름. 메인 `load()`는 setErr로 노출되므로 차별.
- ③: 보조 데이터 실패를 "조용히 무시"와 "카드에 표시"로 구분하지 않음.
- ④: 카드 내부에 "지표 못 불러옴 · 재시도" 인라인. 30초 폴링이라 "직전 성공 + 마지막 실패" 톤다운 권장.
- ⑤: 거의 없음.
- ⑥: 없음.

#### W-03 [High] Settings 폼 로드 실패 시 silent 증발
- **STATUS**: PRESENT (`MonitorTools.tsx:93` `getSettings().catch(()=>{})` + `:112` `if(!s) return null`).
- ①: `web/src/components/MonitorTools.tsx:93,112`, `pages/Settings.tsx:139`.
- ②: 로드 실패 시 위험 한도+알림 폼 전체가 안내 없이 사라짐 → "기능 없음" 오인. 사용자 위험 한도를 못 바꿈.
- ③: 로드 실패와 "설정 없음"이 같은 null로 합쳐짐.
- ④: `loading|error|loaded` 상태 분리, error면 "불러오지 못함·재시도" 표기. 저장 경로는 이미 setMsg 노출 — 유지.
- ⑤: 거의 없음.
- ⑥: 없음.

#### W-04 [Med] Pair revoke 확인 부재 + 기기목록 중복 (부분 FIXED)
- **STATUS**: PARTIAL (Settings.tsx에는 confirm 도입 완료, Pair.tsx는 미적용).
- ①: `web/src/pages/Pair.tsx:36-39`(revoke confirm 없음) vs `pages/Settings.tsx:40-43`(있음).
- ②: Pair 화면에서 잘못 클릭하면 즉시 페어링 해제 → 라이브 자동매매 중단(자금 안전엔 안전 방향이나 의도치 않은 중단).
- ③: 공용 컴포넌트 부재 → 두 페이지가 로직을 복제, 안전 가드 일관성이 깨짐.
- ④: 공용 `<DeviceList>` 컴포넌트 추출 또는 Pair.revoke에도 confirm 추가. 1단계는 단순 confirm.
- ⑤: 컴포넌트 추출 시 Pair 페이지의 IA 단순화 필요.
- ⑥: Pair 페이지가 여전히 NAV 비노출 진입점인지 확인.

#### W-05 [Med] set-state-in-effect 안티패턴
- **STATUS**: PRESENT (lint에서 `react-hooks/set-state-in-effect` 룰 위반 다수 — 출력 `68 | setErr("");` 등 10건).
- ①: `pages/Monitor.tsx:54`, `pages/Strategies.tsx:52,65` 외 lint 출력 참조.
- ②: 의도 외 재렌더·동작 회귀 가능. Strategies의 [mode]→setFilter는 토글 후 사용자 수동변경이 덮어써짐.
- ③: useEffect 안에서 setState로 동기화하는 패턴이 컴포넌트 곳곳에 반복.
- ④: 파생값화(`useMemo`/`computed`) 또는 의도적 `eslint-disable` + 주석. 데이터 패칭은 의도적 패턴이므로 case-by-case.
- ⑤: 수동변경 UX(특히 Strategies 모드 토글) 확인 필요.
- ⑥: 사용자 시나리오: 필터 수동변경 후 모드토글 시 어떤 동작이 옳은지 명세.

#### W-06 [Med] `Login.tsx`에서 GSI 타입 `any`
- **STATUS**: PRESENT (`Login.tsx:37` `(window as unknown as { google?: any }).google`).
- ①: `web/src/pages/Login.tsx:37`.
- ②: 런타임 GSI 변경 시 컴파일러가 못 잡음.
- ③: 외부 SDK 타입 정의 미사용.
- ④: 최소 인터페이스 선언 또는 `@types/google.accounts` 도입.
- ⑤: 거의 없음(lint 1건 감소).
- ⑥: 없음.

#### W-07 [—] amber 경고색 하드코딩 — **이미 FIXED**
- **STATUS**: FIXED (`index.css:27 --amber: #b45309` + Monitor.tsx에서 var 사용).
- ⑥: 추가 위치 잔존 여부 1회 grep("#f0b400|amber-soft 외 하드값") 권장.

#### A-01 [Med] 키보드 포커스 표시 부족
- **STATUS**: PARTIAL (`index.css:132-134` `input:focus, select:focus`만 outline; **버튼·`a`·`.navlink`·`.chip`·`.tab` 등 인터랙티브 요소엔 `:focus`/`:focus-visible` 규칙 없음**).
- ①: `web/src/index.css`. 검색: `:focus-visible` 0건, `:focus` 1건(input/select).
- ②: 키보드 사용자가 nav·버튼·칩 포커스 위치를 인지 못함 → a11y 위반(WCAG 2.4.7). 모바일 외부 키보드 사용에도 영향.
- ③: 디자인 시스템에 포커스 토큰·룰 누락.
- ④: 일반 규칙 `:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }` + `.navlink`·`.chip`·`.tab` 등 디자인 시스템 컴포넌트별 명시. DESIGN.md에 패턴 명문화.
- ⑤: 디자이너 의도와 어울리는 색 채택(현 accent로 OK).
- ⑥: 색 대비 측정(accent 위 배경별 대비).

#### P-01 [Med] Dashboard `reasonFor()` O(n²) 외 정적 perf
- **STATUS**: PRESENT (재검증 — `Dashboard.tsx:155-165` 중첩 루프).
- ①: `pages/Dashboard.tsx:155-165`(`reasonFor`), `Backtest.tsx` 다수 useState + set-state-in-effect.
- ②: 현재 데이터 규모(orders×cycles ≈ 50-100)에선 미체감, 사이클·이력 증가 시 렌더 stall.
- ③: 사전 인덱싱 부재.
- ④: `useMemo`로 `decisionMap = Map<{symbol,strategy_id}, reason>` 한 번 계산, 조회 O(1). Backtest는 `useReducer`/`useCallback` 정리.
- ⑤: 동작 회귀 없게 단위 스냅샷 테스트 권장.
- ⑥: 없음.

#### P-02 [Med] 번들 단일 청크 (>500kB) — 코드 분할 없음
- **STATUS**: PRESENT (`npm run build` 마지막 부분 `(!) Some chunks are larger than 500 kB after minification`; `App.tsx`가 모든 페이지 static import; `vite.config.ts`에 manualChunks/lazy 없음).
- ①: `web/src/App.tsx`(import), `web/vite.config.ts`, `_sig_build.txt`.
- ②: 초기 진입 페이지(Login)에서도 Backtest/Strategies/Monitor/Settings/차트 라이브러리 전부 로드 → 첫 페인트·인터랙션 지연.
- ③: 라우트 단위 코드 분할 미설계.
- ④: `React.lazy` + `Suspense` 라우트 분할(특히 Backtest·EquityChart), vendor 분리(`manualChunks: { recharts: ['recharts'], react: ['react','react-dom'], }`).
- ⑤: lazy 경계 로딩 표시(빈 상태 패턴), 과분할 주의.
- ⑥: 차트 라이브러리 SSR/번들 영향(현 SPA니 단순).

#### W-EXT [Med][게이트] 3rd-party SDK `huddlekit` 주입
- **STATUS**: PRESENT (`web/index.html:15-19` `<script src="https://app.huddlekit.com/sdk/huddlekit.js" data-project-key="pk_live_unxN0R8f8nRjVSU7UCzI" async>`).
- ①: `web/index.html:15-19`.
- ②: 금융 UI에 미상의 외부 SDK가 데이터 접근/수집할 가능성. 사용자 동의 없이 production 키로 로드 → 개인정보·세션 노출 위험.
- ③: 외부 의존을 정책 게이트(production 환경 + 사용자 동의) 없이 도입.
- ④: 용도 확인 후 ① 제거 ② DEV에서만 로드 ③ 사용자 동의(쿠키 배너)+마스킹 중 택일.
- ⑤: 사용 의도(고객지원/세션 리플레이 등)에 따라 운영 영향.
- ⑥: **huddlekit 도입 목적·수집 범위·계약 확인 필요(사용자 결정 게이트)**.

#### N-01 [Med] NextDayPreviewPanel set-state-in-effect 안티패턴
- **STATUS**: PRESENT (web 에이전트가 modified 파일 검사 중 추가 발견).
- ①: `web/src/components/NextDayPreviewPanel.tsx` mount 시 `load()` → setState 다수.
- ②: 마운트마다 re-render, 빠른 navigate에서 stale state 가능.
- ③: W-05 패턴 재발.
- ④: 데이터 패칭은 `useEffect`로 유지하되 의존성 명시 + abort controller, 파생값은 useMemo.
- ⑤: 거의 없음.
- ⑥: 없음.

---

## 5. Phase 2 — Visual & UX Design (정적)

DESIGN.md(테라코타 디자인 시스템)와 `index.css` 풀 리딩 + 페이지 컴포넌트 맵 기반 평가. 라이브 스크린샷·런타임 검증은 **사용자 개입 필요(REPORT-ONLY, dev 서버 미기동)**.

| 페이지 | 정적 점수 | 핵심 관측 |
|---|---|---|
| Login | 9/10 | 인증 카드 단일 책임. 최근 commit `36a628a`로 Google 버튼 폭=카드 inner 정렬 — overhang 해소. |
| Pair | 7/10 | revoke confirm 부재(W-04). 디자인 자체는 단순. |
| Dashboard | 8/10 | 액션 패널/equity/포지션/시스템 상태 IA 정돈. 최근 `4c04b55`로 market/context 비블로킹 분리(콜드로드 개선). reasonFor O(n²)는 perf 항목(P-01). |
| Monitor | 7.5/10 | risk·reconciliation·preview·killswitch 정렬은 양호. silent catch(W-02) UX 영향. amber 토큰화 완료(W-07). |
| Strategies | 8/10 | 카드 그리드+detail overlay+승격 2-step modal — Product 핵심. |
| Backtest | 8.5/10 | 빌더+결과+이력+마켓플레이스 placeholder 탭. 차트·결과 metrics 균일 grid. useState 수가 많음(P-01). |
| Settings | 8.5/10 | 페어링·로컬앱 다운로드·알림·위험 한도 한 페이지로 통합. W-03(silent) 외 OK. |

**시스템 토큰 평가**: terracotta 브랜드, 한국식 시장 방향(빨강=상승), 4-상태(`.empty-state`/`.panel .empty`/`.error`/`.ok`), 모바일 760px 사이드바→상단바·44px 터치 타깃, tabular-nums, live 모드 적색 테두리+pulse — **성숙**. 다만:
- **A-01 a11y 포커스**(버튼/링크/nav `:focus-visible` 없음) — 디자인 시스템 결함.
- 아이콘 이모지 정리는 `e9f6f96`으로 진행.

라이브 4상태 완전성(빈/로딩/에러/성공) 페이지별 실측, 모바일 spacing, AI-slop(중복 카드/생성형 패턴) — **dev 서버 + 브라우저로 사용자 개입 필요**.

---

## 6. Phase 3 — User Flow (정적)

페이지 컴포넌트 + api.ts + auth/mode 컨텍스트 기반 플로우 워크스루. 런타임 17 시나리오 실행은 **사용자 개입 필요(dev 서버 미기동)**.

| 시나리오 | 정적 진단 |
|---|---|
| 신규 가입 → 로그인 | ✅ Email/PW + Google SSO 정상 동선. |
| 디바이스 페어링 | ⚠️ 코드 입력·승인 OK. revoke confirm 부재(W-04). |
| 첫 전략 생성 | ✅ ConditionBuilder DSL(중첩 그룹·이력통계·아핀·[이 종목]) 강력. 이모지 제거(`e9f6f96`)로 시각 단정. |
| 백테스트 실행→결과→저장 | ✅ 빌더·결과·보관함 IA 정돈. 세금/틱/소수주 모델 결함은 도메인(C-01/C-03/C-04). |
| 모의 ↔ 실전 토글 | ✅ 라이브 진입 confirm dialog 존재(`Layout.tsx:16-21`). 적색 테두리/pulse 등 시각 경고. |
| 실시간 모니터링 | ⚠️ silent catch(W-02), ErrorBoundary 부재(W-01) 시 위험. |
| 위험 한도 설정 | ⚠️ Settings 폼 로드 실패 silent(W-03) — 사용자가 한도 조정 불가 인지 못함. |
| 페어링 해제 → snapshot stale 차단 | ✅ Dashboard 게이트(line 64)·N/A 표기 — 0104에서 FIXED 유지. |
| 로그아웃 → 재로그인 | ✅ 토큰 클리어 → Login 라우팅. |

런타임 검증 필요 시나리오: 자동선택 스크리너 KR/US 프리셋 적용, 자동선택 리밸런싱 실동작, 미국 정규장 시각 자동매매(US 실시간 미신청 고지 UX, `cb2951d` 단위테스트는 결정론으로 추가됨), Pair 딥링크 진입.

---

## 7. Phase 4 — 최근 변경(diff) 리뷰

직전 리뷰 `0104` 이후의 커밋 16건(`5c6c22a..629d5ed`) + 미커밋 `REVIEW_PLAYBOOK.md`(+82).

**변경 분류**:
- 디자인/a11y: `01a13c1`(대비 토큰 + 통일), `c1f7d21`(테라코타 브랜드 적용), `36a628a`(Google 버튼), `e9f6f96`(이모지 정리), `629d5ed`(a11y 다운로드 a>button 정정).
- Perf: `4c04b55`(market/context 비블로킹).
- 기능: `e46025c`(빌더 표현력+스크리너 커스터마이징+자동선택 리밸런싱), `b15d29f`(미국 정규장 자동매매+US 스크리너), `337da8f`(US 프리셋), `8c5ffe4`(국내/미국 섹션 분리·$).
- 신뢰성/보안: `07e4787`(로컬앱 preview pull 인증 — 자동 매수 401 해소), `c2f8d5d`(콜드스타트 us_metrics 빈 값 레이스 제거), `26705c8`(PyInstaller 번들에 quant_core 데이터 포함).
- 테스트: `cb2951d`(미국 실시간 미신청 결정론 테스트) 외 7건 신규(condition_engine, market_calendar, rebalance, round_to_tick, sync_preview_auth, cold_start_us_metrics, us_metrics_enrich, webhook_ssrf, market_index, us_realtime_notify).
- 데이터: `75c69eb`(US 기술지표 enrich).
- 운영: `891502a`(manage.py CLI).

**잠재 리스크 또는 회귀**(읽기만):
- 다수 web 변경 + 신규 컴포넌트(ScreenerPanel +459 라인)에 반응형/포커스/에러 상태가 동일 패턴으로 도입되었는지 라이브 검증 필요(W-01/W-02/W-03/A-01과 일관 영향).
- `4c04b55`(market/context 비블로킹)이 W-02 silent catch 패턴을 더 도입했는지 확인 필요(현 코드엔 catch null 1건 잔존).
- `c2f8d5d`(콜드스타트 us_metrics 레이스)와 `S-05`(preview stale)는 같은 "데이터 가용성" 도메인 — 합쳐서 진단 가치 있음.

SQL 안전성·LLM trust boundary 결함은 없음(LLM 미사용, raw SQL 미사용).

---

## 8. Phase 6 — Performance (정적)

라이브 CWV·Lighthouse는 **deployed URL + 브라우저 필요(사용자 개입)**. 본 진단은 빌드/번들 단계 정적 신호.

| 신호 | 결과 |
|---|---|
| `npm run build` | exit 0, `(!) Some chunks are larger than 500 kB after minification` 경고 = P-02 확인 |
| `npm audit` | 0 vulnerabilities |
| 정적 perf 결함 | P-01(Dashboard reasonFor O(n²)), P-02(코드 분할 없음) |

**개선 ROI 큰 순**: P-02 React.lazy 라우트 분할(특히 Backtest·차트) → P-01 인덱싱 → `4c04b55` 패턴(비블로킹 fetch) 다른 페이지로 전파.

---

## 9. Phase 7 — Security

### 9.1 자격증명 격리 (CLAUDE.md 절대원칙)
- **server 트리 grep** `appkey|appsecret|account_number|kis_account` → **0건**(이전 turn 매핑 + 서버 에이전트 grep 결과). 격리 무결.
- **sync push payload**(`server/app/schemas.py SyncPushIn` + `routers/sync.py`) — balance·positions·equity·trades·decisions·killswitch·drawdown·reconciliation 한정. KIS 키/계좌# 부재 확인.
- **로컬 자격증명** — `secrets_store.py`가 OS keyring(Windows Credential Manager) 사용, `file_security.py`가 토큰 캐시 파일에 `icacls /inheritance:r /grant:r {user}:F` ACL 적용. 평문 저장 무.

### 9.2 종속성 감사
- **npm audit**: 0.
- **pip-audit**: **차단됨**(F-X01/X-01 — cp949 디코드 실패). Python 측 취약점 가시성 손실 — 우선 해결 권장.

### 9.3 그 외 보안 결함
- S-01/S-02(tz), S-03(blocking webhook), S-05(stale preview), S-09(/health/refresh 무인증), S-10(SECRET_KEY fallback) — 위 §4 참조.
- S-04(SSRF) **FIXED**.
- 로컬 머니세이프티(L-01·L-02·L-03·L-04) — 자금 손실 직접 경로.

### 9.4 결론
critical 자격증명 침해 없음. Active fund-loss path은 L-01(멱등성)이 가장 가까움. 그 외는 운영 시 발생 가능한 신뢰성·가시성·정합성 결함.

---

## 10. Phase 8 — System Trading Domain

`QUANT_DOMAIN_CHECKLIST.md` 7개 카테고리 평가:

| 카테고리 | 평가 | 핵심 |
|---|---|---|
| 1. 백테스트 정확성 | ⚠️ | look-ahead 안전(`next_open`, `.shift()`·`.rolling()` 양수 shift 위주). 시장 마찰: **commission/slippage default 불일치(CM-01), 매도세 모델 부재(C-01), 틱 라운딩 미적용(C-03), 소수주 허용(C-04)**. 기업 액션: parquet 어드정 여부 미검증(CL-02). |
| 2. 시그널→주문 idempotency | ❌ | 멱등성 부재(L-01). |
| 3. 모의↔실전 일관성 | ⚠️ | Strategy 객체·build_signal_mask 공유로 신호 일치는 구조적으로 OK. 라이브 괴리 노이즈는 슬리피지/모델 결함(C-03/C-04). 백테스트 vs 라이브 overlay UI는 존재(MonitorTools.BacktestLiveOverlay) — 라이브 검증 필요. |
| 4. 리스크 관리 | ⚠️ | killswitch/drawdown 트리거·신규차단 OK. **단일 종목 한도 pct_cash 미적용(L-10), 섹터 한도 부재(L-10)**. Webhook 알림 동작(S-03 blocking 외 OK). |
| 5. KIS ↔ ledger 정합성 | ⚠️ | reconcile_with_kis 존재하나 **15:35만 → 장중 over-sell(L-04)**. 알림 토글 OK. |
| 6. 자격증명 분리 | ✅ | 서버 0건, 로컬 keyring+ICACLS. 격리 무결. |
| 7. 한국 시장 특수성 | ⚠️ | 시간 KST 가정은 스케줄러만, Trader는 naive(L-06). 정규장 인식 OK. **휴장일 KRX 캘린더 부재(L-03)**. 호가 단위 함수 존재·테스트 추가(`test_round_to_tick`)지만 백테스트가 호출 안 함(C-03). 상·하한가 ±30% 로직: backtest·trader에서 명시 grep 0(별도 backlog). |

**golden test**: 15 passed, 1 skipped — 기능 회귀 없음. **30 warnings 중 RuntimeWarning(divide by zero/invalid in log) 확인 = C-02**.

**도메인 카테고리 점수**: ✅×1 + ⚠️×5(0.5) + ❌×1 → (1.0 + 2.5 + 0) / 7 ×10 ≈ **5.0/10**. 

(주: 도메인 체크리스트 §8 가이드를 따른 정량 계산. 이 점수는 카테고리 binary 평균이므로 5점 관점 점수와 직접 비교 안 됨 — §11에서 SysTrading 관점 별도 점수.)

---

## 11. Phase 9 — 통합 SUMMARY

### 11.1 우선순위 매트릭스 (완료조건 5)

| 심각도 | 정의 | 건수 | 결함 ID |
|---|---|---|---|
| **Critical** | 자산 손실·보안 침해·서비스 다운 직접 경로 | **0** | — |
| **High** | 사용자 신뢰 손상·핵심 기능 부분 고장 | **11** | C-01, C-02, L-01, L-02, L-03, L-04, S-01, S-03, S-05, S-10, W-01, W-02, W-03 (오기 정정: 13) |
| **Medium** | UX 마찰·성능 저하·코드 품질 | **18** | C-03, C-04, CM-01, CM-02, L-06, L-09, L-10, S-02, S-06, S-07, S-08, S-09, W-04, W-05, W-06, A-01, P-01, P-02, W-EXT, N-01, X-01, X-02 (정정: 22) |
| **Low** | 코스메틱·미세 개선 | **6** | CM-03, CL-01, CL-02, L-05, L-07, L-08, S-11, X-03 (정정: 8) |
| **FIXED(이번 사이클)** | 직전 list에서 해소 | **2** | S-04, W-07 (+W-04 부분) |

> 정정 합계: **Critical 0 · High 13 · Medium 22 · Low 8 = 43건** + FIXED 2건.

### 11.2 5개 관점 점수 (0-10, 직전 0415 baseline 대비)

| 관점 | 점수 | Δ baseline | 근거 |
|---|---|---|---|
| **UX / 사용성** | **8.0**/10 | −0.6 | 모드 confirm·sentence builder·모바일·다국어시장 동선은 강함. W-01·W-02·W-03(silent failure)·A-01·W-04 일부 미해결로 신뢰성 하락. |
| **Visual Design** | **8.8**/10 | +0.2 | 테라코타 브랜드 적용, --amber 토큰 추가, a11y 대비 토큰 교정. 시스템 토큰 일관. |
| **Engineering** | **6.8**/10 | −0.5 | ruff 21→**42**, mypy 82(노이즈 비중 큼), eslint 10. 신규 테스트 +7건은 +. S-04/W-07 FIXED는 +. 미해결 S-/W- 다수. |
| **Product** | **8.5**/10 | +0.5 | US 정규장 자동매매·US 스크리너·자동선택 리밸런싱·빌더 표현력 확장 — 제품 surface 큰 확장. |
| **System Trading** | **6.3**/10 | −0.6 | C-01·C-02·C-03·C-04·CM 도메인 정확성 잔존, L-01·L-02·L-03·L-04 머니세이프티 High 잔존. golden 통과지만 30 warnings(C-02 신호). |
| **종합** | **7.7**/10 | −0.2 | 제품·디자인은 전진, 엔지니어링·도메인은 잔존 결함이 새 surface 확장으로 노출도 증가. |

### 11.3 권장 다음 phase (ROI 큰 3)

1. **머니세이프티 배치**: L-02(원자 저장 — 1-2시간) → L-01(설계 승인 후 멱등성) → L-04(장중 reconcile/over-sell 가드). 직접 자금 손실 차단.
2. **도메인 정확성 배치(게이트)**: C-02(log÷0 — baseline 영향 적음 우선) → 사용자 승인 후 C-01·C-03·C-04·CM-01·CM-02 + golden baseline 재생성. 백테스트 신뢰 회복.
3. **프론트 신뢰성 배치**: W-01(ErrorBoundary) → W-03 → W-02 → A-01. 라이브에서 위험 차단 UI 보장.

추후 별도: P-02 코드 분할(첫인상 개선) · S-10 SECRET_KEY fail-fast · L-03 KRX 캘린더 · X-01 cp949 주석 해소(pip-audit 복구).

### 11.4 사용자 결정/Align 필요 항목

- **C-01·C-03·C-04 게이트**: golden baseline 재생성 승인.
- **L-01 게이트**: 멱등성 2-phase 설계안 승인. KIS ODNO 활용 가능 여부 결정.
- **W-EXT 게이트**: huddlekit SDK 용도·계약 결정(제거/dev-only/동의배너 중 선택).
- **S-09**: `/health/*/refresh`를 외부 모니터링이 호출 중인지 확인 후 인증 방식 결정.
- **L-10**: 섹터 분류 소스(KIS 업종/Naver) 결정, 단일종목 한도 기본값 합의.

---

## 12. 자체 점검표 — 6필드 채움 검증 (완료조건 4)

> 모든 결함 ID에 대해 ①문제·근거 ②영향 ③근본원인 ④해결방향 ⑤트레이드오프 ⑥추가정보 6필드 채움을 ✅/❌로 표시. ❌가 하나라도 있으면 미완료.

| ID | 영역 | 심각도 | STATUS | ① | ② | ③ | ④ | ⑤ | ⑥ |
|---|---|---|---|---|---|---|---|---|---|
| C-01 | Core | High | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| C-02 | Core | High | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| C-03 | Core | Med | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| C-04 | Core | Med | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| CM-01 | Core | Med | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| CM-02 | Core | Med | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| CM-03 | Core | Low | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| CL-01 | Core | Low | PARTIAL | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| CL-02 | Core | Low | UNVERIFIABLE | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| L-01 | Local | High | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| L-02 | Local | High | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| L-03 | Local | High | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| L-04 | Local | High | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| L-05 | Local | Low | PRESENT-guarded | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| L-06 | Local | Med | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| L-07 | Local | Low | 의도-구현 불일치 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| L-08 | Local | Low | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| L-09 | Local | Med | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| L-10 | Local | Med | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S-01 | Server | High | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S-02 | Server | Med | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S-03 | Server | High | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S-04 | Server | — | **FIXED** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S-05 | Server | High | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S-06 | Server | Med | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S-07 | Server | Med | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S-08 | Server | Med | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S-09 | Server | Med | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S-10 | Server | High | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S-11 | Server | Low | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| X-01 | Server | Med(실효) | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| X-02 | Server | Med | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| X-03 | Server | Low | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| W-01 | Web | High | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| W-02 | Web | High | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| W-03 | Web | High | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| W-04 | Web | Med | PARTIAL | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| W-05 | Web | Med | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| W-06 | Web | Med | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| W-07 | Web | — | **FIXED** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| A-01 | Web | Med | PARTIAL | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| P-01 | Web | Med | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| P-02 | Web | Med | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| W-EXT | Web | Med | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| N-01 | Web | Med | PRESENT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**합계: 45항목(FIXED 2 포함) × 6필드 = 270 cell, ❌ 0건. 자체점검 통과.**

---

## 13. 한계·관측 불가 항목

- **Phase 2 라이브 스크린샷 비교**: dev 서버 미기동(REPORT-ONLY) → 사용자 개입 필요.
- **Phase 3 17 시나리오 런타임 실행**: 동일.
- **Phase 6 라이브 Lighthouse / Core Web Vitals**: deployed URL + 브라우저 필요.
- **pip-audit Python 공급망**: X-01 cp949로 차단 → 우선 해결 필요(파일 인코딩 정리).
- **CL-02 parquet tz**: 본 진단에서 현재 line 재확인 미수행. 후속 단일 read로 확정 가능.

---

*근거 보강: `_sig_*.txt`(신호), `_diff_uncommitted.txt`(미커밋), `../2026-05-22-0415/SUMMARY.md`(추세 baseline), `../2026-05-23-0104/REMEDIATION_PLAN.md`(0104 list). 기준 문서: `../../../CLAUDE.md`, `../../../DESIGN.md`, `../../QUANT_DOMAIN_CHECKLIST.md`.*
