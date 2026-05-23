# FINDINGS_REPORT — 진단 전용 풀리뷰 (REPORT-ONLY)

- **생성**: 2026-05-23 01:04 (KST) · **모드**: REPORT-ONLY (코드 수정·commit·push 없음)
- **기준**: REVIEW_PLAYBOOK.md Phase 0~9 + QUANT_DOMAIN_CHECKLIST.md + CLAUDE.md 보안/협업 원칙
- **방식**: gstack 스킬 부재 → 동등 수동 진단. 읽기 전용 신호 명령 직접 실행 + 4개 영역(local·server·core·web) 병렬 심층 정독(서브에이전트) + 진단자 종합·spot-verify.
- **관측 한계**: bun 미설치로 dev 서버 기동 불가 → Phase 2·3 **브라우저 런타임 미관측**(정적 분석으로 갈음, 런타임 항목은 각 결함 ⑥에 명시). codex 미설치 → Phase 5 skip. 이전 리뷰 폴더 없음 → 추세 비교 불가(첫 산출물).

각 결함은 6필드로 기록: ①문제 사항(위치·근거) ②왜 문제인가(영향) ③근본 원인(구조적) ④방향성에 맞는 해결책 ⑤Trade-off·한계·예상 부작용 ⑥추가 필요 정보·align.

---

## A. 읽기 전용 신호 (Phase 1 / 완료 조건 #3)

| 신호 | 명령 | 마지막 줄 | 판정 |
|---|---|---|---|
| 백테스트 골든 | `pytest tests/golden_backtest.py -v` | `15 passed, 1 skipped, 30 warnings in 193.98s` | ✅ 통과 (log 경고 → C-area) |
| 전체 테스트 | `pytest tests/ -q` | `40 passed, 2 warnings in 11.07s` | ✅ |
| server lint | `ruff check .` | `Found 21 errors. [*] 1 fixable` | ❌ 21 (E701 위주) |
| server type | `mypy app` | `Found 80 errors in 22 files (checked 31 source files)` | ⚠️ 노이즈+일부 |
| web type | `npx tsc --noEmit` | (무출력) exit 0 | ✅ |
| web lint | `npm run lint` | `✖ 10 problems (10 errors, 0 warnings)` | ❌ 10 |
| web 의존성 | `npm audit` | `found 0 vulnerabilities` | ✅ |
| py 의존성 | `pip-audit -r (server·local, 주석제거 사본)` | `No known vulnerabilities found` (both) | ✅ |

> pip-audit 주의: 원본 requirements.txt에 한글 주석(UTF-8) → pip-audit 파서가 Windows cp949로 디코딩 실패(`UnicodeDecodeError`). 소스 미변경, 주석 제거 ASCII 사본으로 감사. **모든 server·local 의존성은 `==`가 아닌 `>=` 비고정** — 재현성/공급망 측면 Medium 권장사항(아래 X-02).

mypy 80건 분류: 대다수 `quant_core` import-path 미설정 + pandas/apscheduler stub 부재(도구 노이즈), `int|None→int`는 SQLModel PK Optional 특성(런타임 안전 — server 에이전트가 commit/refresh 후 사용 확인), `datetime.desc/asc`·`str.in_`은 SQLAlchemy 매핑 컬럼 오탐. 실 런타임 결함으로 승격된 것 없음.

---

## B. SERVER 결함 (FastAPI) — S-01 ~ S-11

> 자격증명 격리(CLAUDE.md §3): `appkey|appsecret|account_number|cano|acct_no` grep → **서버 전체 0건**. 미들웨어는 GZip+CORS뿐, request body echo/로그 없음, `db.py echo=False`. **유출 경로 없음 확인(✅)**. (단 S-04 SSRF는 별개 egress 결함.)

### S-01 [High] APScheduler 재시도 시각이 naive datetime → UTC 배포에서 misfire drop
1. **문제**: `server/app/main.py:70` `run_at = datetime.now() + timedelta(minutes=backoff_min)`을 `add_job(trigger="date", run_date=run_at)`(`:75`)에 사용. scheduler는 `BackgroundScheduler(timezone="Asia/Seoul")`(`:325`).
2. **왜 문제**: naive `run_date`는 KST로 해석됨. Railway(UTC)에서 `datetime.now()`는 UTC 벽시계 → KST로 재해석하면 실제보다 ~9h 과거 시각. "5분 후 재시도"가 과거로 등록되어 default `misfire_grace_time`(1s) 초과 → **조용히 drop**. 외부 fetch(KRX/NAVER/dataset) 한 번 실패 시 backoff 재시도 전체 무력화 → 다음 정시 cron까지 stale 데이터로 preview/screener 동작.
3. **근본 원인**: tz-aware 시간 규율 부재. cron 트리거는 tz를 알지만 동적 date 잡 생성부만 naive `now()`.
4. **해결책**: `run_at = datetime.now(ZoneInfo("Asia/Seoul")) + timedelta(...)` (또는 `datetime.now(timezone.utc)`). 프로젝트 `models.py`가 이미 `datetime.now(timezone.utc)` 패턴 사용 → 동일 규율 적용.
5. **Trade-off**: 거의 없음. 부작용: 우연히 즉시 재실행되던 misfire가 사라지고 정확히 backoff 후 실행(의도된 개선).
6. **추가 정보**: Railway 로그에서 "N분 후 재시도" 직후 실제 재실행 로그 존재 여부 확인 시 확정.

### S-02 [High] `market.py` 세션시각 deprecated `utcnow()` + 수동 +9h
1. **문제**: `server/app/routers/market.py:69-70` `now_utc = datetime.utcnow(); kst = now_utc + timedelta(hours=9)`.
2. **왜 문제**: `utcnow()`는 Py3.12+ deprecated. 한국은 DST 없어 결과값은 맞지만 naive 산술이라 서버가 KST로 배포되면 +18h 오류로 돌변(환경 의존). `phase`(장 시작 전/정규장/마감)가 자동매매 페이지 상단에 노출 → 장 상태 오인 가능.
3. **근본 원인**: tz 라이브러리 미사용(서버만 누락).
4. **해결책**: `datetime.now(ZoneInfo("Asia/Seoul"))` 사용. `kst_now.isoformat()`에 `+09:00` offset 포함되어 프런트 파싱도 명확.
5. **Trade-off**: 거의 없음. 단 isoformat 출력에 offset이 붙어 프런트 포맷터가 처리해야 함.
6. **추가 정보**: 프런트가 `kst_now`를 offset 유무 어느 가정으로 파싱하는지 확인 후 적용.

### S-04 [High] `_post_webhook` URL scheme/host 미검증 → SSRF *(진단자 직접 확인)*
1. **문제**: `server/app/routers/sync.py:49-56` `_post_webhook`이 `s.alert_webhook_url`(사용자 설정값, `models.py:75`)을 검증 없이 `requests.post(url, json=body, timeout=8)`. scheme/host 화이트리스트 없음. `preview_engine.py:388`도 동일.
2. **왜 문제**: 사용자가 `http://localhost:...`, `http://169.254.169.254/...`(클라우드 메타데이터), 사설 IP를 webhook URL로 저장하면 서버가 그 주소로 POST → 내부망 스캔·메타데이터 탈취(SSRF). 멀티테넌트 SaaS에서 자기 계정 설정만으로 서버측 요청 유발.
3. **근본 원인**: 사용자 제어 URL을 egress에 그대로 사용, allowlist 부재.
4. **해결책**: 저장·발송 양 시점에서 (a) `https`만 허용, (b) resolve된 IP가 private/loopback/link-local이면 거부(`ipaddress`), 가능하면 `discord.com`/`hooks.slack.com` 도메인 allowlist.
5. **Trade-off**: 도메인 allowlist는 자체호스팅 webhook 차단(개인 트레이더엔 Discord/Slack이면 충분). IP 차단만으론 DNS rebinding에 약함(완전 방어는 과설계).
6. **추가 정보**: `routers/settings.py`의 webhook 저장 핸들러 구조 확인 후 저장-시 vs 발송-시 가드 위치 결정(발송 시점 가드가 최소 침습).

