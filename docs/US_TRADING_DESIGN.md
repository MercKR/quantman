# 설계문서 — 미국 종목 정규장 시각 자동매매

상태: **검토 대기 (구현 전)**
범위: **미국(NASDAQ/NYSE/AMEX) 전용, end-to-end** — 스케줄·발주·체결추적·장중손절·잔고·환율 포함
작성: 2026-05-22

---

## 0. 한 줄 요약

지금 시스템은 KRX(09:00~15:30 KST) 단일 시장 + 원화 + 전일종가(EOD) 모델에
완전히 못박혀 있다. AAPL 같은 미국 종목은 정규장이 KST 밤 22:30~익일 05:00(서머)
또는 23:30~06:00(겨울)이라, 종목별 정규장 시각에 맞춰 매매하려면 스케줄러부터
브로커·체결추적·장중손절·잔고·환율까지 여러 계층을 같이 바꿔야 한다.

---

## 1. 배경과 목표

### 사용자 관점 문제
사용자가 미국 종목(예: AAPL)을 자동매매 대상으로 등록하면, 지금은 08:55 KST에
"전일 종가 지정가"로 주문을 던지고 14시간을 방치한다. 미국장은 그 시각 닫혀
있으므로 정상 매매가 아니다. 더 나아가 **해외 체결은 원장에 들어오지도 않고**
(§3), 장중 손절도 작동하지 않는다. 즉 현재 미국 종목 자동매매는 사실상
동작하지 않는 상태다.

### 목표
미국 종목을 **그 종목의 정규장 시각**(DST·휴장일 반영)에 맞춰
매수 사이클·장중 손절·마감 정산까지 KRX와 동일한 수준으로 자동 실행한다.
달러 예수금·환율·미국 호가단위를 정확히 반영한다.

### 범위 결정 (확정)
- **미국 자동선택 유니버스 = S&P500(~500 대형주) 큐레이션.** 풀 유니버스(~6,000)는
  벌크 데이터 소스가 필요해 v2로 분리(§9). S&P500은 기존 yfinance로 감당 가능하고
  대부분의 사용자 수요(대형주)를 커버.

### 비목표 (이번 범위 밖)
- 일본(TSE)·홍콩(SEHK) — 다음 단계. 점심 휴장 처리가 추가로 필요.
- 미국 장전(pre-market)·장후(after-hours)·주간거래(daytime) — 정규장만.
- 미국 풀 유니버스(~6,000) 스크리닝 — v2, 벌크 소스(Stooq+유료 펀더멘털).
- 서버 preview 거래일 경계 재정렬 — 후속 과제(§9). 이번엔 최소 변경.

---

## 2. 시장 정규장 시각 레퍼런스 (KST 환산)

| 시장 | 현지 정규장 | KST 환산 | 주의 |
|---|---|---|---|
| KRX (KOSPI/KOSDAQ) | 09:00–15:30 KST | 09:00–15:30 | 현행 |
| 미국 (NAS/NYSE/AMEX) | 09:30–16:00 ET | **22:30–05:00**(EDT) / **23:30–06:00**(EST) | DST 1h 이동, 익일로 넘어감, 반일장(조기 마감) 존재 |

- **DST**: 미국은 3월 둘째 일요일~11월 첫째 일요일 EDT. 한국은 DST 없음 →
  KST 기준 미국 개장시각이 연 2회 1시간씩 이동한다. **직접 계산 금지** —
  캘린더 라이브러리로 처리(§4.1).
- **반일장**: 추수감사절 다음날·크리스마스 이브 등은 13:00 ET 조기 마감.
  캘린더가 세션별 close를 정확히 줘야 손절 loop 종료·정산 시각이 맞는다.
- **휴장일**: 미국 공휴일은 한국과 다르다. 캘린더로 휴장일 자동 skip.

---

## 3. 현재 상태 갭 분석 (코드 근거)

### 3.1 스케줄 — KRX 시각 고정
`local/localapp/scheduler.py:32-54` — 4개 잡 모두 `Asia/Seoul` 고정 cron:
08:50 loop 시작 / 08:55 매수 사이클 / 15:30 loop 종료 / 15:35 정산.
미국 시각 개념 없음.

