# 결함 수정 작업 지시서 (REMEDIATION PLAN)

> **이 문서를 받은 Claude Code에게**: 이것은 2026-05-23 진단(`FINDINGS_REPORT.md`)에서 도출된 **검증·수정 작업 지시서**다. 너의 임무는 각 이슈를 **(1) 현재 코드로 직접 재검증한 뒤 (2) 근본 원인을 해결**하는 것이다. 아래 §0의 규칙을 반드시 먼저 읽어라.

---

## 0. 작업 규칙 (반드시 준수)

### 0.1 절대 원칙 (CLAUDE.md)
1. **자격증명 격리 — 위반 금지**: KIS appkey/appsecret/계좌번호/원시 주문은 **로컬 PC 전용**. 서버 스키마·payload·로그·웹에 절대 넣지 마라. 어떤 수정도 이 경계를 넘으면 즉시 중단·보고.
2. **근본 원인 해결**: fallback·예외 무시(`except: pass`)·임시 패치 금지. 그 자체가 결함이다.
3. **규모 있는 작업은 설계안 → 질문 → 승인 → 구현** 순서. 곧장 코드부터 쓰지 마라.
4. **git push 금지** (사용자 명시 허락 시에만). commit은 논리 단위로 가능하나 push는 하지 마라.
5. **UI 변경은 완료 전 브라우저 검증** (타입체크·테스트는 정확성을 보장하지 않음).

### 0.2 검증 우선 (가장 중요)
- 이 문서의 `file:line`은 **2026-05-23 기준 스냅샷**이다. 코드가 이동·수정됐을 수 있으니, **각 이슈를 손대기 전에 grep/read로 현재 상태를 재확인**하라.
- **이미 수정됐거나 재현되지 않으면**, 고치지 말고 "검증 결과: 해당 없음/이미 해결"로 보고하라.
- 이 진단은 2일 전(qa_findings.md)의 다수 항목을 **오진/이미 FIXED로 정정**했다(§5 참조). 같은 실수를 반복하지 마라 — §5 목록은 **재작업 금지**.

### 0.3 게이트 (사용자 승인 없이 진행 금지)
- **백테스트 결과 수치가 바뀌는 변경**(C-01 매도세, C-04 정수주 등) → `golden_baseline.json` 재생성이 필요하므로 **반드시 사용자 승인 후** 진행.
- **외부 SDK 제거/정책 변경**(W-EXT huddlekit) → 용도 확인 후 사용자 결정.
- **제품 UX 변경**(전략 prefill 등) → 사용자 결정.
- 각 이슈의 `[게이트]` 표시를 확인하라.

### 0.4 환경 (Windows)
- 콘솔 cp949. 한글 출력 Python 스크립트는 첫 줄에 `import sys, io; sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")`. 파일 읽기는 `encoding="utf-8"` 명시.
- **bun 미설치** → 웹은 `npm run dev`(Vite :5173), `npx tsc --noEmit`, `npm run lint`, `npm run build`. 백엔드는 `python -m uvicorn app.main:app --port 8000 --app-dir server`.
- dev 서버는 이미 떠 있을 수 있음(5173/8000). 브라우저 검증은 preview 도구 사용.

### 0.5 작업 흐름 (이슈마다)
```
재검증(grep/read/실행) → [게이트면 사용자 확인] → 설계(규모 크면 승인) →
구현(근본 해결) → 검증(아래 §6 신호 + 관련 테스트 + UI면 브라우저) → 회귀 없음 확인 → 보고
```

---

## 1. 검증 기준선 신호 (수정 전/후 비교용)

수정으로 **회귀가 없는지** 아래를 기준으로 비교하라. (2026-05-23 측정값)