### S-03 [High] 다중 webhook 동기 인라인 호출이 push 요청 블로킹 (timeout 8s × N)
1. **문제**: `sync.py:55` `requests.post(..., timeout=8)`이 동기 핸들러 `push_snapshot`(`:42`) 안에서 호출. 한 push에서 killswitch/drawdown/preview_missing/daily_loss 등 최대 다수 webhook 순차 발송.
2. **왜 문제**: 느린 webhook 다수면 8s씩 누적(최악 수십 초) 동기 블로킹. 동시 사용자 증가 시 threadpool 고갈 → 전 요청 지연. 알림 발송이 push 응답 latency에 직접 결합된 구조적 결함.
3. **근본 원인**: 알림 발송이 요청-응답 경로에 인라인, fire-and-forget 분리 부재.
4. **해결책**: `BackgroundTasks`(이미 `:14` import, `/complete`에서 사용) 주입해 응답 후 발송. 또는 `httpx.AsyncClient`+`asyncio.gather`. timeout 8s→3~5s.
5. **Trade-off**: BackgroundTask도 같은 프로세스라 진짜 느린 webhook은 워커 점유 — 근본 해결은 큐(Redis/RQ)지만 베타 규모엔 과설계.
6. **추가 정보**: 동시 사용자·webhook 사용률 가정 필요.

### S-05 [High] preview가 데이터 fetch 실패 시 어제 종가로 매수 후보 산출 (상폐/거래정지 위험)
1. **문제**: `server/app/preview_engine.py:36-44` `_prev_close`가 `df["Close"].iloc[-1]`을 날짜 검증 없이 사용. cron fetch 실패 시 예외가 `_run_with_retry`로 전파되어 `data_cache.invalidate()`(`main.py:262`)에 미도달 → 어제 parquet 유지.
2. **왜 문제**: 어제 OHLCV로 매수 후보·예상가를 계산해 preview/webhook에 "내일 매수 N건"으로 노출. 거래정지·상폐 직전 종목 잔존 시 사용자 오인. (실발주는 로컬앱 KIS 현재가 기준이라 자금손실은 로컬 가드 의존 — 서버측은 "잘못된 투명성 정보".)
3. **근본 원인**: dataset as-of 날짜 stale 판정 부재. `_last_date` 계산하나 후보 필터 미사용.
4. **해결책**: `build_user_preview`에서 기준일이 직전 거래일보다 오래되면 `available=False, reason="데이터 갱신 지연"`. 종목별 `data_as_of` 오래된 후보 skip. 거래정지 플래그(KIS 마스터) 활용.
5. **Trade-off**: 너무 엄격하면 연휴 직후 정상 케이스 false-skip(거래일 캘린더 필요). 서버에 휴장일 캘린더 부재 → 단순 휴리스틱은 연휴 오탐.
6. **추가 정보**: 서버 거래일/휴장일 소스 유무, 거래정지 정보가 KIS 마스터에 포함되는지.

### S-06 [Medium] `get_current_device` last_seen 매 요청 commit — write 경쟁·부하
1. **문제**: `server/app/deps.py:46-49` 매 인증마다 `device.last_seen_at=now; add; commit; refresh`.
2. **왜 문제**: 모든 기기 엔드포인트(push/poll/stream/ack/pull)가 매 호출 device row UPDATE. SSE까지 합쳐 빈번한 write — 정합성 손상은 경미(last-write-wins)하나 Postgres 불필요 write·row lock 경쟁.
3. **근본 원인**: 인증 의존성에 부수효과(write) 결합, 관측치를 critical path에.
4. **해결책**: throttle(마지막 갱신 60s 이내면 skip) 또는 background write. SSE는 연결 시 1회.
5. **Trade-off**: last_seen 분 단위 정밀도 저하(모니터링 표시엔 무해).
6. **추가 정보**: 없음.

### Medium / Low (server)
- **S-07 [Medium]** `commands.py:152,179` — SSE event_gen이 동기 `Session` + `await asyncio.sleep(2)` 혼합 → 매 2초 이벤트 루프 짧은 블로킹. 권장: `run_in_threadpool` 또는 async 드라이버.
- **S-08 [Low]** `backtest.py:179` — `list_backtest_runs` `.limit(50)` 하드코딩, pagination 없음. 권장: `limit/offset` Query 파라미터.
- **S-09 [Low]** `main.py:427-433` — `/health/master/refresh` 등 POST refresh가 인증 없이 공개 → 반복 호출 시 외부 소스 rate-limit/부하. 권장: 내부 토큰/rate-limit.
- **S-10 [Low(보안)]** `config.py:11` *(진단자 직접 확인)* — `SECRET_KEY = os.getenv("QP_SECRET_KEY", "dev-insecure-secret-change-me")`. Railway에 `QP_SECRET_KEY` 미설정 시 JWT 위조 가능. 권장: 프로덕션 부팅 시 기본값이면 fail-fast.
- **S-11 [Low]** `db.py:99-100` — `_migrate` 예외를 `print`로 삼키고 계속(CLAUDE.md "예외 무시 금지"와 충돌, 단 멱등 부팅 보호 목적). 권장: `_log.exception`으로 격상.

### qa_findings 재검증 (server)
| qa 항목 | 판정 | 근거 |
|---|---|---|
| main.py:69 datetime naive +9h | **STILL-OPEN (정정)** | `:70` 그대로. 증상은 "+9h"보다 misfire-drop → S-01 |
| market.py:69 utcnow+수동+9h | **STILL-OPEN (정정)** | `:69-70`. DST 무관·결과 맞음, 본질은 deprecated+naive → S-02 |
| deps.py:46 last_seen 경쟁 | **STILL-OPEN** | `:46-49` 매 요청 commit → S-06 (부하 이슈로 재평가) |
| auth.py:150-157 Device/consumed 분리→다중토큰 | **FALSE-POSITIVE** | `:153-156` `add(device); pr.consumed=True; add(pr); commit()` 단일 트랜잭션 + `:148 if pr.consumed` 가드. 원자적 |
| commands.py SSE 동기+sleep | **STILL-OPEN(저위험)** | `:152,179` → S-07 |
| sync.py webhook 실패→last_alerted 미갱신 스팸 | **PARTIAL** | killswitch 경로(`:75-87`)는 cooldown 없음+성공 시만 갱신 → 지속 실패 시 스팸 *(진단자 확인)*. drawdown/daily_loss(`:102`)는 cooldown 1h라 OK |
| preview_engine stale 종목 | **STILL-OPEN** | `_prev_close:36-44` 날짜 무검증 → S-05 |
| sync.py webhook timeout 8s 누적 | **STILL-OPEN** | `:55` → S-03 |
| sync.py _post_webhook SSRF | **STILL-OPEN** | `:49-56` 검증 전무 *(진단자 확인)* → S-04 |
| backtest.py limit=50 하드코딩 | **STILL-OPEN** | `:179` → S-08 |

---

## C. WEB 결함 (React+TS) — W-01 ~ W-06

