# KIS API GOTCHAS — 실측 발견사항

공식 docs와 다른 동작·알려진 한계·workaround. 작업 전 한 번 훑기.
새 발견 시 **위에 추가** (최신순). 각 entry: 날짜·증상·원인·해결.

---

## 2026-05-28 — `HHDFS00000300` 응답에 OHLC 없음 (open 필드 X)

**증상**: trader catch-up이 `broker.today_open(symbol)` 호출 시 6 종목 모두 0.0 반환 → 매수 0건.

**원인**: 우리 옛 코드(`_open_overseas`)가 `HHDFS00000300` (해외주식 현재체결가) 호출. 실측한 응답 11 fields에 `open` 필드 자체 없음:
```
output: [base, diff, last, ordy, pvol, rate, rsym, sign, tamt, tvol, zdiv]
        ↑ 전일종가 ↑ 현재가 ↑ 거래량
        open / high / low ✗ 모두 미제공 (doc spec상 보장 안 함)
```

**해결**: `HHDFS76200200` (해외주식 현재가상세)로 교체 — 41 fields, open/high/low 모두 정상 제공. [v0.9.7-beta fix](../../local/RELEASE_NOTES_v0.9.7-beta.md).

**우리 코드**: `local/localapp/kis_broker.py::_open_overseas`

---

## 2026-05-28 — `quote_base`는 모든 사용자 실전 도메인 (모의/실전 무관)

**증상**: doc에 "모의 미지원"이라 표시된 시세 endpoint가 모의 사용자도 동작.

**원인**: `KisBroker.__init__`이 `self.quote_base = _REAL` 고정. 시세는 KIS 정책상 모의·실전 사용자 모두 실전 도메인 호출. 즉 모의 appkey + 실전 도메인 조합.

**결과**:
- 일부 시세 endpoint (`HHDFS76200200`·`HHDFS76950200` 등): 모의 appkey도 실전 도메인에서 정상 응답 (rt_cd: 0)
- 일부 (`FHKST03030100` 일별차트): 거부 — "실전투자 도메인은 모의투자 앱키로 호출 불가" (HTTP 500 EGW02004)

**해결**: doc만 보지 말고 실측. INDEX.md "모의" 컬럼은 실측 결과 기준 갱신.

**우리 코드**: `local/localapp/kis_broker.py:95-96`

---

## 2026-05-28 — `HHDFS76950200` 분봉 NREC 한도 ~120봉

**증상**: NREC=400 명시 호출해도 응답 분봉 ~120개. 미장 4시간+ 진행 시 09:30 EDT 시초가 분봉 도달 불가.

**원인**: KIS 분봉 endpoint의 응답 한도는 최근 N개 (실측 ~120봉). NREC param이 상한이 아닌 hint 정도. 시초가 분봉 받으려면 NEXT/KEYB로 페이징 필요 (복잡).

**해결**: 시초가 받기엔 부적합. **`HHDFS76200200` 현재가상세의 output.open이 단일 호출로 시초가 제공** — 그것 사용.

**우리 코드**: 분봉 endpoint는 우리 자동매매에서 미사용. 시초가는 HHDFS76200200으로 대체.

---

## 2026-05-28 — Transfer-Encoding chunked + `requests.r.raw` 충돌

**증상**: 서버 dataset bundle (Railway, `Transfer-Encoding: chunked`) 디코드 시 `zstandard: Unknown frame descriptor`.

**원인**: `requests.get(stream=True).raw`로 chunked response 받으면 chunk header (hex digit + CRLF)가 raw bytes에 섞임. zstd magic (`28 b5 2f fd`) 앞에 hex digit이 끼어 디코드 실패.

**해결**: `r.iter_content(chunk_size=...)`로 chunk를 자동 de-chunk 처리해서 임시파일 거쳐 디코드. [v0.9.5-beta fix](../../local/RELEASE_NOTES_v0.9.5-beta.md).

**우리 코드**: `local/localapp/sync_client.py::fetch_dataset_bundle`

⚠ KIS API 직접 관련 아니나, KIS·외부 API 모두 동일 패턴 위험.

---

## 2026-05-28 — KIS 모의투자는 일부 시세 API에서 일부 필드 누락

**증상**: 같은 endpoint·같은 응답 구조라도 모의 사용자는 일부 필드 빈 값.

**원인**: KIS 모의투자 환경의 시세 데이터 한계. 종가·전일종가·당일거래량은 OK, 시초가·고가·저가는 누락 가능.

**해결**:
- 모의에서 OHLC 받으려면 OHLC 명시 제공하는 endpoint 선택 (`HHDFS76200200`)
- 또는 prev_close 기반 fallback 설계 (PR-1 정당 — KIS 한계)

---

## 작성 가이드

새 entry 추가 시:
1. 위에 (최신순) 추가
2. **날짜** + **증상** (사용자가 본 현상) + **원인** (root cause) + **해결** (어떤 endpoint·코드로 회피)
3. **우리 코드** 섹션 — `file:line` 형식 reference
4. fix가 release에 들어갔으면 [RELEASE_NOTES](../../local/) link