### 3.2 체결·미체결 조회가 국내 전용 — **치명적**
`local/localapp/kis_broker.py:332` `_daily_ccld()`는
`domestic-stock/v1/trading/inquire-daily-ccld` 호출. 해외 주문은 이 응답에
없다. 따라서:
- `order_status()` (kis_broker.py:349) → 항상 `"unknown"`
- `pending_orders()` (kis_broker.py:379) → 해외 미체결 누락
- `trader._resolve_pending()` (trader.py:212-265) → 해외 체결을 영원히
  인식 못 하고, 타임아웃 시 국내 취소 endpoint로 잘못 취소 시도.

결과: **해외 매수 체결이 원장(ledger)에 절대 반영되지 않는다.**

### 3.3 잔고 조회가 국내 전용
`kis_broker.py:116` `_balance_raw()`는 `domestic-stock/.../inquire-balance`만
호출. 해외 포지션·달러 예수금이 `account_snapshot`(kis_broker.py:128)에 없다.
사이징 분모(`trader.py:469` `balance["cash"]`)는 원화 현금뿐.

### 3.4 시장 판별이 코드길이 휴리스틱
`kis_broker.py:145` `_detect_market` — 알파벳이면 무조건 `"NAS"`로 가정
(주석에 명시). NYSE/AMEX 종목을 NASDAQ EXCD로 발주 → KIS 거부.

### 3.5 해외 종목 마스터 없음
`local/localapp/kis_master.py:24-25,71` — KOSPI/KOSDAQ `.mst`만 다운로드.
**미국 마스터(nasmst/nysmst/amsmst)가 없어** 종목→거래소 매핑 소스가 로컬에
존재하지 않는다.

### 3.6 통화·틱 불일치
- 사이징: `trader.py:492` `int(cash[KRW] * pct / prev_close[USD])` — 단위 불일치.
- 틱: `qc.round_to_tick` (trader.py:331,360)이 KRX 호가단위 가정. 미국은 $0.01.

### 3.7 장중 손절 WebSocket 국내 전용
`local/localapp/kis_websocket.py:28` `H0STCNT0`(국내 체결가)만 구독.
해외 실시간(`HDFSCNT0` 계열) 미구독 → 미국 종목 익절/손절/트레일링
(`intraday_loop.py`) 전혀 작동 안 함.

### 3.8 서버 preview 타이밍
`server/app/main.py:325-327` — preview는 18:15 KST 생성(KRX 기준).
미국 거래일 경계와 정합 검토 필요(§9, 이번 범위 밖이나 리스크로 명시).

---

## 4. 목표 아키텍처

### 4.1 신규: 시장 캘린더 모듈 — `core/quant_core/market_calendar.py`
- **런타임 의존성 없음** — `exchange_calendars`는 **빌드/개발 시점**에만 사용해
  미국 세션(개장·반일장·휴장, 수년치)을 정적 JSON
  (`core/quant_core/calendars/us_sessions.json`)으로 생성. 런타임은 JSON +
  `zoneinfo`(stdlib)로 ET→KST 변환만 한다.
  - 이유: 로컬앱이 PyInstaller 번들이라 `exchange_calendars`(+CSV 데이터)를
    묶으면 hidden-import/데이터 누락으로 frozen 빌드가 조용히 깨질 위험. 정적
    JSON은 그 위험이 없고 서버·로컬 동작이 동일.
  - DST는 `zoneinfo`(OS tz DB)가 정확히 처리. 까다로운 NYSE 휴장·반일장만
    JSON에 박제. 세션 데이터는 수년치를 미리 생성, 만료 전 재생성(sp500.json과
    같은 주기적 유지 항목).
- 생성기: `core/gen_market_sessions.py` (개발 전용, `exchange_calendars` 사용).
- core에 두는 이유: 서버 preview와 로컬 스케줄러가 **동일 소스**를 공유.
- 공개 API:
  ```python
  def session_kst(market: str, day: date) -> tuple[datetime, datetime] | None
      # 해당 ET 세션일의 (개장, 폐장) KST tz-aware. 휴장이면 None.
  def is_session_open(market: str, now: datetime | None = None) -> bool
  def next_session_kst(market: str, after: datetime) -> tuple[datetime, datetime] | None
  ```