| 명령 | 현재 결과 | 수정 후 기대 |
|---|---|---|
| `cd platform && python -m pytest tests/ -q` | 40 passed | 유지(또는 신규 테스트 추가분만 증가) |
| `python -m pytest tests/golden_backtest.py -v` | 15 passed, 1 skipped, **30 warnings** | C-02 수정 후 log 경고 **0** 목표 / C-01·C-04 수정 시 baseline 재생성 |
| `cd platform/server && python -m ruff check .` | **21 errors** | 감소(X-03 수정 시 0) |
| `python -m mypy app` | 80 errors (대부분 노이즈) | 실질 항목만 정리, 노이즈는 mypy 설정으로 |
| `cd platform/web && npx tsc --noEmit` | 0 errors | **0 유지** |
| `npm run lint` | **10 errors** | 감소(W-05/W-06 수정 시) |
| `npm run build` | index.js **732kB** (gzip 215kB) | P-02 분할 시 초기 청크 감소 |
| `npm audit` / `pip-audit` | 0 / 0 | 0 유지 |

---

## 2. High 결함 (14건) — 우선 처리

### 도메인/백테스트 (core/quant_core)

#### C-01 [High][게이트] 한국 매도세를 commission에 대칭 흡수 — 비용 모델 부정확
- **위치**: `core/quant_core/backtest.py:169-184`(`_close`), `:160`(`_open`), `exec_defaults.py:45-46`(DEFAULT_EXECUTION 주석/기본값).
- **재검증**: `_close`에 `sell_tax`/세금 항목이 정말 없는지, `_open`/`_close`가 commission을 양방향 대칭 적용하는지 read. Backtest UI "5.백테스트 가정"이 commission을 "위탁+거래세 25bps 양쪽"으로 안내하는지 확인(`web/src/pages/Backtest.tsx` 해당 섹션).
- **문제**: 매도세(거래세+농특세, 코스피 0.23%/코스닥 0.18%, 매도 단방향)를 별도 모델 없이 commission에 양방향으로 녹임. 라운드트립 0.50%(25bps×2)로 계산되나 실제는 ≈0.26%. 엔진 default(0.015%)를 쓰면 반대로 과대평가.
- **근본 원인**: 비용 모델이 commission/slippage 2개의 **대칭** 파라미터뿐 — 한국시장의 매수 무세금/매도 유세금 **비대칭**을 표현할 수단 부재.
- **수정 방향**: `_close`에만 적용되는 `sell_tax`(default 0.0023) 파라미터 신설 → `proceeds = shares*price*(1-commission-sell_tax)`. `ExecutionPolicy`에 `bt_sell_tax_bps`. KOSPI/KOSDAQ 메타가 `ticker_db.py:34-35`·KIS 마스터에 있으므로 차등 적용 가능하나, **1단계는 보수적 단일 0.23%**. CM-02(주석)도 함께 정정.
- **수용 기준**: 매수 비용에서 세금 제거, 매도에만 세금 적용. golden 회귀 테스트가 새 baseline으로 통과. UI "백테스트 가정"이 세금을 별도로 노출(commission과 분리).
- **고려/리스크**: `golden_baseline.json` 전 케이스 수치 변경 → **재생성 필요(사용자 승인 게이트)**. 차등(코스피/코스닥) 적용 시 종목→시장 매핑 정확성.

#### C-02 [High] log() divide-by-zero — 매크로 음수/0 종목 지표 오염·신호 누락
- **위치**: `core/quant_core/indicators.py:22`(add_returns), `:121`(realized_vol), `:131`(zscore). 오염원: `load_all()`로 들어오는 매크로 시계열(금리차·스프레드 등 9개, Close ≤ 0).
- **재검증**: `python -m pytest tests/golden_backtest.py -v`로 `divide by zero in log`·`invalid value in log` 경고 재현. 어떤 심볼의 Close가 0/음수인지 확인.
- **문제**: 가격용 로그 지표를 음수 가능 레벨 시계열에 적용 → −inf/NaN. `analysis._condition_mask`가 `fillna(False)`로 처리해 **조건 신호가 조용히 누락**.
- **근본 원인**: price-positive 지표와 음수 가능 level 지표를 구분하지 않음.
- **수정 방향**: 로그 계열을 `Close>0 & Close.shift>0` 마스킹 후 계산하거나, 음수 가능 심볼군엔 로그 지표 미산출 분기. **경고를 `warnings.filterwarnings("ignore")`로 덮지 마라**(정의역에서 해결).
- **수용 기준**: golden 테스트 경고 **0**(또는 명시적 NaN 처리), 매매종목 지표 불변(회귀 없음).
- **고려/리스크**: 매크로의 로그수익률은 금리차에 무의미하므로 제거해도 실손실 없음. 단 기존 전략이 그 컬럼을 참조하면 NaN→False 동작이 바뀔 수 있으니 사용 여부 확인.

