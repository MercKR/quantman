# H0STPGM0 — 국내주식 실시간프로그램매매 (KRX)

> KIS Open API 공식 docs 자동 변환. 시행착오는 [GOTCHAS.md](../../GOTCHAS.md) 참조.

## Metadata

| 항목 | 값 |
|---|---|
| API 명 | 국내주식 실시간프로그램매매 (KRX) |
| API ID | 실시간-048 |
| 실전 TR_ID | `H0STPGM0` |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | `POST` |
| URL | `/tryitout/H0STPGM0` |
| 실전 Domain | `ws://ops.koreainvestment.com:21000` |
| 모의 Domain | 모의투자 미지원 |

## 개요

[참고자료]
실시간시세(웹소켓) 파이썬 샘플코드는 한국투자증권 Github 참고 부탁드립니다.
https://github.com/koreainvestment/open-trading-api/blob/main/websocket/python/ws_domestic_overseas_all.py

실시간시세(웹소켓) API 사용방법에 대한 자세한 설명은 한국투자증권 Wikidocs 참고 부탁드립니다.
https://wikidocs.net/book/7847 (국내주식 업데이트 완료, 추후 해외주식·국내선물옵션 업데이트 예정)

종목코드 마스터파일 파이썬 정제코드는 한국투자증권 Github 참고 부탁드립니다.
https://github.com/koreainvestment/open-trading-api/tree/main/stocks_info

[호출 데이터]
헤더와 바디 값을 합쳐 JSON 형태로 전송합니다.

[응답 데이터]
1. 정상 등록 여부 (JSON)
- JSON["body"]["msg1"] - 정상 응답 시, SUBSCRIBE SUCCESS
- JSON["body"]["output"]["iv"] - 실시간 결과 복호화에 필요한 AES256 IV (Initialize Vector)
- JSON["body"]["output"]["key"] - 실시간 결과 복호화에 필요한 AES256 Key

2. 실시간 결과 응답 ( | 로 구분되는 값)
ex) 0|H0STCNT0|004|005930^123929^73100^5^...
- 암호화 유무 : 0 암호화 되지 않은 데이터 / 1 암호화된 데이터
- TR_ID : 등록한 tr_id (ex. H0STCNT0)
- 데이터 건수 : (ex. 001 인 경우 데이터 건수 1건, 004인 경우 데이터 건수 4건)
- 응답 데이터 : 아래 response 데이터 참조 ( ^로 구분됨)

## Request / Response

| 구분 | Element | 한글명 | Type | Required | Length | Description |
|---|---|---|---|---|---|---|
| Request Header | `approval_key` | 웹소켓 접속키 | string | Y | 36 | 실시간 (웹소켓) 접속키 발급 API(/oauth2/Approval)를 사용하여 발급받은 웹소켓 접속키 |
|  | `custtype` | 고객 타입 | string | Y | 1 | B : 법인 / P : 개인 |
|  | `tr_type` | 등록/해제 | string | Y | 1 | "1: 등록, 2:해제" |
|  | `content-type` | 컨텐츠타입 | string | Y | 20 | utf-8 |
| Request Body | `tr_id` | 거래ID | string | Y | 7 | H0STPGM0 |
|  | `tr_key` | 종목코드 | string | Y | 6 | 종목코드 |
| Response Body | `MKSC_SHRN_ISCD` | 유가증권단축종목코드 | object | Y | 9 | '각 항목사이에는 구분자로 ^ 사용, 모든 데이터타입은 String으로 변환되어 push 처리됨' |
|  | `STCK_CNTG_HOUR` | 주식체결시간 | string | Y | 6 |  |
|  | `SELN_CNQN` | 매도체결량 | string | Y | 1 |  |
|  | `SELN_TR_PBMN` | 매도거래대금 | string | Y | 1 |  |
|  | `SHNU_CNQN` | 매수2체결량 | string | Y | 1 |  |
|  | `SHNU_TR_PBMN` | 매수2거래대금 | string | Y | 1 |  |
|  | `NTBY_CNQN` | 순매수체결량 | string | Y | 1 |  |
|  | `NTBY_TR_PBMN` | 순매수거래대금 | string | Y | 1 |  |
|  | `SELN_RSQN` | 매도호가잔량 | string | Y | 1 |  |
|  | `SHNU_RSQN` | 매수호가잔량 | string | Y | 1 |  |
|  | `WHOL_NTBY_QTY` | 전체순매수호가잔량 | string | Y | 1 |  |

## Example

### Request Example (Python)
```
{
    "header": {
        "approval_key": "35xxxxxa-bxxa-4xxb-87xxx-f56xxxxxxxxxx",
        "custtype": "P",
        "tr_type": "1",
        "content-type": "utf-8"
    },
    "body": {
        "input": {
            "tr_id": "H0STPGM0",
            "tr_key": "005930"
        }
    }
}
```

### Response Example
```
# 연결 확인
{
    "header": {
        "tr_id": "H0STPGM0", 
        "tr_key": "005930", 
        "encrypt": "N"
        }, 
    "body": {
        "rt_cd": "0", 
        "msg_cd": "OPSP0000",
        "msg1": "SUBSCRIBE SUCCESS", 
        "output": {
            "iv": "0123456789abcdef", 
            "key": "abcdefghijklmnopabcdefghijklmnop"}
        }
}

# output
0|H0STPGM0|001|005930^092237^1413444^109159646900^1189408^91931710200^-2240
36^-17227936700^65033^15475^-49558
```


---
## 우리 코드 위치
_(사용 위치 기록)_