- 검증: DST 경계(여름 EDT 22:30 / 겨울 EST 23:30), 반일장(13:00 ET→KST 03:00),
  휴장일·주말 단위테스트.

### 4.2 신규: 종목→시장 매핑
**소스 결정 (택1, 권장 A):**
- **A. 로컬 해외 마스터 다운로드** — `kis_master.py`에 미국 마스터 추가
  (nasmst/nysmst/amsmst `.cod`). 주문 라우팅 EXCD의 권위 소스. 로컬 자급.
- B. 서버 preview/strategy payload에 거래소 필드 동봉 — 로컬은 읽기만.
  (단, 수동 입력 종목·고아 포지션엔 메타 없을 수 있어 불완전.)

권장: **A**(주문은 로컬 책임이므로 권위 소스도 로컬). 서버 category는 교차검증용.
- `market_of(symbol) -> "KRX"|"NAS"|"NYS"|"AMS"` 인덱스. `_detect_market` 폐기.

**구현 메모 (P2 완료)**
- 서버 `kis_master_cache`는 이미 해외(NAS/NYS/AMS/TSE/HKS) 마스터를 받고 있었음.
  로컬은 runner 견고성 원칙(서버 단절 시 자급)에 따라 **별도로** 미국 마스터를
  받아 `market_index`(localapp)에 캐싱 — 12,301종목 확인.
- **티커 심볼로지 (중요·교차 영향)**: KIS 마스터/주문 PDNO는 **슬래시** 형식
  (`BRK/B`, `BF/B`). yfinance는 대시(`BRK-B`), 위키 S&P500은 점(`BRK.B`).
  `market_index`가 점/대시/슬래시를 정규화해 조회하고 `kis_ticker_of(symbol)`로
  주문용 KIS 티커(슬래시)를 돌려준다. **P3(유니버스 매칭)·P5(주문 PDNO/시세 SYMB)
  에서 이 정규화를 반드시 적용**할 것.

### 4.3 스케줄러 재설계 — `scheduler.py`
- KRX 4-cron 유지.
- **야간 플래너 잡** 추가: 매일 정오(12:00 KST) 1회 실행 →
  `market_calendar.session_kst("US", today/tonight)`로 그날 밤 미국 세션 계산 →
  휴장이면 무동작, 열리면 **one-shot 잡 4개**(`apscheduler DateTrigger`) 등록:
  | 잡 | 시각(KST) | 동작 |
  |---|---|---|
  | US loop 시작 | open − 10m | `intraday_loop.start(market="US")` |
  | US 매수 사이클 | open − 5m | `run_cycle(market="US")` |
  | US loop 종료 | close | `intraday_loop.stop(market="US")` |
  | US 정산 | close + 5m | `run_post_close_settlement(market="US")` |
- DST·휴장은 매일 재계산되므로 22:30↔23:30 이동·휴장 자동 반영.
- KRX 야간(=미국 새벽)과 US 주간이 겹치지 않으므로 loop 단일 인스턴스 재사용 가능.

### 4.4 Trader 시장 단위 배칭 — `trader.py`, `runner.py`
- `run_cycle(market: str = "KRX")`, `run_post_close_settlement(market)`,
  `Trader.cycle(..., market=...)` 파라미터화.
- US 사이클은 **US 종목 전략만** 평가하고 **US 보유분만** 청산:
  - 청산 루프(trader.py:707) — `market_of(pos["symbol"]) == market`만.
  - `_enter_from_preview`(trader.py:507) — 후보를 `market_of`로 필터.
- 통화별 사이징(`_try_buy_one_symbol` trader.py:437):
  - US는 **USD 예수금 / USD 전일종가**, `round_to_tick`은 통화별(미국 $0.01).
  - `account_snapshot`이 통화별 cash를 주도록 확장(§4.5).

### 4.5 브로커 해외 확장 — `kis_broker.py`
- `account_snapshot`: 국내 + **해외 잔고**(`overseas-stock/v1/trading/inquire-balance`)
  + **매수가능금액**(`inquire-psamount`) + **환율** 병합. 반환 스키마(안):
  ```python
  {"balance": {"cash_krw": ..., "cash_usd": ..., "fx_usdkrw": ...,
               "total_eval": ...(KRW 환산)},
   "positions": [{..., "market": "NAS", "currency": "USD"}, ...]}
  ```