### 로컬앱 자금 안전 (local/localapp) — 변경마다 단위 테스트 + 모의 검증 권장

#### L-01 [High][설계 승인] 주문 멱등성 부재 — 크래시·재시작 시 중복 발주
- **위치**: `local/localapp/trader.py:142-166`(__init__/pending 로드), 발주부(`_submit_buy`/`_enter_from_preview`), `_save`(`:161-166`), `order_log.py`.
- **재검증**: 발주 전 (date,전략,종목,side) dedup 키가 있는지, intent가 발주 *이전*에 영속되는지 grep. `_daily_ccld()`/`_overseas_ccnl_today()` 존재 확인.
- **문제**: 멱등 단위가 KIS order_no뿐. 발주 직후~`_save()` 전 크래시 시 pending 미기록 → 재시작 시 동일 후보 재발주 → 2배 포지션(실자금 손실).
- **근본 원인**: 영속화가 발주와 분리된 사후 `_save()`(race window) + 의도(intent) 기록 부재.
- **수정 방향**: 발주 직전 intent를 원자적으로 append(`intents.jsonl`) + cycle 진입 시 당일 intent 대조 skip. 또는 cycle 시작 시 KIS 당일 체결조회로 reconcile. **2-phase(intent→결과확정)로 "유령 intent" 방지** 설계 필요 → 설계안 제시 후 승인.
- **수용 기준**: 발주 후 강제 종료→재기동 시나리오에서 동일 종목 재발주 안 됨(테스트 또는 모의계좌 재현).
- **고려/리스크**: KIS가 client-side 주문ID(ODNO)를 지원하면 진짜 멱등키 → **KIS 문서 확인 필요**. 발주 실패 시 intent 정리 로직 필수.

#### L-02 [High] `_save()` 비원자적 순차 write — 부분 상태·원장 소실
- **위치**: `local/localapp/trader.py:161-166`.
- **재검증**: grep `os.replace|atomic` (없어야 현존). `write_text`로 ledger/equity/pending/rebalance 순차 저장 확인.
- **문제**: 중간 크래시 시 파일 간 불일치, truncate 중 손상 시 `_load_json`이 `default={}`로 **전체 보유 원장 소실**.
- **근본 원인**: 다중 파일 트랜잭션을 원자 단위로 다루지 않음(`write_text`=truncate-then-write).
- **수정 방향**: 파일별 `tmp = path.with_suffix(".tmp"); tmp.write_text(...); os.replace(tmp, path)`.
- **수용 기준**: 저장 중 강제 종료해도 각 파일이 "이전 완전본 또는 새 완전본"(파싱 실패 0).
- **고려/리스크**: 4파일 cross-consistency는 여전히 미보장 — 완전 해결(단일 파일/WAL)은 베타엔 과설계, 지금은 파일별 원자성으로 충분.

