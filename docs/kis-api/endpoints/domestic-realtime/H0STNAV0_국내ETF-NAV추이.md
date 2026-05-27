# H0STNAV0 — 국내ETF NAV추이

> KIS Open API 공식 docs 자동 변환. 시행착오는 [GOTCHAS.md](../../GOTCHAS.md) 참조.

## Metadata

| 항목 | 값 |
|---|---|
| API 명 | 국내ETF NAV추이 |
| API ID | 실시간-051 |
| 실전 TR_ID | `H0STNAV0` |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | `POST` |
| URL | `/tryitout/H0STNAV0` |
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

## Request / Response

| 구분 | Element | 한글명 | Type | Required | Length | Description |
|---|---|---|---|---|---|---|
| Request Header | `approval_key` | 웹소켓 접속키 | string | Y | 36 | 실시간 (웹소켓) 접속키 발급 API(/oauth2/Approval)를 사용하여 발급받은 웹소켓 접속키 |
|  | `custtype` | 고객 타입 | string | Y | 1 | B : 법인 / P : 개인 |
|  | `tr_type` | 등록/해제 | string | Y | 1 | 1: 등록, 2:해제 |
|  | `content-type` | 컨텐츠타입 | string | Y | 20 | utf-8 |
| Request Body | `tr_id` | 거래ID | string | Y | 2 | H0STNAV0 |
|  | `tr_key` | 구분값 | string | Y | 12 | 종목코드 (ex. 005930 삼성전자) |
| Response Body | `MKSC_SHRN_ISCD` | 유가증권단축종목코드 | string | Y | 9 |  |
|  | `NAV` | NAV | string | Y | 8 |  |
|  | `NAV_PRDY_VRSS_SIGN` | NAV전일대비부호 | string | Y | 1 |  |
|  | `NAV_PRDY_VRSS` | NAV전일대비 | string | Y | 8 |  |
|  | `NAV_PRDY_CTRT` | NAV전일대비율 | string | Y | 8 |  |
|  | `OPRC_NAV` | NAV시가 | string | Y | 8 |  |
|  | `HPRC_NAV` | NAV고가 | string | Y | 8 |  |
|  | `LPRC_NAV` | NAV저가 | string | Y | 8 |  |

## Example

### Request Example (Python)
```
{
         "header":
         {
                  "approval_key": "35xxxxxa-bxxa-4xxb-87xxx-f56xxxxxxxxxx",
                  "custtype":"P",
                  "tr_type":"1",
                  "content-type":"utf-8"
         },
         "body":
         {
                  "input":
                  {
                           "tr_id":"H0STNAV0",
                           "tr_key":"069500"
                  }
         }
}
```

### Response Example
```
# 연결 확인
{
    "header": {
        "tr_id": "H0STNAV0", 
        "tr_key": "069500", 
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
0|H0STNAV0|001|069500^37235.46^5^-381.26^-1.01^37646.25^37646.25^37202.10
```


---
## 우리 코드 위치
_(사용 위치 기록)_