- `order_status`/`pending_orders`: 해외 체결(`inquire-ccnl`)·미체결(`inquire-nccs`)
  분기. pending dict의 symbol→`market_of`로 라우팅.
- §3.2 치명적 버그 해결 — 해외 체결이 원장에 정상 반영.

### 4.6 장중 손절 — `kis_websocket.py`, `intraday_loop.py`
- 해외 실시간 구독(`HDFSCNT0`, tr_key = EXCD+티커 예 `DNASAAPL`) 추가,
  매니저 `on_tick`이 해외 PIPE 포맷 파싱.
- `intraday_loop.start(market)` — market별 보유종목만 구독.
- 해외 실시간 시세 신청 필요 여부 KIS 문서 대조(미신청 시 지연시세 fallback 정책 명시).

---

### 4.7 미국 데이터 수집 (S&P500 큐레이션)

현재 한국은 FDR로 전 종목 ~2,800개를 매일 받지만(`data_fetcher.py:265`),
해외는 사용자 등록 종목만 on-demand로 yfinance 1종목씩 0.3초 sleep
(`main.py:192-198`)이라 풀 유니버스 스크리닝 데이터가 없다. yfinance는
종목당 호출이라 ~6,000개엔 부적합(sleep만 30분 + rate-limit). 그래서:

**두 수요를 분리한다.**
- **거래용 전일종가** — 보유·매수대상 소수 종목. 기존 yfinance 증분 캐싱 유지.
- **스크리너용 유니버스** — S&P500 ~500개. yfinance 500 × 0.3초 = 2.5분, 감당 가능.

**유니버스 목록 소스**
- S&P500 구성종목은 분기 단위로만 바뀌므로 **정적 목록 파일**(`sp500.json`:
  ticker·name·exchange)로 유지하고, 위키피디아 등에서 **수동/주기적 갱신**
  (매일 스크랩 금지 — 깨지기 쉬움). 거래소(NAS/NYS) 정확값은 §4.2 KIS 해외
  마스터로 교차확정.
- 이 목록을 `managed_overseas`에 union으로 주입 → `_refresh_global_dataset`가
  S&P500 + 사용자 등록 종목을 함께 fetch.

**수집 주기 분리 (07:30 글로벌 창 부담 최소화)**
- **OHLCV: 매일** (07:30, 기존 fetch_yfinance 증분 — 미국 마감 06:00 이후라 정합).
- **펀더멘털(시총/PER/PBR): 주 1회** (`fetch_fundamentals` data_fetcher.py:577은
  분기 재무라 매일 받을 이유 없음). 일일 창을 가볍게 유지.

**v2 전환점(§9)** — 풀 유니버스로 갈 때 OHLCV는 Stooq 벌크(미국 전 종목 일봉
단일 다운로드, 무료), 펀더멘털은 FMP/EODHD 벌크로 교체. 종목당 호출 폐기.

### 4.8 선택 가능 종목 = 데이터 보유 종목 (미국 일치 제약) — 중요

`_build_symbols_payload`(server/app/routers/backtest.py:33)는 두 소스를 머지한다:
KIS 마스터(`tradable=True`, 선택 가능) ∪ dataset(`has_backtest_data=True`,
데이터 포인트 보유). 마스터에만 있고 dataset에 없는 종목은
`tradable=True, has_backtest_data=False`로 **선택은 되지만 데이터가 없다**
(line 91-104). 이런 종목을 매수대상으로 고르면 자동매매가 조용히 skip한다
(`trader.py:451-457` `skip_no_data` — "전일 종가 없음").

한국은 `_refresh_kr_dataset`가 마스터 전 종목을 매일 fetch해 마스터 ≈ dataset이라
갭이 거의 없다. **미국은 마스터(~6,000) ≫ 데이터(S&P500 ~500)로 갭이 구조적으로
크다.** 그대로 두면 ~5,500개 미국 종목이 "선택되지만 안 사지는" 상태가 된다.