#### L-03 [High] 한국(KRX) 휴장일 캘린더 미적용
- **위치**: `local/localapp/scheduler.py:99-110`(KRX cron), `core/quant_core/market_calendar.py`(US 전용 `_FILES`), `core/gen_market_sessions.py`, cycle/intraday/settlement 진입부(`trader.py`, `intraday_loop.py`).
- **재검증**: `market_calendar`가 KR을 지원하는지(`session_kst("KR")`가 에러나는지), cycle/intraday/settlement에 거래일 게이트가 있는지 grep.
- **문제**: 휴장 평일에도 사이클·청산·reconcile 실행. 청산 패스가 휴장일에 매도 발주, 킬스위치가 stale 시세로 평가.
- **근본 원인**: US만 동적 캘린더, KRX는 "평일=거래일" 가정.
- **수정 방향**: `market_calendar`에 KR 세션 추가(`gen_market_sessions.py`에 KRX 포함) → cycle/intraday/settlement 진입부에서 `is_session_open("KR")` 가드(US와 동일 패턴).
- **수용 기준**: 휴장일에 cycle/청산/reconcile 무동작. `test_market_calendar.py`에 KR 케이스 추가·통과.
- **고려/리스크**: KR 캘린더 데이터 생성·만료 관리(US처럼). 반일장(연말) 마감시각 반영 여부 확인.

#### L-04 [High] reconcile가 15:35에만 → 장중 수동매도 후 over-sell
- **위치**: `local/localapp/trader.py:173-229`(reconcile_with_kis), `runner.py:183`(호출), `intraday_stop.py:130-137`(on_tick 매도).
- **재검증**: on_tick 매도 발주 직전 KIS 실보유 재조회가 있는지 확인.
- **문제**: 장중 사용자 수동 전량매도 후 ledger 잔존 → 손절 트리거 시 없는 수량 매도(over-sell).
- **근본 원인**: ledger 신뢰, 장중 KIS 정합성 미확인.
- **수정 방향**: on_tick 매도 직전 KIS 실보유로 `min(ledger_qty, broker_qty)` 클램프, 0이면 ledger 정리·skip. 짧은 TTL 캐시로 rate-limit 회피.
- **수용 기준**: 수동 매도 시뮬레이션에서 over-sell 발주 없음.
- **고려/리스크**: tick마다 조회는 KIS 초당제한 압박 → TTL 캐시. 체결통보 WS가 수동매도까지 통지하면 ledger 실시간 차감이 더 근본적.

### 서버 (server/app)

#### S-04 [High] webhook URL 미검증 → SSRF
- **위치**: `server/app/routers/sync.py:49-56`(_post_webhook), `routers/settings.py:45-81`(put_settings, `:50` 무검증 저장), `preview_engine.py:388`.
- **재검증**: `alert_webhook_url`이 scheme/host 검증 없이 저장·발송되는지 read.
- **문제**: 사용자가 `http://localhost`·`169.254.169.254`(메타데이터)·사설 IP를 webhook으로 저장 → 서버가 그 주소로 POST(SSRF).
- **근본 원인**: 사용자 제어 URL을 egress에 그대로 사용, allowlist 부재.
- **수정 방향**: 저장 시점(`put_settings` 검증 블록 옆)에서 `https`만 허용 + resolve IP가 private/loopback/link-local이면 거부(`ipaddress`), 가능하면 `discord.com`/`hooks.slack.com` 도메인 allowlist(UI도 둘을 제안 중).
- **수용 기준**: 내부/사설/메타데이터 URL 저장 시 400. Discord/Slack URL은 정상.
- **고려/리스크**: 도메인 allowlist는 자체호스팅 webhook 차단(개인 트레이더엔 무방). IP 차단만으론 DNS rebinding에 취약(완전방어는 과설계).

#### S-01 [High] APScheduler 재시도 naive datetime → UTC 배포 misfire drop
- **위치**: `server/app/main.py:70`(run_at), `:75`(add_job date), `:325`(scheduler tz=KST).
- **재검증**: `datetime.now()`(naive)를 `run_date`로 쓰는지 확인. scheduler tz 확인.
- **문제**: naive 시각을 KST 해석 → Railway(UTC)에선 과거 시각 → misfire로 재시도 drop → stale 데이터 방치.
- **근본 원인**: tz-aware 규율 부재(동적 잡 생성부만 naive).
- **수정 방향**: `datetime.now(ZoneInfo("Asia/Seoul"))`로 aware 시각 생성(`models.py` 기존 패턴 일치).
- **수용 기준**: 재시도 잡이 의도한 시점에 실행(로그 확인).
- **고려/리스크**: 거의 없음. 동일 패턴을 S-02와 함께 일괄 적용 권장.

