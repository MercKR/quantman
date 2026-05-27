# H0NXMKO0 — 국내주식 장운영정보 (NXT)

> KIS Open API 공식 docs 자동 변환. 시행착오는 [GOTCHAS.md](../../GOTCHAS.md) 참조.

## Metadata

| 항목 | 값 |
|---|---|
| API 명 | 국내주식 장운영정보 (NXT) |
| API ID | 국내주식 장운영정보 (NXT) |
| 실전 TR_ID | `H0NXMKO0` |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | `POST` |
| URL | `/tryitout/H0NXMKO0` |
| 실전 Domain | `ws://ops.koreainvestment.com:21000` |
| 모의 Domain | 모의투자 미지원 |

## 개요


## Request / Response

| 구분 | Element | 한글명 | Type | Required | Length | Description |
|---|---|---|---|---|---|---|
| Request Header | `approval_key` | 웹소켓 접속키 | string | Y | 286 | 실시간 (웹소켓) 접속키 발급 API(/oauth2/Approval)를 사용하여 발급받은 웹소켓 접속키 |
|  | `custtype` | 고객 타입 | string | Y | 1 | B : 법인  P : 개인 |
|  | `tr_type` | 거래타입 | string | Y | 1 | 1 : 등록 2 : 해제 |
|  | `content-type` | 컨텐츠타입 | string | Y | 1 | utf-8 |
| Request Body | `tr_id` | 거래ID | string | Y | 2 | H0NXMKO0 : 국내주식 장운영정보 (NXT) |
|  | `tr_key` | 구분값 | string | Y | 12 | 종목코드 (ex 005930 삼성전자) |
| Response Body | `MKSC_SHRN_ISCD` | 종목코드 | string | Y | 9 |  |
|  | `TRHT_YN` | 거래정지 여부 | string | Y | 1 |  |
|  | `TR_SUSP_REAS_CNTT` | 거래 정지 사유 내용 | string | Y | 100 |  |
|  | `MKOP_CLS_CODE` | 장운영 구분 코드 | string | Y | 3 |  |
|  | `ANTC_MKOP_CLS_CODE` | 예상 장운영 구분 코드 | string | Y | 3 |  |
|  | `MRKT_TRTM_CLS_CODE` | 임의연장구분코드 | string | Y | 1 |  |
|  | `DIVI_APP_CLS_CODE` | 동시호가배분처리구분코드 | string | Y | 2 |  |
|  | `ISCD_STAT_CLS_CODE` | 종목상태구분코드 | string | Y | 2 |  |
|  | `VI_CLS_CODE` | VI적용구분코드 | string | Y | 1 |  |
|  | `OVTM_VI_CLS_CODE` | 시간외단일가VI적용구분코드 | string | Y | 1 |  |
|  | `EXCH_CLS_CODE` | 거래소 구분코드 | string | Y | 1 |  |

## Example


---
## 우리 코드 위치
_(사용 위치 기록)_