**제약**: 미국은 **`tradable` 노출을 S&P500(데이터 보유분)으로 한정**한다.
`_build_symbols_payload`의 "마스터만 있는 종목" 경로(line 91-104)를 미국 시장엔
적용하지 않는다. KIS 해외 마스터는 **주문 라우팅(EXCD) 내부용으로만** 쓰고
선택 목록은 채우지 않는다. 결과: 사용자가 고를 수 있는 미장 종목 = 자동매매가
실제 데이터를 가진 종목 = **동일 집합**. 조용한 skip 제거. (자동선택 스크리너는
dataset 위에서만 평가하므로 이미 안전 — 위험한 건 수동 선택 경로뿐.)

## 5. KIS 해외 API — 검증 완료 (실제 VTS + 공식 GitHub 대조)

KIS 공식 GitHub(`koreainvestment/open-trading-api`)와 **실제 모의투자(VTS)
응답**으로 대조 확인. 모의는 OVRS_EXCG_CD="NASD"가 미국 전체.

**잔고/현금/환율 — `inquire-present-balance`** (통합, 권장)
- URL `/uapi/overseas-stock/v1/trading/inquire-present-balance`
- TR: `CTRP6504R`(실전) / `VTRP6504R`(모의)
- params: CANO, ACNT_PRDT_CD, WCRC_FRCR_DVSN_CD="02"(외화), NATN_CD="840"(미국),
  TR_MKET_CD="00", INQR_DVSN_CD="00"
- **output2**(통화별): `crcy_cd`, `frcr_dncl_amt_2`(외화예수금=USD현금),
  `frcr_drwg_psbl_amt_1`(출금가능), `frst_bltn_exrt`(환율, USD≈1503)
- **output3**(종합): `tot_asst_amt`(총자산KRW), `frcr_evlu_tota`(외화평가총액),
  `frcr_use_psbl_amt`(외화사용가능), `evlu_amt_smtl`, `tot_evlu_pfls_amt`
- **output1**(보유종목): 현재 0 → 보유 발생 시(P9) 필드 확정.

**매수가능금액(주문 사이징) — `inquire-psamount`**
- URL `/uapi/overseas-stock/v1/trading/inquire-psamount`
- TR: `TTTS3007R` / `VTTS3007R`
- params: CANO, ACNT_PRDT_CD, OVRS_EXCG_CD, OVRS_ORD_UNPR(가격), ITEM_CD(티커)
- output: `exrt`(환율), `frcr_ord_psbl_amt1`/`ord_psbl_frcr_amt`(USD 주문가능금액),
  `max_ord_psbl_qty`/`ovrs_max_ord_psbl_qty`(주문가능수량), `tr_crcy_cd`

**해외 잔고(손익) — `inquire-balance`** TTTS3012R/VTTS3012R
- output2는 손익 요약(`tot_evlu_pfls_amt` 등) — 현금·환율 없음. present-balance 우선.

**체결/미체결 (P5)**
- 체결 `inquire-ccnl` `/uapi/overseas-stock/v1/trading/inquire-ccnl`
  TR `TTTS3035R`/`VTTS3035R`. params 다수(PDNO, ORD_STRT_DT, ORD_END_DT,
  SLL_BUY_DVSN, CCLD_NCCS_DVSN, OVRS_EXCG_CD, ODNO, ...)
- 미체결 `inquire-nccs` `/uapi/overseas-stock/v1/trading/inquire-nccs`
  TR `TTTS3018R`(실전) — 모의 `VTTS3018R` 확인 필요(P5).

**보유종목 inquire-balance output1 필드 (실거래로 확정)**
- `ovrs_pdno`(티커), `ovrs_item_name`(명), `ovrs_cblc_qty`(수량),
  `pchs_avg_pric`(평단), `now_pric2`(현재가), `ord_psbl_qty`(매도가능).

**해외 실시간 시세 WS (P8, 확정)**
- TR `HDFSCNT0`(체결가). tr_key = 지연시세 접두 `BAQ`(나스닥)/`BAY`(뉴욕)/`BAA`(아멕스)
  + KIS 티커. 실시간(D-prefix)은 별도 신청 필요 → 지연 사용.