#### S-05 [High] preview가 fetch 실패 시 어제 종가로 후보 산출 (상폐/거래정지 위험)
- **위치**: `server/app/preview_engine.py:36-44`(_prev_close), `main.py:262`(invalidate), `_refresh_kr_dataset`.
- **재검증**: `_prev_close`가 날짜/as-of 검증 없이 `iloc[-1]`을 쓰는지, fetch 실패 시 캐시 무효화 경로 확인.
- **문제**: 어제 데이터로 매수 후보·예상가 노출 → 거래정지·상폐 직전 종목 잔존(잘못된 투명성 정보).
- **근본 원인**: dataset as-of stale 판정 부재(`_last_date` 미사용).
- **수정 방향**: 기준일이 직전 거래일보다 오래되면 `available=False, reason="데이터 갱신 지연"`. 거래정지 플래그(KIS 마스터) 활용.
- **수용 기준**: stale dataset에서 preview가 "갱신 지연" 표기, 후보 미생성.
- **고려/리스크**: 연휴 직후 false-skip 방지 위해 거래일 캘린더 필요(L-03과 연계).

#### S-03 [High] 다중 webhook 동기 인라인 호출이 push 블로킹
- **위치**: `server/app/routers/sync.py:42`(push_snapshot), `:55`(requests.post timeout=8), `_check_alerts`.
- **재검증**: webhook 발송이 push 동기 핸들러 안에서 순차 실행되는지 확인. `BackgroundTasks` import 여부(`:14`).
- **문제**: 느린 webhook 다수면 8s씩 누적 블로킹, threadpool 고갈.
- **근본 원인**: 알림 발송이 요청-응답 경로에 인라인.
- **수정 방향**: `BackgroundTasks`로 응답 후 발송(fire-and-forget) + timeout 3~5s.
- **수용 기준**: push 응답 시간이 webhook latency와 분리.
- **고려/리스크**: BackgroundTask도 같은 프로세스 — 진짜 큐(Redis)는 베타엔 과설계.

#### S-02 [High] `market.py` deprecated utcnow + 수동 +9h
- **위치**: `server/app/routers/market.py:69-70`.
- **재검증**: `datetime.utcnow() + timedelta(hours=9)` 패턴 확인.
- **문제**: deprecated API + naive 산술 → KST 배포 시 +18h로 돌변(환경 의존). 장 상태 오인 가능.
- **근본 원인**: tz 라이브러리 미사용(서버만 누락).
- **수정 방향**: `datetime.now(ZoneInfo("Asia/Seoul"))`.
- **수용 기준**: 응답 KST 시각·phase 정확, deprecation 경고 제거.
- **고려/리스크**: isoformat에 offset 추가 → 프런트 파서 가정 확인(S-01과 일괄).

### 프론트엔드 (web/src) — UI 변경은 브라우저 검증 필수

#### W-01 [High] 최상위 ErrorBoundary 부재 → 흰 화면
- **위치**: `web/src/App.tsx`, `main.tsx`, `Layout`(콘텐츠 영역).
- **재검증**: grep `ErrorBoundary|componentDidCatch|getDerivedStateFromError` (0건이어야 현존).
- **문제**: 한 페이지 렌더 예외가 전체 SPA 백지화 → 킬스위치·미체결도 안 보임.
- **근본 원인**: 렌더 예외 격리 계층 부재.
- **수정 방향**: `<ErrorBoundary>` 클래스 컴포넌트를 `Layout`의 콘텐츠 영역에 래핑, fallback은 `.empty-state` 패턴 + 새로고침 CTA, `console.error`로 원인 보존.
- **수용 기준**: 자식 컴포넌트 강제 throw 시 전체가 아닌 콘텐츠 영역만 fallback. 브라우저로 확인.
- **고려/리스크**: 경계를 콘텐츠 영역 단위로(전역이면 한 위젯 오류로 전 페이지 fallback). DESIGN.md 빈 상태 패턴 준수.

