## 주요 변경 — Hotfix: KIS 해외주식 시초가 endpoint 교체 + prev_close fallback

### 🐞 사용자 발견 사건 (2026-05-28 KST 01:19)

증상: v0.9.6의 universe fix까지 적용 후 trader가 6 종목 모두 정상 평가
(skip_no_data 0건!) — 그러나 모두:
```
skip_no_open_price - "catch-up: 당일 시가 조회 실패"
```
catch-up 매수 6/6 skip → 매수 0건.

### 원인 — KIS `HHDFS00000300` 응답에 open 필드 자체 없음

`broker._open_overseas`가 호출한 KIS endpoint 응답 분석 (사용자 PC 실측):
```
HHDFS00000300 output (11 fields):
  [OK]    last:  311.00   ← 현재가
  [OK]    base:  308.33   ← 전일종가
  [OK]    tvol, pvol, rate, diff ...
  [없음]  open                ← 시초가 X
  [없음]  high, low           ← 고가/저가 X
```

KIS docs 확인: `HHDFS00000300`(해외주식 현재체결가)은 의도적으로 OHLC가
아닌 last+base만 제공. 모의·실전 모두 같은 결함.

### Fix — `HHDFS76200200` (해외주식 현재가상세)로 교체

KIS API docs 비교:

| TR_ID | 명 | 모의 spec | output 필드 |
|---|---|---|---|
| HHDFS00000300 | 현재체결가 | 모의 지원 | 11개 (open 없음) |
| **HHDFS76200200** | **현재가상세** | doc상 "모의 미지원" | **41개 (open·high·low 포함)** |

실측: KIS 시세는 모든 사용자가 실전 도메인 호출 (`self.quote_base = _REAL`).
모의 appkey + 실전 도메인 조합으로 **HHDFS76200200 정상 동작 확인** (rt_cd: 0, open: 308.44).

분봉(`HHDFS76950200`)도 대안 검토 — NREC=400 호출해도 마지막 ~120봉만 받아
미장 4시간+ 진행 시 09:30 EDT 첫 분봉(=시초가)에 도달 불가. 채택 안 함.

### PR-1 정당 fallback 추가

trader catch-up branch: `open_price <= 0`이면 `prev_close × (1 + buy_tolerance_pct%)`
보수적 매수가로 fallback. 휴장일·KIS 통신 오류 등 진짜 한계 시에도 사용자
매수 의지 존중. 어제 종가에서 slippage 비용만큼 비싸게 사는 최악의 보수적 가격.

이전: silent skip → 매수 0건 + 사용자 알 길 없음 (PR-4 위반)
변경: prev_close fallback + log 명시 + 정상 발주

### 내부 변경

**[localapp/kis_broker.py](localapp/kis_broker.py)** `_open_overseas`:
- TR_ID HHDFS00000300 → HHDFS76200200
- path `/quotations/price` → `/quotations/price-detail`
- output.get("open") 단순 조회 (3-key fallback 제거 — overthinking 해소)

**[localapp/trader.py](localapp/trader.py)** catch-up 분기:
- `open_price <= 0` 시 skip 대신 `ref_price` (prev_close 기반) fallback
- log.info으로 사용자에게 명시 ("prev_close 기반 발주")

**[localapp/__init__.py](localapp/__init__.py)**:
- 버전 0.9.6-beta → 0.9.7-beta
