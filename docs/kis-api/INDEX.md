# KIS API Endpoint Index

전체 endpoint 한 줄 색인. **작업 전 `grep -i <키워드> INDEX.md`로 후보 찾기.**
상세는 `endpoints/{TR_ID}_*.md` 파일 참조.

## 해외주식 — 기본시세 ([raw xlsx](raw/해외주식_기본시세.xlsx))

| TR_ID | 명 | 용도 | 모의 | URL |
|---|---|---|---|---|
| [`HHDFS76200200`](endpoints/HHDFS76200200_해외주식-현재가상세.md) | **해외주식 현재가상세** | ⭐ **OHLC + 시초가 + 52주·PER·시가총액** (41 fields) | ✓ 실측 | `/quotations/price-detail` |
| [`HHDFS76200100`](endpoints/HHDFS76200100_해외주식-현재가-호가.md) | 해외주식 현재가 호가 | 호가창 (매수/매도 잔량) | doc 미지원 | `/quotations/inquire-asking-price-exp-ccn` |
| [`HHDFS00000300`](endpoints/HHDFS00000300_해외주식-현재체결가.md) | 해외주식 현재체결가 | **last + base만** (OHLC ✗ — GOTCHAS 참조) | ✓ | `/quotations/price` |
| [`HHDFS76200300`](endpoints/HHDFS76200300_해외주식-체결추이.md) | 해외주식 체결추이 | 체결 streaming | doc 미지원 | `/quotations/inquire-ccnl` |
| [`HHDFS76950200`](endpoints/HHDFS76950200_해외주식분봉조회.md) | **해외주식분봉조회** | N분봉 OHLC (NREC 한도 ~120봉) | ✓ 실측 | `/quotations/inquire-time-itemchartprice` |
| [`FHKST03030200`](endpoints/FHKST03030200_해외지수분봉조회.md) | 해외지수분봉조회 | 지수(S&P500 등) 분봉 | doc 미지원 | `/quotations/inquire-time-indexchartprice` |
| [`HHDFS76240000`](endpoints/HHDFS76240000_해외주식-기간별시세.md) | 해외주식 기간별시세 | 일·주·월 OHLC | ✓ | `/quotations/dailyprice` |
| [`FHKST03030100`](endpoints/FHKST03030100_해외주식-종목-지수-환율기간별시세-일-주-월-년.md) | 기간별 종목·지수·환율 시세 | 일/주/월/년 차트 | ⚠ **실전 전용** | `/quotations/inquire-daily-chartprice` |
| [`HHDFS76410000`](endpoints/HHDFS76410000_해외주식조건검색.md) | 해외주식 조건검색 | screener 유사 | ✓ | `/quotations/inquire-search` |
| [`CTOS5011R`](endpoints/CTOS5011R_해외결제일자조회.md) | 해외결제일자조회 | 결제일 calendar | doc 미지원 | `/quotations/countries-holiday` |
| [`CTPF1702R`](endpoints/CTPF1702R_해외주식-상품기본정보.md) | 해외주식 상품기본정보 | 종목 메타 (티커·종목명) | doc 미지원 | `/quotations/search-info` |
| [`HHDFS76370000`](endpoints/HHDFS76370000_해외주식-업종별시세.md) | 해외주식 업종별시세 | 섹터별 종목 | doc 미지원 | `/quotations/industry-price` |
| [`HHDFS76370100`](endpoints/HHDFS76370100_해외주식-업종별코드조회.md) | 해외주식 업종별코드 | 섹터 code list | doc 미지원 | `/quotations/industry-theme` |
| [`HHDFS76220000`](endpoints/HHDFS76220000_해외주식-복수종목-시세조회.md) | 해외주식 복수종목 시세조회 | 다종목 batch | doc 미지원 | `/quotations/multprice` |

## 국내주식 (TBD — docs 받으면 endpoints/ 추가)

| TR_ID | 명 | 용도 | 모의 | URL |
|---|---|---|---|---|
| `FHKST01010100` | 국내주식 현재가 | OHLC | ✓ | `/uapi/domestic-stock/v1/quotations/inquire-price` |

_(국내 docs 추가 요청)_

---

## 빠른 사용 가이드

**시초가 받기**: 미국 → `HHDFS76200200` (모의·실전 둘 다 OK, 실측). KR → `FHKST01010100`의 `stck_oprc`.
**현재가**: `HHDFS00000300` (해외) / `FHKST01010100` (국내).
**일별 OHLC**: 미국 → `HHDFS76240000`. (실전만 `FHKST03030100`.)
**분봉**: `HHDFS76950200` — NREC 한도 ~120봉 (장중 시초가 도달 불가, GOTCHAS 참조).

## 도메인 routing

| 용도 | 모의 사용자 | 실전 사용자 |
|---|---|---|
| 주문·계좌 (`self.base`) | `openapivts.koreainvestment.com:29443` | `openapi.koreainvestment.com:9443` |
| **시세 (`self.quote_base`)** | **`openapi.koreainvestment.com:9443`** ← 항상 실전 | `openapi.koreainvestment.com:9443` |

⚠ doc상 "모의 미지원" 표시여도 quote_base가 실전 도메인이라 모의 appkey + 실전 도메인 조합으로 동작 가능한 경우 있음 (`HHDFS76200200`, `HHDFS76950200` 등 — 실측 확인). 일부는 거부 (`FHKST03030100` 등).

새 endpoint 사용 전 GOTCHAS.md 한 번 훑기.