### W-01 [High] 최상위 ErrorBoundary 부재 → child crash = 흰 화면
1. **문제**: `web/src/App.tsx:12-40`·`main.tsx:9-19` 전체에 `ErrorBoundary`/`componentDidCatch`/`getDerivedStateFromError` 0건. 트리는 `StrictMode>BrowserRouter>AuthProvider>ModeProvider>App`뿐.
2. **왜 문제**: 자동매매에 돈을 맡기는 도구인데 한 페이지 렌더 예외(예: snapshot payload 형태 불일치 시 `.toLocaleString()`)가 전체 SPA를 백지로 → 사용자가 킬스위치·미체결조차 못 봄. DESIGN 신뢰감 원칙 위배.
3. **근본 원인**: 렌더 예외를 fallback UI로 격리하는 계층이 설계에 없음. API 에러는 페이지별 `setErr` 처리하나 렌더-타임 throw는 무방비.
4. **해결책**: `<ErrorBoundary>` 클래스 컴포넌트를 `Layout`의 `main-inner` 래핑(또는 App 바깥). fallback은 `.panel`+`.empty-state` 패턴 "문제 발생 + 새로고침 CTA". `console.error`로 원인 보존(no silent-except).
5. **Trade-off**: 경계가 너무 위면 한 위젯 오류로 전 페이지 fallback → 콘텐츠 영역 단위로 거는 게 적절.
6. **추가 정보**: 에러 리포팅(Sentry 등) 도입 여부 — 있으면 boundary에서 함께 전송.

### W-02 [High] Monitor 위험 카드 로드 실패 silent catch
1. **문제**: `web/src/pages/Monitor.tsx:46-51` `loadRisk()`의 `catch {/* ignore */}`, `:34` `api.marketContext().catch(()=>null)`. (메인 `load()`는 `:38-40` `setErr`로 노출 — 정상.)
2. **왜 문제**: 포트폴리오 위험(상관·섹터 집중)은 "위험 관리" 화면 핵심인데 실패 시 `PortfolioRiskCard`가 조용히 빈 상태 → "위험 없음" 오인. no silent-except 위배.
3. **근본 원인**: 보조 데이터 실패를 "조용히 무시"와 "카드에 실패 표시"로 구분하지 않음.
4. **해결책**: `loadRisk` 실패 시 카드 내부에 "위험 지표 불러오지 못함 · 재시도" 인라인 표기(페이지 전역 err까지 올릴 필요 없음).
5. **Trade-off**: 30초 폴링이라 일시 실패 잦을 수 있음 → "직전 성공 데이터 + 마지막 갱신 실패" 톤다운 표기가 균형.
6. **추가 정보**: `/portfolio/risk`가 포지션 0일 때 4xx인지 빈 200인지(정상 빈 상태 vs 실패 구분).

### W-03 [High] MonitorTools `getSettings` silent catch → 위험한도+알림 폼 전체 증발
1. **문제**: `web/src/components/MonitorTools.tsx:93` `api.getSettings().then(setS).catch(()=>{})`. 실패 시 `s=null` → `:112 if(!s) return null`로 **위험 한도+알림 폼 전체가 안내 없이 사라짐**. 이 컴포넌트가 `Settings.tsx:139`에서 렌더되는 유일한 위험설정 UI.
2. **왜 문제**: 로드 실패 시 사용자는 "설정 기능이 없다"고 오인 → 자동매매 안전장치(킬스위치·drawdown) 설정 불가 = 신뢰성 직결.
3. **근본 원인**: 로드 실패와 "설정 없음"이 같은 `null`로 합쳐짐.
4. **해결책**: 상태를 `loading|error|loaded` 분리. error면 `.panel`에 "설정 불러오지 못함 · 재시도". (저장 경로 `:99-110`은 이미 `setMsg`로 실패 노출 — 양호.)
5. **Trade-off**: 거의 없음.
6. **추가 정보**: 없음. (참고: qa의 "위험한도 UI 부재"는 오진 — 폼은 존재.)

### W-04 [Medium] Pair vs Settings revoke 확인 불일치 + 기기목록 중복 구현
1. **문제**: `web/src/pages/Pair.tsx:36-39` `revoke()`는 확인 없이 즉시 실행. `Settings.tsx:40-44`는 `confirm("...해제할까요?")` 보호. 두 페이지가 기기목록 UI 중복 구현(`Pair.tsx:92-120`).
2. **왜 문제**: 기기 해제는 자동매매를 멈추는 동작인데 한쪽은 오클릭 한 번에 실행. 중복 구현이라 한쪽만 가드 추가됨(향후 또 어긋날 위험).
3. **근본 원인**: DRY 위반. `Settings.tsx:1-6` 주석은 Pair를 "deep-link 전용 빈 진입점"으로 규정하나 실제 Pair엔 완전한 목록·해제가 렌더.
4. **해결책**: 기기목록+페어링 폼을 공용 컴포넌트로 추출(가드 일원화). 차선: Pair를 코드 입력만 남기고 목록 제거. 최소수정: Pair에도 confirm 추가.
5. **Trade-off**: 컴포넌트 추출은 변경 폭 큼. 단 분기 유지 시 재발 위험.
6. **추가 정보**: Pair를 IA에서 계속 노출할지(사이드바 NAV에 `/pair` 없음).

### W-05 [Medium] set-state-in-effect 연쇄 렌더 (lint 신호)
1. **문제**: `Monitor.tsx:53-59`·`Strategies.tsx:51-53`(setFilter on `[mode]`)·`:65`·`Backtest.tsx:88,121` effect 내 동기 set.
2. **왜 문제**: effect→set→재렌더 캐스케이드. 기능은 동작하나 초기 추가 렌더·StrictMode 이중 호출로 폴링 타이머 잠깐 두 번. 코드 위생/성능 신호.
3. **근본 원인**: 데이터 로딩을 effect+다수 useState 수기 관리.
4. **해결책**: `Strategies.tsx:51`의 `[mode]→setFilter`는 파생값화. 데이터 패칭은 현 패턴 유지 + 의도적 `eslint-disable`(이미 `Backtest.tsx:123`·`Login.tsx:68` 선례).
5. **Trade-off**: 과도한 리팩터링 위험. 가장 가치 있는 건 Strategies의 필터 동기화.
6. **추가 정보(런타임 미검증)**: 필터 수동 변경 후 모드 토글 시 선택 덮어쓰기 여부 — 브라우저 확인 필요.

### W-06 [Low→Medium] Login `any` 타입 (lint 신호) *(진단자 확인: `Login.tsx:37`)*
1. **문제**: `web/src/pages/Login.tsx:37` `(window as unknown as { google?: any }).google`.
2. **왜 문제**: `any`가 GSI 콜백 체인 타입 안전성 차단 + lint 게이트 막음(런타임 위험 낮음).
3. **근본 원인**: GSI 글로벌 타입 선언 부재.
4. **해결책**: 최소 인터페이스 선언 또는 `@types/google.accounts` 도입.
5. **Trade-off**: 거의 없음, 5분.
6. **추가 정보**: 없음.

### Medium / Low (web)
- **[Med]** `Monitor.tsx:140-143`·`MonitorTools.tsx:169-172` — 미국 실시간 경고 색 `rgba(240,180,0,..)` 리터럴, DESIGN `--amber` 토큰 미사용(같은 amber인 ReconciliationPanel은 토큰 사용 `Monitor.tsx:423`). 토큰 통일.
- **[Low]** `Monitor.tsx:545` EventBadge cancelled `#f3f4f6` 하드코딩 → 크림 팔레트와 미세 어긋남. `var(--border)` 계열로.
- **[Low]** `Strategies.tsx:205-207` — legacy `sell.conditions`+`sell_rules.conditions` 둘 다 OR 합산 → 마이그레이션 후 중복 카운트 가능(데이터 의존, 미검증).
- **[Low]** ScreenerPanel `krPresets.length>0` 가드 부재 → KR 0·US만 있을 때 빈 "국내" 헤더 노출(`:291` 무조건 렌더). 데이터상 희박.