#### W-03 [High] Settings 폼 로드 실패 시 silent 증발
- **위치**: `web/src/components/MonitorTools.tsx:93`(getSettings catch), `:112`(if !s return null), `Settings.tsx:139`(렌더).
- **재검증**: `getSettings().catch(()=>{})` + `if(!s) return null` 패턴 확인.
- **문제**: 로드 실패 시 위험 한도+알림 폼 전체가 안내 없이 사라짐 → "기능 없음" 오인.
- **근본 원인**: 로드 실패와 "설정 없음"이 같은 null로 합쳐짐.
- **수정 방향**: `loading|error|loaded` 상태 분리, error면 "불러오지 못함·재시도" 표기. 저장 경로(`:99-110`)는 이미 setMsg로 노출 — 유지.
- **수용 기준**: API 실패 시 폼 자리에 에러+재시도 노출(브라우저로 확인 — 네트워크 차단 후).
- **고려/리스크**: 거의 없음.

#### W-02 [High] Monitor 위험 카드 로드 실패 silent catch
- **위치**: `web/src/pages/Monitor.tsx:46-51`(loadRisk catch ignore), `:34`(marketContext catch null).
- **재검증**: `catch {/* ignore */}` 확인. (메인 `load()`는 setErr로 노출되니 건드리지 마라.)
- **문제**: 포트폴리오 위험 실패 시 카드가 조용히 빈 상태 → "위험 없음" 오인.
- **근본 원인**: 보조 데이터 실패를 "조용히 무시"와 "카드에 표시"로 구분 안 함.
- **수정 방향**: 카드 내부에 "지표 못 불러옴·재시도" 인라인(전역 err까진 불필요).
- **수용 기준**: risk API 실패 시 카드에 실패 표시(브라우저 확인).
- **고려/리스크**: 30초 폴링이라 "직전 성공 + 마지막 실패" 톤다운 권장.

---

## 3. Medium 결함 (15건)

#### S-06 [Med] last_seen 매 요청 commit (`deps.py:46-49`) → 60s throttle 또는 background write. 고려: last_seen 분 단위 정밀도 저하 무방.
#### S-07 [Med] SSE 동기 Session+`asyncio.sleep(2)` (`commands.py:152,179`) → `run_in_threadpool`로 DB 쿼리 위임. 고려: 동작 동일성 유지.
#### C-03 [Med][게이트] 틱 라운딩 백테스트 미적용 (`backtest.py:160,172`) → `_open/_close`에 `round_to_tick` 적용. 고려: slippage와 중복보정 순서 정의, **baseline 재생성**.
#### C-04 [Med][게이트] 소수주 허용 (`backtest.py:161`) → 정수주 내림. 고려: 잔여현금 처리, **baseline 재생성**.
#### CM-01 [Med] slippage 기본값 불일치 (`backtest.py:75`=5bps vs `exec_defaults.py:46`=10bps) → 단일 출처로 통일. 고려: 통일값에 따라 baseline 영향.
#### CM-02 [Med] commission 주석이 세금 누락 은폐 (`exec_defaults.py:45`) → C-01과 함께 정정(세금 분리 명시).
#### P-01 [Med] 정적 성능: `Dashboard.tsx:148-158 reasonFor()` O(n²), `Backtest.tsx` 18 useState, set-state-in-effect → 인덱싱 map·useReducer·useCallback. 고려: 동작 회귀 없게.
#### P-02 [Med] 번들 732kB 단일 청크 → `React.lazy`+`Suspense` 라우트 분할(특히 Backtest·차트), vendor 분리. 고려: lazy 경계 로딩 표시(빈 상태 패턴), 과분할 주의. 검증: `npm run build` 청크 감소 확인.
#### W-EXT [Med][게이트] huddlekit 3rd-party SDK (`web/index.html:16-19`) → **용도 확인 후** 마스킹/동의/환경 게이트 또는 제거. 고려: 금융 DOM 접근 SDK라 데이터 수집 범위 확인 필수(사용자 결정).
#### A-01 [Med] 키보드 포커스 표시 없음 → CSS에서 `:focus-visible`에 가시 outline 부여(`outline-color` 이미 brand로 정의됨). 검증: 키보드 Tab으로 포커스 링 확인(브라우저).
#### W-04 [Med] Pair revoke 확인 없음 + 기기목록 중복 (`Pair.tsx:36-39` vs `Settings.tsx:40-44`) → 공용 컴포넌트 추출(가드 일원화) 또는 Pair에 confirm 추가. 고려: Pair의 IA 역할(NAV 비노출).
#### W-05 [Med] set-state-in-effect (`Monitor.tsx:54`, `Strategies.tsx:52,65`) → Strategies `[mode]→setFilter`는 파생값화, 데이터 패칭은 의도적 `eslint-disable`. 고려: 필터 수동변경 후 모드토글 시 덮어쓰기 UX(브라우저 확인).
#### W-06 [Med] `Login.tsx:37` `any` → GSI 최소 인터페이스 선언 또는 `@types/google.accounts`. 검증: `npm run lint` 1건 감소.
#### W-07 [Med] amber 경고색 하드코딩 (`Monitor.tsx:140-143`, `MonitorTools.tsx:169-172`) → `--amber` 토큰 통일(ReconciliationPanel 패턴).
#### X-02 [Med] 의존성 `>=` 비고정 (server/local `requirements.txt`) → lock 또는 `==` 핀. 고려: 핀 후 `pip-audit`·동작 재확인.