- 메시지 `^` 구분: field[1]=SYMB(종목코드), field[11]=LAST(현재가).
- **중요(검증으로 발견)**: 해외 시세 WS는 구독은 SUBSCRIBE SUCCESS로 수락되나
  **데이터(tick)는 KIS 해외 실시간 시세 신청(HTS [7781])이 있어야 흐른다.**
  모의계좌·미신청 실계좌에선 tick이 0건. → 결정: WebSocket 방식 유지 +
  **entitlement 감지**(US 보유 중 grace 120초 내 tick 0 → 미신청 판정) +
  **사용자 고지**(웹 설정에 사전 안내 + 런타임 `us_realtime_unavailable` push).
  미신청 시 미국 종목은 장중 실시간 손절 미제공(사이클 청산만).

## 5.1 실거래 검증 로그 (페이퍼/VTS, 미국 정규장 중)

AAPL 1주 라운드트립(매수→체결→보유파싱→매도청산)을 실제 VTS에서 2회 수행,
재정 리스크 0. 검증된 것: 해외 발주(슬래시 PDNO·소수 USD가격), 체결 감지
(overseas ccnl 라우팅), 보유 파싱(output1), 청산. §3.2 치명버그(해외 체결→원장)
end-to-end 해결 입증.

**실거래로만 드러난 버그 2건 (수정 완료)**
1. **통합증거금 사이징** — USD 예수금이 0이어도 KIS 통합증거금(KRW 담보)으로
   미국 주문이 가능. 사이징을 USD 예수금이 아니라 `inquire-psamount`의
   주문가능액(통합증거금 반영)으로 변경. 안 그러면 KRW만 충전한 계좌(한국
   사용자의 일반적 경우)에서 미국 매수가 전부 skip됐음.
   - **제품 결정(완료)**: 통합증거금은 FX 노출이 생기므로 **사용자 설정 옵션**으로
     구현. `UserSettings.us_buying_power_mode`: `"integrated"`(통합증거금, 기본) |
     `"usd_cash"`(USD 예수금 한정, 보수적). 서버 모델·스키마·settings·sync +
     db `_migrate` + 로컬 trader(`_us_bp_mode`, risk_limits로 주입) + 웹 설정 UI.
     dry-run으로 토글 동작 확인(integrated→매수 / usd_cash→예수금0이면 skip).
2. **주문 POST rate-limit 미보호** — 다중 호출 버스트 뒤 매도 POST가
   초당거래제한(EGW00201)으로 실패 → 포지션 방치 위험. `_post_retry` 추가
   (EGW00201에만 재시도 — 처리 전 거부라 중복 발주 없음).
3. **국내 GET rate-limit 미보호** — P9 통합 리허설에서 발견. `_balance_raw`·
   `_price_domestic`·`_daily_ccld`가 재시도 없이 직접 호출돼 사이클 버스트에서
   크래시. 모든 KIS GET(국내·해외·시세)을 `_get_retry`(base 인자 추가)로 통일.

## 5.2 P9 통합 리허설 (cycle 오케스트레이션)

실 VTS 잔고·시세 + 발주 가로채기(DryRunBroker) + 상태 격리(임시 APP_DIR)로
가짜 US/KRX 전략·후보 주입 후 `cycle(market=...)` 검증:
- US 사이클 → MSFT만 발주(61주 @ $422.13, USD 사이징·소수점), 000660 미발주.
- KRX 사이클 → 000660만 발주(55주 @ ₩181,800, KRW 사이징·정수), MSFT 미발주.
- 시장 배칭·통화 사이징·틱 포맷 정확, 통합 equity·kill switch 계좌 단위 동작.
실제 체결→원장 경로는 §5.1 라운드트립으로 별도 실증.

(기존 `kis_broker.py:237-253` 해외 주문 TR_ID 매핑은 검증 후 재사용.)

---

## 6. 변경 파일 요약

| 파일 | 변경 |
|---|---|
| `core/quant_core/market_calendar.py` | **신규** — 시장 캘린더 |
| `core/pyproject.toml` | `exchange_calendars` 의존성 |
| `local/requirements.txt` | `exchange_calendars` |
| `local/localapp/kis_master.py` | 미국 마스터 다운로드·파싱 추가 |
| `local/localapp/scheduler.py` | 야간 플래너 + one-shot 잡 |
| `local/localapp/runner.py` | `market` 파라미터, US 경로 |
| `local/localapp/trader.py` | 시장 필터·통화별 사이징/틱 |
| `local/localapp/kis_broker.py` | 해외 잔고·체결·미체결·환율, `market_of` |
| `local/localapp/kis_websocket.py` | 해외 실시간 구독·파싱 |
| `local/localapp/intraday_loop.py` | `market` 파라미터 |
| `core/quant_core/data/sp500.json` (또는 server) | **신규** — S&P500 구성종목 정적 목록 |
| `core/quant_core/data_fetcher.py` | S&P500 union 주입, 펀더멘털 주 1회 분리 |
| `server/app/main.py` | 펀더멘털 주간 cron 분리(선택), S&P500 시드 |
| `server/app/routers/backtest.py` | §4.8 — 미국 `tradable`을 S&P500로 한정 |