### Phase-4 코드 리뷰 — ScreenerPanel 미커밋 변경 (KR/US 분리)
`types.ts:454` `market_group?: "KR"|"US"` 추가 정상. ScreenerPanel.tsx: **(a)** KR·US 둘 다 렌더(`:291-298`, US는 `usPresets.length>0`일 때) — "computed but never shown" 버그 없음. **(b)** `renderPresetCard` 헬퍼 `key`·클로저 정상, 두 섹션이 `expanded/previews` 공유하나 key가 preset key라 충돌 없음. **(c)** empty/loading 정상. → **머지 안전**, 위 Low 가드 하나만 선택적 보강.

### qa_findings 재검증 (web)
| qa 항목 | 판정 | 근거 |
|---|---|---|
| auth.tsx:23 me() silent catch | **FALSE-POSITIVE** | `:23` `.catch(()=>tokenStore.clear())`→`:24 finally setReady`→Login 라우팅. 의도된 만료 토큰 정리 |
| MonitorTools:93 / Monitor:50 silent catch | **STILL-OPEN** | W-03 / W-02 |
| Pair vs Settings revoke 불일치 | **STILL-OPEN** | W-04 |
| App.tsx ErrorBoundary 부재 | **STILL-OPEN** | W-01 |
| Settings 위험한도 UI + 토글 부재 | **FIXED** | `MonitorTools.tsx:125-149` kill_switch/max_drawdown 입력, reconcile `:202`/preview `:220`/killswitch `:197` 토글. Settings `:139`서 렌더 |
| Backtest 매수후보 localStorage prefill | **FALSE-POSITIVE** | 출처는 `Backtest.tsx:88-110 api.symbols()` 첫 tradable 종목(서버 데이터). localStorage는 토큰·모드뿐 |
| 페어링 0인데 보유종목 stale 표시 | **FIXED** | `Dashboard.tsx:64 effectiveSnap=connected?snap:null`, `Monitor.tsx:79 paired?...:undefined` |
| Dashboard "킬스위치 정상" 오표시 | **FIXED** | `Dashboard.tsx:417-418 !connected?"—":...` N/A 처리 |
| Mobile 375px 깨짐 | **PARTIAL (정적 FIXED 추정)** | `index.css:1390 @media(max-width:760px)` top-nav 전환, 테이블 `overflow-x:auto`(`:1413`), 900px 1열(`:974`). 375px 실측은 브라우저 필요 |

### Phase-2 디자인 정적 점수 (브라우저 미실행)
| 페이지 | 점수 | 근거 |
|---|---|---|
| Login | 8 | 카드+브랜드+GSI 일관. 약점: 필드 단위 검증 피드백 없음 |
| Pair | 6 | 단계 안내 양호하나 Settings와 중복·confirm 누락·NAV 비노출 |
| Dashboard | 9 | 액션 우선순위·KPI strip·N/A 처리·근거 표시 우수 |
| Monitor | 8 | 상태 표시 풍부. 감점: amber 하드코딩, 보조 로드 silent |
| Strategies | 9 | 카드그리드+3단계 승격모달·"실전 시작" 텍스트 가드 탁월 |
| Backtest | 9 | 문장형 빌더·실시간/EOD 분리·손익 가드 우수. 감점: 폼 길이 |
| Settings | 7 | 통합 IA 합리적·위험한도 폼 존재. 감점: 로드 실패 시 폼 증발(W-03), Pair 중복 |

---

## D. LOCAL APP 결함 (데스크탑 자동매매 — 자금 직접 거래) — L-01 ~ L-10