---

## 4. Low 결함 (18건) — 일괄 정리 가능

체크리스트(위치·조치):
- [ ] **S-08** `backtest.py:179` limit=50 하드코딩 → `limit/offset` Query 파라미터.
- [ ] **S-09** `main.py:427-433` `/health/*/refresh` 무인증 공개 → 내부 토큰/rate-limit. (검증: 외부 노출 의도 확인)
- [ ] **S-10** `config.py:11` `SECRET_KEY` 기본값 → 프로덕션 부팅 시 기본값이면 fail-fast. **(보안 — 우선 처리 권장)**
- [ ] **S-11** `db.py:99-100` `_migrate` 예외 print → `_log.exception` 격상.
- [ ] **L-05** `trader.py:317-320` 가중평균 ZeroDiv 방어 1줄(사실상 안전).
- [ ] **L-06** `trader.py:711,182`·`intraday_loop.py:122,147,191` `date.today()` naive → `datetime.now(ZoneInfo("Asia/Seoul")).date()`.
- [ ] **L-07** `trader.py:442-446` 즉시체결 데드코드 정리(의도-구현 불일치).
- [ ] **L-08** `killswitch.py:48-59` reset 프로세스 간 잠금 없음 → 명시적 가드 검토.
- [ ] **L-09** `intraday_loop.py:96-109` WS 체결 중복 dedup 키 추가.
- [ ] **L-10** 단일종목 한도 `pct_cash` 모드 미적용·섹터 한도 전무 → 도메인 체크리스트 4.3.
- [ ] **CM-03** `_gap_extra:144-155` 갭비용 next_open 한정 — 문서화.
- [ ] **CL-01** `indicators.py:143,156` volume_ratio/adv 부분 0거래일 inf 방어.
- [ ] **CL-02** parquet `tz_localize(None)` (`data_fetcher.py:341`) — KST 가정 문서화.
- [ ] **X-01** requirements.txt 한글 주석 cp949 → ASCII 주석(CI 안정화).
- [ ] **X-03** `technical_cache.py` E701 21건 → `ruff --fix`.
- [ ] **web Low** EventBadge 색 하드코딩 / Strategies 매도규칙 중복 카운트 / ScreenerPanel `krPresets.length` 가드.

---