---

## 6.5 진행 재정렬 (구현 중 확정)

구현 중 발견: 스크리너(`server/app/screener.py`)는 `krx_cache.get_all_metrics()`
전용이고 `parse_spec`이 markets를 `KOSPI/KOSDAQ`로만 허용한다. 미국 자동선택은
KRX와 평행한 **미국 metrics 파이프라인 + 스크리너 일반화 + preview 엮기**가
필요해 단순 데이터 시딩보다 훨씬 크다. 그러나 **미국 실행(execution)과
자동선택(screener)은 독립**이며, 원래 요청("정규장 시각 자동매매")의 핵심은 실행이다.

**결정**: 실행(P4~P9)을 먼저 완성. 미국 자동선택 스크리너는 **별도 트랙으로 보류**
(task #7). 수동 선택한 미국 종목은 기존 managed_overseas 흐름으로 OHLCV가 들어와
실행에 막힘이 없다. 단 known caveat: (a) 전략 생성 첫날 밤엔 아직 OHLCV 미수집이면
trader가 skip_no_data로 안전하게 건너뜀(다음 07:30 수집 후 정상). (b) 현재 US 마스터
전 종목이 selectable이라, 데이터 없는 US 종목 선택 가능 — §4.8 제약은 스크리너
트랙에서 함께 처리.

## 7. 단계별 구현 + 검증 게이트

각 단계는 **KIS 모의투자(VTS)에서 실제 동작 검증** 후 다음으로. 시간 의존이라
타입체크·단위테스트만으론 불충분.

1. **토대** — 시장 캘린더 모듈 + 종목→시장 매핑(미국 마스터). 단위테스트로
   DST 경계·반일장·휴장일 검증.
2. **잔고·환율** — `account_snapshot` 해외 확장. VTS로 달러 예수금·환율 조회 확인.
3. **발주·체결추적** — `_submit`·`order_status`·`pending_orders` 해외 분기.
   VTS로 미국 종목 1주 매수→체결→원장반영 확인(§3.2 버그 해결 검증).
4. **스케줄러** — 야간 플래너 + one-shot 잡. 실제 야간 US 세션에서 사이클 발화 확인.
5. **장중 손절** — 해외 WebSocket. 야간에 보유분 손절 트리거 확인.
6. **통합 야간 리허설** — 모의투자로 야간 1사이클 end-to-end.

---

## 8. 리스크

- **시간 의존 검증의 어려움** — 야간 미국장에서만 실제 확인 가능. VTS 데모/시각
  주입 가능한 테스트 훅을 둬 낮에도 로직 검증.
- **KIS 모의투자 해외 지원 범위** — VTS가 해외 일부 TR을 지원 안 할 수 있음.
  미지원 시 실전 소액으로만 검증 가능 → 사용자 승인 필요.
- **환율 변동** — 사이징 시점과 체결 시점 환율 차이. 보수적 buffer 적용.
- **PyInstaller 번들** — `exchange_calendars`가 번들 크기·hidden import 추가.
  빌드 spec 검증 필요.

---

## 9. 후속 과제 (이번 범위 밖, 명시)

- **미국 풀 유니버스(~6,000) 스크리닝** — OHLCV는 Stooq 벌크(무료, 전 종목
  단일 다운로드), 펀더멘털은 FMP/EODHD 벌크로 교체. 종목당 yfinance 호출 폐기.
- 서버 preview 거래일 경계를 시장별로 정렬(미국 후보·리밸런싱 멤버십·전일종가).
- 일본(TSE)·홍콩(SEHK) — 점심 휴장 세션 분리 처리.
- 미국 장전/장후/주간거래.
