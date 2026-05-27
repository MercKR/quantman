## 주요 변경 — 본질 fix 묶음 (catch-up 사건의 보조 결함 3건 + KRX 리뷰 발견 1건)

### 🐞 미장 catch-up 사건의 잔존 결함

v0.9.7~v0.9.11 cycle을 통해 미장 매수 4건 정상 체결까지 도달했으나, 사용자
`orders.jsonl`엔 fill 이벤트 0건, `pending_orders.json` stale, `n_bought=0` 표시
+ `foreign_eval_krw` 실 보유 대비 ~5.4배 부풀려진 값. 본 release가 본질 fix.

### Fix 1 — 해외 체결통보 `H0GSCNI0` 별도 구독 (본질)

**근본 원인**: v0.9.11까지 `KisOrderWebSocket`이 `H0STCNI0/H0STCNI9` (국내)만 구독.
해외 매수 fill 이벤트(`H0GSCNI0/H0GSCNI9`)를 받지 못해 `_apply_fill` 미호출 →
orders.jsonl + ledger + pending 모두 갱신 안 됨.

**변경**:
- [localapp/kis_order_websocket.py](localapp/kis_order_websocket.py)
  - `EXEC_FIELDS_DOMESTIC` (26 fields) + `EXEC_FIELDS_OVERSEAS` (25 fields) 분리
  - `_decode_us_price(packed) → float` — 미국 4자리 packed 단가 정규화 ('001480100' → 148.01)
  - `KisOrderWebSocket.__init__(market="KR"|"US")` 파라미터 — 시장별 tr_id·fields·decode 분기
  - `parse_exec_payload(plain, fields)` — fields 인자 받음
- [localapp/intraday_loop.py](localapp/intraday_loop.py)
  - `KisOrderWebSocket(broker, hts_id, on_exec, market=market)` — 시장 인자 전달

**검증**:
- AST OK, import OK
- `_decode_us_price('001480100')` → 148.01 (KIS spec AAPL example 일치)
- `_decode_us_price('004967700')` → 496.77 (AMD-like 정상)

다음 미장(5/29 22:30) catch-up·정규 cycle에서 매수 fill 이벤트가 실시간 수신되어
orders.jsonl·pending·n_bought 모두 정상 갱신 예상.

### Fix 2 — `foreign_eval_krw` 직접 계산 (본질)

**근본 원인**: KIS `inquire-present-balance` 응답의 `output3.frcr_evlu_tota` 필드가
실측 ~5.4배 부풀려진 값 반환. KIS docs description 부재 — 필드 의미 모호.

**변경**: [localapp/kis_broker.py:286-329](localapp/kis_broker.py) `overseas_snapshot`
- 옛: `foreign_eval_krw = float(out3.get("frcr_evlu_tota", 0) or 0)`
- 새: `foreign_eval_krw = (usd_cash + Σ qty·eval_price) × fx` (직접 계산)

**검증** (사용자 PC 실측):
- positions $39,421.17 × fx 1,501.60 = **₩59,194,829** (정확)
- 이전 KIS 응답 ₩319,541,151 (5.4배 부풀려짐)

### Fix 3 — catch-up kind 매칭 (KRX 리뷰 발견 2, PR-3)

**근본 원인**: `_last_of(entries, "KRX", "cycle")`이 `catchup_cycle` 미매칭 →
사용자가 catch-up 후 재부팅 시 또 catch-up 실행 (cycle 자원 중복). 자금 안전엔
L-01 intent journal idempotency가 차단했으나 KIS API 호출 낭비.

**변경**: [localapp/catchup.py](localapp/catchup.py)
- `_last_of`이 kind를 tuple로 받음 (str도 backward compat)
- `_last_of(entries, "KRX", ("cycle", "catchup_cycle"))` — 둘 다 매칭
- US 분기도 동일

### Fix 4 — KRX 리뷰 영향 없음 확정

KRX 자동매매 코드 리뷰 결과 (subagent):
- universe 자동 등록 ✓ (sync_client.py 이미 적용)
- chunked + zstd ✓ (KRX/US 공통)
- 시간 가드 제거 ✓ (KRX 정규장 영향 0)
- 휴장일·발주 endpoint·미체결 cancel ✓

KRX 모의 시초가 (PR-1) — 실측 우선. 코드 변경 보류.

### 4원칙 자가검토

- **근본 원인**: ✓ H0GSCNI0 별도 구독·직접 환산·kind tuple — 모두 *증상 봉합 아님*.
- **Over-eng 금지**: ✓ 분리된 `EXEC_FIELDS_*`·`_decode_us_price`는 KIS spec 차이
  반영 필수. 미사용 옵션 추가 0.
- **Overthinking 금지**: ✓ 한 클래스 + `market` 파라미터 (두 인스턴스 spawn은
  intraday_loop에서 시장 분기 활용). multi-subscribe 같은 복잡 대안 회피.
- **검증**: AST·import·unit test (decode_us_price) 통과. 실 fill은 다음 미장
  catch-up에서 실측.

### 내부 변경

**[localapp/kis_order_websocket.py](localapp/kis_order_websocket.py)**
- `EXEC_FIELDS` → `EXEC_FIELDS_DOMESTIC` (rename).
- `EXEC_FIELDS_OVERSEAS` 추가 (25 fields).
- `_decode_us_price` 함수 추가.
- `parse_exec_payload(plain, fields)` — fields 인자 추가.
- `KisOrderWebSocket.__init__(market="KR")` — 파라미터 추가, tr_id/fields/decode 분기.
- `_handle_exec_message` — tr_id == self._tr_id 매칭, CNTG_UNPR decode.

**[localapp/intraday_loop.py](localapp/intraday_loop.py)**
- `KisOrderWebSocket(market=market)` 인자 전달.

**[localapp/kis_broker.py](localapp/kis_broker.py)**
- `overseas_snapshot` — `frcr_evlu_tota` 제거, 직접 계산으로 변경.

**[localapp/catchup.py](localapp/catchup.py)**
- `_last_of`이 kind tuple 받음.
- KRX·US cycle 분기에서 `("cycle", "catchup_cycle")` 매칭.

**[localapp/__init__.py](localapp/__init__.py)**
- 버전 0.9.11-beta → 0.9.12-beta

**[docs/kis-api/GOTCHAS.md](../docs/kis-api/GOTCHAS.md)**
- H0GSCNI0 별도 구독 entry 추가.
- frcr_evlu_tota mismatch entry 추가.