## 5. 재작업 금지 — 이미 검증된 FIXED / 오진

아래는 2일 전 qa_findings에서 지적됐으나 **이미 해결됐거나 오진**임을 이번에 코드·런타임으로 확인했다. **다시 "고치지" 마라.** (현재도 그러한지 1회 확인만 하고 넘어가라.)

| 항목 | 판정 | 근거 |
|---|---|---|
| Settings 위험한도 UI 부재 | **오진(존재)** | `MonitorTools.tsx:125-149` 폼 렌더 확인(런타임) |
| Backtest localStorage prefill | **오진** | `Backtest.tsx:88-110` api.symbols 첫 종목(서버 데이터) |
| 페어링 0인데 stale 표시 / "킬스위치 정상" | **FIXED** | `Dashboard.tsx:64,417` gating·N/A |
| auth.tsx me() silent catch | **오진** | `auth.tsx:23` 토큰 정리 후 Login 라우팅(의도) |
| server Device/PairingRequest 다중토큰 | **오진** | `auth.py:153-156` 단일 트랜잭션 |
| 모바일 375px 깨짐 | **FIXED** | 런타임 측정: 가로 overflow 0, 사이드바→상단바 |
| 로컬앱 다운로드 비활성 | **활성화됨** | Settings에서 활성 링크 렌더(href=VITE_LOCAL_APP_URL 확인) |
| 즉시체결 중복발주 | **미발화(데드코드)** | `trader.py:442-446` (정리는 L-07) |
| 해외 1원 주문 / 토큰 평문 / pending 평문 / preview 강제청산 | **FIXED(Phase 41)** | `kis_broker.py:434,75-81`, `runner.py:149-215`, `sync_client.py:114-144` |

또한: **자격증명 격리는 server·local 모두 위반 없음**(grep 0건, payload는 안전정보만). 이 경계를 새로 만들지 말고, 수정 중 깨뜨리지만 마라.

---

## 6. 권장 작업 순서 (배치)

근접한 변경끼리 묶어 회귀 검증을 효율화하라:

1. **보안 배치(서버)**: S-04(SSRF) + S-10(SECRET_KEY) + S-09. → `pytest tests/`, 수동 URL 검증.
2. **시간/tz 배치(서버)**: S-01 + S-02 + (L-06 로컬). → 일괄 `ZoneInfo("Asia/Seoul")` 규율.
3. **로컬 자금안전 배치**: L-02(원자 저장) → L-01(멱등성, 설계 승인) → L-04(over-sell) → L-03(휴장일). 각 단위 테스트 + 모의 검증.
4. **백테스트 정확성 배치(게이트)**: C-02(log, baseline 영향 적음 우선) → [승인 후] C-01·C-03·C-04·CM-01·CM-02 + golden baseline 재생성.
5. **프론트 신뢰성 배치**: W-01(ErrorBoundary) → W-03 → W-02 → A-01 → W-04~W-07. 브라우저 검증.
6. **성능/공급망**: P-02(코드분할) + P-01 + X-02 + X-03.
7. **server 안정성**: S-03 + S-05 + S-06 + S-07.

각 배치 후 §1 신호로 회귀 확인. 게이트(C-01/C-03/C-04/W-EXT/L-01 설계) 항목은 사용자 승인 전 구현 금지.

---

## 7. 보고 형식 (작업 후)

각 이슈에 대해: **검증 결과(현존/이미해결/오진) → 조치(수정/보류/사용자결정대기) → 변경 파일 → 검증 신호(테스트·lint·브라우저) → 잔여/리스크**. 게이트 항목은 설계안과 함께 사용자 결정을 요청하라. **push는 명시 허락 전까지 금지.**

---

*근거 상세는 같은 폴더의 `FINDINGS_REPORT.md`(6필드 분석·근거 file:line), 환경/도메인 기준은 `../../QUANT_DOMAIN_CHECKLIST.md`, `../../../CLAUDE.md`, `../../../DESIGN.md` 참조.*