> 자격증명 격리(규칙 #1): sync push payload(`runner.py:140`→`sync_client.py:31-35 push_snapshot`)는 `balance/positions/equity/trades/decisions/cycle_summary`만 전송. appkey·appsecret·account_no·원시 KIS 응답 미포함. 자격증명은 `secrets_store.py:22-33` **keyring 전용**, 평문 파일 없음. **위반 없음(✅)**.
>
> Phase 41 수정 검증: L항목 1~4(해외 1원 가드·token ACL·pending ACL·preview 캐시 fallback) 모두 현재 코드에 정확히 존재 = **FIXED 확정**.

### L-01 [High] 주문 멱등성 부재 — 크래시·재시작 시 재발주
1. **문제**: `local/localapp/trader.py:142-166` `__init__`은 pending을 디스크 로드하나, 발주 전 "오늘 이 (sid,symbol,side)를 이미 보냈는가" 키가 없음. `order_log.py`는 로깅 전용(dedup 저장소 없음). cycle 도중 `_submit_buy` 직후·`_save()` 전 크래시 시 발주는 KIS에 나갔지만 pending 미기록 → 재시작 시 같은 후보 재발주.
2. **왜 문제**: preview 후보는 매 사이클 재평가 없이 발주되므로 재시작 후 동일 종목 중복 매수 → 의도의 2배 포지션. 실거래 자금 손실.
3. **근본 원인**: 멱등 단위가 "KIS가 돌려준 order_no"뿐 — 발주 *이전* intent 기록 없음. 영속화가 발주와 분리된 사후 `_save()`라 race window.
4. **해결책**: 발주 직전 intent를 원자적으로 append(`(date,sid,symbol,side)`)하고 cycle 진입 시 대조해 skip. 또는 cycle 시작 시 `_daily_ccld()`/`_overseas_ccnl_today()`(이미 존재) 1회 조회로 "오늘 발주됨" reconcile.
5. **Trade-off**: intent 기록 후 발주 실패 시 "유령 intent"가 정상 재시도 차단 → 결과 확정 2-phase 필요(복잡도↑).
6. **추가 정보**: KIS order-cash가 client-side 주문 ID(사용자 지정 ODNO) 지원하는지 — 지원하면 진짜 멱등키. 모의투자 응답에 `filled_qty` 포함되는지 KIS 문서 확인.

### L-02 [High] `_save()` 비원자적 순차 write — 크래시 시 부분 상태·원장 소실
1. **문제**: `trader.py:161-166` `_save()`가 LEDGER→EQUITY→PENDING→REBALANCE 순차 `write_text`. `os.replace`/temp-rename 없음(grep `os.replace|atomic` → 0건).
2. **왜 문제**: ledger 쓴 뒤 pending 전 크래시 → "보유는 늘었는데 미체결 추적 사라짐"(미체결 영원히 미추적). 원장이 truncate 중 깨지면 다음 기동 `_load_json`이 파싱 실패 → `default={}`로 **전체 보유 원장 소실**, 청산이 보유를 모름.
3. **근본 원인**: 다중 파일 트랜잭션을 원자 단위로 다루지 않음. `write_text`는 truncate-then-write라 중간 크래시 취약.
4. **해결책**: 파일별 `tmp.write_text(); os.replace(tmp, path)`(POSIX·NTFS 원자적 rename). 파싱 실패로 인한 전체 소실 제거.
5. **Trade-off**: 4파일 간 cross-consistency는 여전히 미보장(A 후 B 직전 크래시). 완전 해결은 단일 파일 통합/WAL — 과설계 가능.
6. **추가 정보**: `equity.json`은 append-only로 커져 손상 영향 큼 — 보존 정책 확인.

### L-03 [High] KRX 한국 휴장일 캘린더 미적용 — 휴장일 청산·킬스위치 오작동
1. **문제**: `scheduler.py:99-110`은 KRX를 `CronTrigger(day_of_week="mon-fri", hour=8, minute=55)` 고정 발사. `market_calendar.py:27 _FILES={"US":...}` — **KR 미지원**(`session_kst("KR")`는 `CalendarError`). cycle/intraday 어디에도 KR 거래일 게이트 없음.
2. **왜 문제**: 신정·설날·추석·광복절 평일 휴장일에도 loop·cycle·settlement 실행. 신규 발주는 거래소가 거부하나 **청산 패스(`cycle:781-825`)는 휴장일에도 매도 지정가 발주**, kill-switch/drawdown도 stale 시세로 평가, reconcile(15:35)이 휴장일 잔고로 ledger 차감 가능.
3. **근본 원인**: US만 동적 캘린더, KRX는 "평일=거래일" 가정. KR 세션 데이터·헬퍼 부재.
4. **해결책**: `market_calendar`에 KR 세션 추가(`gen_market_sessions.py`에 KRX 포함) 후 cycle·intraday·settlement 진입부에서 `is_session_open("KR")` 가드. US와 동일 패턴 → 구조 일관.
5. **Trade-off**: KR 캘린더 생성·만료 관리 부담(US처럼 주기 재생성). 임시 휴장(재난) 반영 지연.
6. **추가 정보**: `test_market_calendar.py`는 US 전용 — KR 추가 시 테스트 필요. 반일장(연말) 마감시각 반영 여부 align.

### L-04 [High] reconcile가 15:35에만 → 장중 수동매도 후 over-sell
1. **문제**: `trader.py:173-229 reconcile_with_kis`는 15:35 settlement에서만 호출(`runner.py:183`). 장중 `intraday_stop.py:130-137 on_tick`은 ledger `qty`를 그대로 매도 발주, 발주 직전 KIS 실보유 재조회 없음(`_sold_today`로 중복만 방지).
2. **왜 문제**: 사용자가 장중 HTS/MTS로 수동 전량 매도 → ledger엔 남아 있음 → 손절 트리거 시 없는 수량 매도 시도. 운 나쁘면 재매수분까지 잘못 청산, KIS 거부로 끝나도 불필요 발주.
3. **근본 원인**: ledger를 신뢰 원천으로 보고 장중 KIS 정합성 미확인.
4. **해결책**: `on_tick` 매도 직전 KIS 실보유로 `min(ledger_qty, broker_qty)` 클램프, 0이면 ledger 정리·skip. tick마다 전체 조회는 rate-limit 위험 → 짧은 TTL 캐시.
5. **Trade-off**: 빈번 조회는 KIS 초당거래제한(EGW00201) 압박. 캐시 TTL 길면 그 창에서 over-sell 잔존.
6. **추가 정보**: 체결통보 WS(`intraday_loop._on_exec_event`)가 *수동* 매도까지 통지하는지 — 통지되면 ledger 실시간 차감으로 근본 해결.

### Medium / Low (local)
- **L-05 [Low]** `trader.py:317-320` 가중평균 `total`은 양수 합이라 ZeroDivision 불가 → qa#6은 사실상 안전. 방어 1줄은 선택.
- **L-06 [Medium]** `trader.py:711,182`·`intraday_loop.py:122,147,191` `date.today()` naive(로컬TZ). scheduler는 KST지만 cycle 내부 날짜는 PC TZ 의존 → `datetime.now(ZoneInfo("Asia/Seoul")).date()`.
- **L-07 [Low]** `trader.py:442-446` 즉시체결 반영 분기는 `kis_broker._submit_*`가 항상 `filled_qty:0`·`price` 키 없음(`:400,463`)이라 **데드코드**. qa#5의 "즉시체결 중복"은 미발화(위험 낮음)이나 의도-구현 불일치 정리 필요.
- **L-08 [Low]** `killswitch.py:48-59 reset()` + `trader.py:728` cycle이 `load()` 재조회하나 프로세스 간 잠금 없음 → 이론상 reset/cycle 타이밍 race 잔존.
- **L-09 [Low]** `intraday_loop.py:96-109` `filled_so_far` 누적: 동일 `(order_no, CNTG_QTY)` 중복 WS 통지 시 이중 가산 가능(고유키 dedup 부재).
- **L-10 [Low]** 단일종목 한도 `max_position_pct`는 `_atr_qty`(`:138`)만 적용, `pct_cash` 모드(`:547`) 미적용, **섹터 한도 전무** → 도메인 체크리스트 4.3 미충족.

### qa_findings 재검증 (local)
| qa 항목 | 판정 | 근거 |
|---|---|---|
| 1. 해외 시장가 0→1원 | **FIXED** | `kis_broker.py:434,440-443` ≤0이면 현재가 조회·실패 시 `raise` |
| 2. token 평문 권한 | **FIXED** | `kis_broker.py:75-81 restrict_to_owner` + `file_security.py:44-60 icacls` |
| 3. pending snapshot 권한 | **FIXED** | `runner.py:149-152,213-215 restrict_to_owner` |
| 4. preview 실패→강제청산 | **FIXED** | `sync_client.py:114-144` 24h 캐시, 404/available=False만 무시 |
| 5. 즉시체결 재시도 중복 | **PARTIAL** | `:442-446` 분기는 데드코드(미발화). 별개 멱등성(L-01) STILL-OPEN |
| 6. 가중평균 ZeroDiv | **FALSE-POSITIVE** | `:317-320` total 양수 합 |
| 7. killswitch reset 우회 | **PARTIAL** | `killswitch.py:48-59`+`:728` 재조회하나 잠금 없음(L-08) |
| 8. risk_limits 실패 default fallback | **STILL-OPEN** | `sync_client.py:53-61` 실패 시 `{}` → `:738-743` 글로벌 default, 캐시 미사용 |
| 9. WS 체결 dedup | **STILL-OPEN** | `intraday_loop.py:96-109`(L-09) |
| 10. reconcile 15:35만 | **STILL-OPEN** | `trader.py:173`+`runner.py:183`(L-04) |
| 11. _save 비원자 | **STILL-OPEN** | `trader.py:161-166`(L-02) |
| 12. date.today() naive | **PARTIAL** | scheduler KST 수정(`:36,91`), cycle/intraday 내부 naive(L-06) |
| 13. KR 휴장일 캘린더 | **STILL-OPEN** | `market_calendar`는 US 전용(`:27`)(L-03) |

---

## E. CORE 백테스트/엔진 도메인 결함 — C-01 ~ C-02 (+ 체크리스트)

> golden 테스트 실제 재실행: **15 passed, 30 warnings**. 틱표·룩어헤드·자본곡선은 검증 통과(아래). 핵심 결함 2건은 코드에서 실측 확인.

### C-01 [High] 한국 매도세(거래세+농특세 0.23%) 미반영 → 백테스트 수익률 과대평가
1. **문제**: `core/quant_core/backtest.py:169-184 _close()`는 매도 체결을 `proceeds = shares*price*(1 - commission)`로만 계산, 매도세 항목 전무. `commission` default 0.00015(0.015%)는 위탁수수료 수준.
2. **왜 문제**: KRX 매도세는 코스피 0.18%+농특세 0.05%=**0.23%**(코스닥 0.18%). 매도마다 ~0.23%p 비용 누락 → 백테스트가 실제보다 낙관. 회전율 높을수록(골든 `03_uptrend` 246거래) `total_return·cagr·win_rate·sharpe` 모두 상향 편향. 핵심 가치제안(백테스트 신뢰)을 훼손.
3. **근본 원인**: 비용 모델이 commission/slippage 2개뿐, "매수=매도 대칭" 가정. 한국시장의 매수 무세금/매도 유세금 **비대칭**을 표현할 파라미터 부재.
4. **해결책**: `_close()`에만 적용되는 `sell_tax`(default 0.0023) 파라미터 추가 → `proceeds = shares*price*(1-commission-sell_tax)`. `ExecutionPolicy`/`DEFAULT_EXECUTION`에 `bt_sell_tax_bps`(default 23) 신설.
5. **Trade-off**: `golden_baseline.json` 전 케이스 수치 변경 → **baseline 재생성 필요(회귀 테스트 무효화 — 사용자 결정 필요)**. 코스피/코스닥 구분은 종목코드만으론 불완전 → 우선 보수적 0.23% 단일 적용 권장.
6. **추가 정보**: 종목별 시장(KOSPI/KOSDAQ) 메타 소스 확인 필요. ※이전 리뷰가 High로 식별했으나 **현재 코드 미수정** 재확인.

### C-02 [High] `log()` divide-by-zero — 매크로 음수/0 Close 종목에서 지표 오염·신호 누락
1. **문제**: `core/quant_core/indicators.py:22`(add_returns `np.log(Close/Close.shift)`), `:121`(realized_vol), `:131`(zscore). 골든 실행 시 `divide by zero in log` 14회 + `invalid value in log` 14회. 원인: `load_all()` 3972심볼 중 **9개 매크로 시계열(실질기준금리·장단기금리차·신용스프레드·미국채3M=0 등) Close가 0·음수**.
2. **왜 문제**: 현재는 매매종목(005930)엔 음수 없고 Sharpe/CAGR/MDD가 `pct_change` 기반(`backtest.py:40-42`)이라 **수익지표는 미오염**. 그러나 ⑴매크로 종목을 조건 좌변으로 쓰면 `log_return_1d·realized_vol·zscore`가 −inf/NaN → `_condition_mask:225 fillna(False)`로 **신호 조용히 누락**, ⑵금리차·스프레드(0 교차가 의미)에 로그수익률 적용 자체가 도메인 오류.
3. **근본 원인**: 가격(양수 전제)용 지표를 음수 가능 레벨 시계열에 무차별 적용. price-positive 지표와 level 지표 미구분.
4. **해결책**: 로그 계열은 `Close>0` 마스킹 후 계산(`np.log((s/s.shift).where(s>0 & s.shift>0))`) 또는 음수 가능 심볼군엔 로그 지표 미산출 분기. 경고를 `filterwarnings("ignore")`로 덮지 말고(no silent-except) NaN 명시 치환.
5. **Trade-off**: 매크로에서 로그수익률/변동성 제거 시 해당 지표 손실 — 단 금리차엔 애초에 무의미하므로 실손실 없음.
6. **추가 정보**: 어떤 사용자 전략이 매크로 종목을 좌변으로 쓰는지 사용 빈도 확인 시 우선순위 조정 가능.

### 도메인 체크리스트 판정 (QUANT_DOMAIN_CHECKLIST 기준)
| 항목 | 판정 | 근거 |
|---|---|---|
| 룩어헤드(종가신호→익일시가) | ✅ | `backtest.py:128,190-196` next_open, 골든 `test_no_lookahead_bias` 5/5 |
| 지표 음수 shift 부재 | ✅ | `indicators.py` 전부 `shift(1)`; `analysis.py:545 shift(-d)`는 분석엔진 전용 |
| 슬리피지·수수료 양방향 | ✅ | 매수 `:160` 매도 `:172-173` 모두 적용 |
| **매도세 0.23%** | ❌ | C-01 |
| **틱 라운딩 체결경로 호출** | ❌ | `round_to_tick`이 `local/trader.py`만 사용, `backtest.py:160,172`는 raw가격+slippage만 → **모의/실전과 체결가 모델 불일치**(아래 C-03). 단 틱표 `:75-83`은 2023 개편과 ✅ 일치 |
| 기업액션(수정주가) | ⚠️ | KR `fdr`(NAVER, 통상 수정주가) but 명시 flag 없음; yfinance `auto_adjust=True` ✅ |
| 자본곡선 일관성 | ✅ | `:235 equity=cash+shares*close` 매 루프 |
| 포지션 사이징 라운딩 | ⚠️ | `:161` 소수주 허용, **1주 정수 라운딩 없음**(한국주식 정수주만) → 미세 낙관(C-04) |
| 당일 룩어헤드(signal_mask) | ✅ | 당일 종가신호→익일 시가체결 분리 |

### Medium / Low (core)
- **C-03 [Medium]** 틱 라운딩이 백테스트 체결경로 미적용(위 ❌) → 모의/실전 가격모델 불일치. 권장: `_open/_close`에서 `round_to_tick` 적용.
- **C-04 [Medium]** `backtest.py:161` 소수주 허용 → 정수주 라운딩 추가 권장.
- **CM-01 [Medium]** slippage default 불일치: `backtest.py:75=0.0005(5bps)` vs `exec_defaults.py:46 bt_slippage_bps=10`. 함수 직접호출 5bps vs 전략경유 10bps로 결과 상이.
- **CM-02 [Medium]** `exec_defaults.py:45` 주석이 25bps를 "위탁+거래세 평균"이라 표기 → C-01 세금 누락을 부분 은폐. 세금은 매도 비대칭 적용이 정확.
- **CM-03 [Low]** `_gap_extra:144-155` 갭비용이 next_open 모드만 — 의도된 동작이나 문서화 권장.
- **CL-01 [Low]** `indicators.py:143,156` volume_ratio/adv가 부분 0거래일에 inf 가능(일부 `replace(0,nan)`로 완화).
- **CL-02 [Low]** parquet `tz_localize(None)`(`data_fetcher.py:341`) naive → 백테스트가 KST 강제 안 함.

---

## F. Phase 6 성능 — 정적 관찰만 (런타임 측정 불가)

benchmark 툴(gstack)·dev 서버(bun) 부재 → **Lighthouse/Core Web Vitals/bundle 실측 불가**. 정적 관찰:
- **P-01 [Medium]** 불필요 재렌더·연산: `Dashboard.tsx:148-158 reasonFor()` 이중 루프 O(n²)(qa 지적, 미재검증), `Backtest.tsx` 18개 useState(거대 컴포넌트), set-state-in-effect 캐스케이드(W-05). 권장: 인덱싱 map화, useReducer, useCallback.
- bundle/네트워크 워터폴/LCP·CLS·INP는 **관측 불가 — 사용자 개입 필요**(dev 서버 또는 Vercel preview URL에서 Lighthouse 실행). 다음 회차 권장.

---

## G. 환경·공급망·툴링 (Cross-cutting)

- **X-01 [Low]** pip-audit가 requirements.txt 한글 주석을 cp949로 디코딩 실패 → 주석제거 ASCII 사본으로 우회. 권장: requirements.txt를 ASCII 주석으로(또는 주석 제거)해 CI 안정화.
- **X-02 [Medium]** server·local 의존성 전부 `>=` 비고정 → 재현 불가능 빌드·예기치 않은 breaking 업데이트 위험. 권장: lock 파일 또는 `==` 핀.
- **X-03 [Low]** `server/app/technical_cache.py` E701 다수(ruff 21건) — 한 줄 다중 statement. 가독성·정적분석 방해. 권장: `ruff --fix` + 포맷.

> 자격증명 격리(보안 핵심)는 server(grep 0건)·local(payload 검증·keyring 전용) 양측 **모두 위반 없음 확인**. 의존성 취약점 0건(pip-audit·npm audit). → 가장 치명적인 Critical급 위험(자격증명 유출)은 **현재 없음**.

---

## H. Phase 0~9 커버리지 (완료 조건 #2)

| Phase | 상태 | 근거/산출 |
|---|---|---|
| 0 환경 | ✅ 완료 | `phase0-environment.md` (git·도구·skip 판정) |
| 1 health | ✅ 완료 | ruff/mypy/tsc/eslint/pytest 실측, `phase1-health.md`, 본문 §A |
| 2 design | ✅ 정적+런타임 | 7페이지 0-10 점수(§C) + 런타임 렌더·모바일 375px·포커스 실측(§M). bun 없이 npm dev로 돌파 |
| 3 qa | ✅ 정적+런타임 | qa 재검증 + 로그인 세션으로 개요·설정·전략만들기 순회·작동 실측(§M). 데이터 있는 계정 재확인만 잔여 |
| 4 code review | ✅ 완료 | 미커밋 diff(ScreenerPanel/types — 머지 안전) + server/local/core 변경 리뷰 |
| 5 codex | ⊘ skipped | codex 미설치, `phase5-codex.md` |
| 6 perf | ✅ 실측 | §M-3. 프로덕션 번들 732kB(gzip 215kB)·FCP 240ms 실측. Lighthouse 종합·프로덕션 RTT만 잔여 |
| 7 security | ✅ 완료 | 자격증명 격리 grep(0건)+payload 검증, SSRF(S-04)·SECRET_KEY(S-10), pip-audit·npm audit clean |
| 8 domain | ✅ 완료 | 체크리스트 7카테고리 판정(§E)+golden 회귀(15 passed)+C-01/C-02 |
| 9 summary | ✅ 완료 | 본 FINDINGS_REPORT.md |

---

## I. 우선순위 매트릭스 (완료 조건 #5)

| 심각도 | 건수 | 결함 ID |
|---|---|---|
| **Critical** | **0** | (자격증명 유출·1원 주문·평문 토큰 등 Critical급은 검증 결과 부재/수정완료) |
| **High** | **14** | S-01 S-02 S-03 S-04 S-05 · W-01 W-02 W-03 · L-01 L-02 L-03 L-04 · C-01 C-02 |
| **Medium** | **15** | S-06 S-07 · W-04 W-05 W-06 W-07(amber) · L-06 · C-03 C-04 CM-01 CM-02 · P-01 · X-02 · **W-EXT P-02 A-01**(런타임 발견) |
| **Low** | **18** | S-08 S-09 S-10 S-11 · L-05 L-07 L-08 L-09 L-10 · W(EventBadge·Strategies카운트·ScreenerPanel가드) · CM-03 CL-01 CL-02 · X-01 X-03 |

> 런타임 검증(§M)으로 신규 Medium 3건(W-EXT huddlekit·P-02 번들·A-01 포커스) 추가, 다수 qa 항목 FIXED 재확인(모바일·Settings폼·다운로드·N/A·prefill). High/Critical 변동 없음.

> High 중 **Critical 인접(자금/보안)**: L-01(중복발주)·L-03(휴장일 청산)·S-04(SSRF). 단 모두 조건부(크래시 창·휴장일·악성 webhook URL 설정)이고 직접적 손실/침해 증거는 미확보라 High로 분류. 자산손실 직결 Critical급(1원 주문·평문 토큰·강제청산)은 Phase 41에서 수정 확인됨.

## J. 5개 관점 점수 (0-10, 정적 기준 — 런타임 미관측)

| 관점 | 점수 | 근거 |
|---|---|---|
| UX/사용성 | 7.0 | 7페이지 정성 우수(평균 8)이나 ErrorBoundary 부재(W-01)·설정폼 silent 증발(W-03)·위험카드 silent(W-02). 브라우저 미검증 |
| Visual design | 7.5 | DESIGN.md 토큰 체계 준수도 높음. 감점: amber 등 일부 색 하드코딩, 모바일 375px 실측 미검증 |
| Engineering | 6.0 | tsc clean·전 테스트 통과 ✅이나 mypy 80·ruff 21·eslint 10, naive datetime(S-01/02), 비원자 저장(L-02), 멱등성 부재(L-01) |
| Product | 6.5 | 기능 풍부(문장형 빌더·승격 가드·킬스위치/drawdown UI). 단 백테스트 정확성(C-01 매도세)·도메인 갭이 핵심 가치 훼손 |
| System Trading 도메인 | 5.5 | 자격증명 격리 ✅ 탁월. 그러나 매도세 누락(C-01)·KR 휴장일 부재(L-03)·틱 라운딩 백테스트 미적용(C-03)·멱등성(L-01)·log 오염(C-02) |
| **종합(평균)** | **6.5** | 보안·자격증명 강점, 도메인 정밀도·복원력 약점 |

## K. 자체 점검표 — 6필드 충족 (완료 조건 #4)

전 6필드(①문제 ②왜 ③근본원인 ④해결책 ⑤trade-off ⑥추가정보)를 채운 **정식 결함 18건**. 백로그 요약 항목(Low 및 일부 Medium 한 줄)은 설계상 triage 노트로, 6필드 대상이 아님(REVIEW_PLAYBOOK 8-A의 "Medium/Low 한 줄" 규정).

| ID | ① | ② | ③ | ④ | ⑤ | ⑥ |
|---|---|---|---|---|---|---|
| S-01 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S-02 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S-03 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S-04 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S-05 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S-06 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| W-01 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| W-02 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| W-03 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| W-04 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| W-05 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| W-06 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| L-01 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| L-02 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| L-03 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| L-04 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| C-01 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| C-02 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**18/18 결함 6필드 충족 — ❌ 없음.**

---

## L. 종합 결론 (Executive Summary)

**핵심 메시지**: 보안·자격증명 격리는 견고하고(규칙 #1 양측 위반 0건, Phase 41 자금안전 수정 4건 검증), 자동 검사(tsc/전체 pytest/의존성 audit)는 통과. 위험은 **자동 도구가 못 잡는 도메인 정밀도와 장애 복원력**에 집중.

**가장 시급한 5건 (ROI 순)**:
1. **C-01 매도세 0.23% 미반영** — 백테스트가 핵심 가치제안인데 수익률을 체계적으로 과대평가. (단 baseline 재생성=사용자 결정)
2. **L-03 KRX 휴장일 캘린더 부재** — 휴장일에 청산·킬스위치가 stale 시세로 오작동. US만 캘린더 존재.
3. **L-01 주문 멱등성 부재** — 크래시·재시작 시 중복 발주 → 2배 포지션(실자금).
4. **S-04 webhook SSRF** — 사용자 설정 URL 미검증, 내부망/메타데이터 접근 가능.
5. **W-01 ErrorBoundary 부재** — 단일 렌더 예외가 전 화면 백지화(킬스위치도 안 보임).

**의외 정정 (qa_findings 2일 전 대비)**:
- Settings 위험한도 UI "부재"는 **오진** — 이미 구현됨(`MonitorTools.tsx:125-149`).
- Backtest localStorage prefill은 **FALSE-POSITIVE**(서버 데이터).
- 페어링-stale 표시·"킬스위치 정상" 오표시·auth silent catch는 모두 **FIXED**.
- server auth Device/PairingRequest "다중토큰 우회"는 **FALSE-POSITIVE**(이미 단일 트랜잭션).
- 즉시체결 중복발주 경로는 **데드코드**(미발화).

**관측 한계(사용자 개입 필요)**: ⑴브라우저 런타임(Phase 2·3 인터랙션·모바일 375px·접근성)은 bun 미설치로 미검증 → dev 서버 기동 후 재확인. ⑵Phase 6 성능 실측(Lighthouse/bundle) 미수행. ⑶C-01 적용 시 golden baseline 재생성 결정 필요. ⑷S-04 가드 위치(저장 vs 발송)는 settings 핸들러 확인 후 결정.

**다음 회차 권장**: bun 설치 → dev 서버 → Phase 2·3·6 런타임 검증. 그리고 위 5건 중 사용자가 우선순위를 정해 설계→승인→구현(REPORT-ONLY 종료, 본 문서는 진단까지).

---

## M. 런타임 검증 — 관측 한계 돌파 (2026-05-23 dev 서버 실측)

**돌파 방법**: bun 없이도 Vite는 `npm run dev`로 기동 가능(이미 :5173 실행 중) + uvicorn(:8000) 가동 상태. `designtest@example.com` 세션 로그인 상태에서 preview 브라우저로 실측 → 이전 "브라우저 미관측" 한계 해소.

### M-1. 런타임으로 확인된 FIXED/정상 (이전 미검증)
- **모바일 375px 반응형 = FIXED**: `aside.sidebar`가 `flex-direction:row`·sticky 상단바로 전환, `scrollWidth==viewport==375`, **가로 overflow·이탈 요소 0개**. qa P1 "사이드바 그대로·글자 깨짐" 해소. (단 빈 데이터 기준 — 보유종목 테이블 5컬럼은 포지션 데이터 없어 미검증 → 데이터 있는 계정에서 재확인.)
- **Settings 위험한도 폼 = FIXED**: Kill Switch·Drawdown spinbutton, webhook URL, killswitch/reconcile drift 체크박스, preview 임계, 미국 매수여력 모드, 저장 버튼 전부 렌더. qa "위험한도 UI 부재" 오진 재확인.
- **로컬앱 다운로드 활성화**: "Windows용 로컬앱 다운로드"가 `<a><button>` 활성 링크(qa P0 "다운로드 비활성" 해소 추정 — href=VITE_LOCAL_APP_URL 값 확인 권장).
- **Dashboard N/A 처리 = FIXED**: 미연결 시 킬스위치 "—", 로컬앱 "미연결" 정확.
- **Backtest 문장형 빌더 정상 작동**: 매수대상→빈칸 문장 조건→매도 ①장중 실시간/②EOD 분리→리스크/가정/자금. ATR 충돌 안내 표시. 핵심 차별점 작동(설계 9점 타당).
- **000020 동화약품 prefill**: 런타임 확인 — 출처는 `api.symbols` 첫 tradable(서버 데이터)이지 localStorage 잔재 아님(FALSE-POSITIVE 확정). "신규 전략 자동 prefill이 바람직한가"는 UX 결정 사항.
- 개요·설정·전략만들기에서 React 크래시·흰 화면 없음. 콘솔 에러는 외부 huddlekit뿐(W-EXT).

### M-2. 신규 결함 (런타임 발견)

**W-EXT [Medium] 금융 앱이 3rd-party SDK(huddlekit)를 진입 HTML에 직접 로드 — init 실패·DOM 접근 우려**
1. **문제**: `web/index.html:16-19` `<script src="https://app.huddlekit.com/sdk/huddlekit.js" data-project-key="pk_live_unxN0R8f8nRjVSU7UCzI" async>`. 매 로드 콘솔 `[Huddlekit] Initialization failed: Origin not allowed` 반복.
2. **왜 문제**: 잔고·체결가·전략이 표시되는 DOM에 외부 세션 SDK가 접근 가능 → 민감 금융정보 캡처 우려. localhost init 실패=origin 미등록. 실패해도 매 로드 네트워크·콘솔 노이즈.
3. **근본 원인**: 위젯/세션 SDK를 진입 HTML에 무조건 로드, 환경·동의 기반 분기 없음.
4. **해결책**: huddlekit 용도(피드백/세션리플레이/분석) 명확화 → 금융정보 마스킹 설정 또는 동의/환경 게이트, 불필요 시 제거.
5. **Trade-off**: 제거 시 해당 기능 상실. 마스킹은 SDK 설정 의존.
6. **추가 정보**: huddlekit이 무엇이고 어떤 데이터를 수집하는지 사용자 확인 필요(pk_live는 publishable이라 노출 자체는 통상 정상).

**P-02 [Medium] 단일 청크 732kB(gzip 215kB) — 라우트 코드 스플리팅 없음**
1. **문제**: `npm run build` → `index-*.js 732.24kB (gzip 215.46kB)`, Vite 경고 ">500kB, dynamic import 권장". 605 모듈 단일 번들.
2. **왜 문제**: 7페이지·차트가 모두 초기 로드 → 로그인 직후·저사양/모바일에서 TTI 지연. 개요만 보려는 사용자도 Backtest 코드까지 다운로드.
3. **근본 원인**: 라우트 기반 lazy import 부재(전 페이지 정적 import).
4. **해결책**: React.lazy + Suspense 라우트 분할(특히 Backtest·차트), vendor 청크 분리.
5. **Trade-off**: lazy 경계 로딩 표시 필요(빈 상태 패턴 재사용). 과분할은 워터폴↑ — 라우트 단위 적정.
6. **추가 정보**: 프로덕션 gzip 215kB는 수용 가능하나 성장 시 악화 — 차트 라이브러리 크기 확인.

**A-01 [Medium] 키보드 포커스 표시 없음 (WCAG 2.4.7)**
1. **문제**: nav 링크 `.focus()` 시 computed `outline-style:none, outline-width:0, box-shadow:none`(outline-color는 brand 오렌지로 정의돼 있으나 style:none이라 미렌더).
2. **왜 문제**: 키보드 사용자가 포커스 위치를 볼 수 없음. 정확성이 중요한 자동매매 도구에서 키보드 내비 저해.
3. **근본 원인**: CSS 리셋이 `:focus{outline:none}`을 걸고 `:focus-visible` 대체 미제공 추정.
4. **해결책**: `:focus-visible`에 가시 outline/box-shadow(이미 정의된 brand outline-color 활용).
5. **Trade-off**: 거의 없음(마우스 클릭 시 :focus-visible 미표시라 노이즈 없음).
6. **추가 정보**: 프로그램적 focus 측정 — 키보드 Tab의 :focus-visible 최종 확인 권장.

### M-3. Phase 6 성능 실측 (이전 "관측 불가" → 실측)
- 프로덕션 번들: JS 732kB(gzip 215kB), CSS 38.5kB(gzip 7.3kB), build 763ms → P-02.
- dev 런타임(대표성 제한): FCP 240ms, domInteractive 70ms, load ~997ms. 정적 O(n²)/거대 컴포넌트(P-01)는 코드 기준 유지.
- 미수행: Lighthouse 종합·프로덕션 URL 실 RTT(프로덕션 기준 측정 권장).

### M-4. 코드 잔여 항목 해소 (런타임/정독)
- **C-01 정정**: Backtest "5.백테스트 가정"이 수수료를 **"위탁수수료+거래세 합산 25bps(=0.25%) 권장·매수/매도 양쪽 적용"**으로 안내 → 세금을 별도 모델 없이 commission에 **대칭 흡수**. 한국 매도세는 매도 단방향 0.23%인데 양방향 0.25%면 부정확(라운드트립 0.50% vs 실제 ≈0.26%). 즉 C-01은 "비용 전무"가 아니라 **부정확한 대칭 세금 모델**(CM-02 확정) + **엔진/UI 기본값 불일치**(CM-01: 엔진 slippage 5bps vs UI 10bps). 사용자가 UI 권장 25bps를 쓰면 오히려 보수적, 엔진 default(0.015%)면 낙관 — 일관성 결여가 본질.
- **C-01 ⑥ 해소**: KOSPI/KOSDAQ 메타 존재(`ticker_db.py:34-35` exchange 필드, KIS 마스터 KOSPI/KOSDAQ) → 매도세 차등 적용 가능.
- **S-04 정밀화**: `server/app/routers/settings.py:45-81 put_settings`는 범위·enum은 검증하나 `alert_webhook_url`은 무검증 저장(`:50`). UI placeholder가 Discord/Slack 제안 → allowlist 가드의 자연스러운 위치는 이 저장 핸들러.

### M-5. 갱신된 관측 한계 (잔여)
- 보유종목/체결 데이터가 있는 계정에서 테이블 반응형·실시간 위젯 재확인(현 테스트 계정은 빈 paper 상태).
- W-02/W-03 silent-catch의 "실패 시 UI 증발"은 백엔드 강제 중단 없이 미재현(코드 근거로 충분, 해피패스는 정상 렌더 확인).
- Lighthouse 종합·프로덕션 URL 실측·키보드 :focus-visible 실조작 확인.

