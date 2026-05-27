# H0EWASP0 — ELW 실시간호가

> KIS Open API 공식 docs 자동 변환. 시행착오는 [GOTCHAS.md](../../GOTCHAS.md) 참조.

## Metadata

| 항목 | 값 |
|---|---|
| API 명 | ELW 실시간호가 |
| API ID | 실시간-062 |
| 실전 TR_ID | `H0EWASP0` |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | `POST` |
| URL | `/tryitout/H0EWASP0` |
| 실전 Domain | `ws://ops.koreainvestment.com:21000` |
| 모의 Domain | 모의투자 미지원 |

## 개요

ELW 실시간호가 API입니다.

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
|  | `tr_type` | 등록/해제 | string | Y | 1 | 1: 등록, 2:해제 |
|  | `content-type` | 컨텐츠타입 | string | Y | 20 | utf-8 |
| Request Body | `tr_id` | 거래ID | string | Y | 2 | H0EWASP0 |
|  | `tr_key` | 구분값 | string | Y | 12 | ELW 종목코드(ex. 57LA24) |
| Response Body | `MKSC_SHRN_ISCD` | 유가증권단축종목코드 | string | Y | 9 |  |
|  | `BSOP_HOUR` | 영업시간 | string | Y | 6 |  |
|  | `HOUR_CLS_CODE` | 시간구분코드 | string | Y | 1 |  |
|  | `ASKP1` | 매도호가1 | string | Y | 1 |  |
|  | `ASKP2` | 매도호가2 | string | Y | 1 |  |
|  | `ASKP3` | 매도호가3 | string | Y | 1 |  |
|  | `ASKP4` | 매도호가4 | string | Y | 1 |  |
|  | `ASKP5` | 매도호가5 | string | Y | 1 |  |
|  | `ASKP6` | 매도호가6 | string | Y | 1 |  |
|  | `ASKP7` | 매도호가7 | string | Y | 1 |  |
|  | `ASKP8` | 매도호가8 | string | Y | 1 |  |
|  | `ASKP9` | 매도호가9 | string | Y | 1 |  |
|  | `ASKP10` | 매도호가10 | string | Y | 1 |  |
|  | `BIDP1` | 매수호가1 | string | Y | 1 |  |
|  | `BIDP2` | 매수호가2 | string | Y | 1 |  |
|  | `BIDP3` | 매수호가3 | string | Y | 1 |  |
|  | `BIDP4` | 매수호가4 | string | Y | 1 |  |
|  | `BIDP5` | 매수호가5 | string | Y | 1 |  |
|  | `BIDP6` | 매수호가6 | string | Y | 1 |  |
|  | `BIDP7` | 매수호가7 | string | Y | 1 |  |
|  | `BIDP8` | 매수호가8 | string | Y | 1 |  |
|  | `BIDP9` | 매수호가9 | string | Y | 1 |  |
|  | `BIDP10` | 매수호가10 | string | Y | 1 |  |
|  | `ASKP_RSQN1` | 매도호가잔량1 | string | Y | 1 |  |
|  | `ASKP_RSQN2` | 매도호가잔량2 | string | Y | 1 |  |
|  | `ASKP_RSQN3` | 매도호가잔량3 | string | Y | 1 |  |
|  | `ASKP_RSQN4` | 매도호가잔량4 | string | Y | 1 |  |
|  | `ASKP_RSQN5` | 매도호가잔량5 | string | Y | 1 |  |
|  | `ASKP_RSQN6` | 매도호가잔량6 | string | Y | 1 |  |
|  | `ASKP_RSQN7` | 매도호가잔량7 | string | Y | 1 |  |
|  | `ASKP_RSQN8` | 매도호가잔량8 | string | Y | 1 |  |
|  | `ASKP_RSQN9` | 매도호가잔량9 | string | Y | 1 |  |
|  | `ASKP_RSQN10` | 매도호가잔량10 | string | Y | 1 |  |
|  | `BIDP_RSQN1` | 매수호가잔량1 | string | Y | 1 |  |
|  | `BIDP_RSQN2` | 매수호가잔량2 | string | Y | 1 |  |
|  | `BIDP_RSQN3` | 매수호가잔량3 | string | Y | 1 |  |
|  | `BIDP_RSQN4` | 매수호가잔량4 | string | Y | 1 |  |
|  | `BIDP_RSQN5` | 매수호가잔량5 | string | Y | 1 |  |
|  | `BIDP_RSQN6` | 매수호가잔량6 | string | Y | 1 |  |
|  | `BIDP_RSQN7` | 매수호가잔량7 | string | Y | 1 |  |
|  | `BIDP_RSQN8` | 매수호가잔량8 | string | Y | 1 |  |
|  | `BIDP_RSQN9` | 매수호가잔량9 | string | Y | 1 |  |
|  | `BIDP_RSQN10` | 매수호가잔량10 | string | Y | 1 |  |
|  | `TOTAL_ASKP_RSQN` | 총매도호가잔량 | string | Y | 1 |  |
|  | `TOTAL_BIDP_RSQN` | 총매수호가잔량 | string | Y | 1 |  |
|  | `ANTC_CNPR` | 예상체결가 | string | Y | 1 |  |
|  | `ANTC_CNQN` | 예상체결량 | string | Y | 1 |  |
|  | `ANTC_CNTG_VRSS_SIGN` | 예상체결대비부호 | string | Y | 1 |  |
|  | `ANTC_CNTG_VRSS` | 예상체결대비 | string | Y | 1 |  |
|  | `ANTC_CNTG_PRDY_CTRT` | 예상체결전일대비율 | string | Y | 1 |  |
|  | `LP_ASKP_RSQN1` | LP매도호가잔량1 | string | Y | 1 |  |
|  | `LP_ASKP_RSQN2` | LP매도호가잔량2 | string | Y | 1 |  |
|  | `LP_ASKP_RSQN3` | LP매도호가잔량3 | string | Y | 1 |  |
|  | `LP_BIDP_RSQN4` | LP매수호가잔량4 | string | Y | 1 |  |
|  | `LP_ASKP_RSQN4` | LP매도호가잔량4 | string | Y | 1 |  |
|  | `LP_BIDP_RSQN5` | LP매수호가잔량5 | string | Y | 1 |  |
|  | `LP_ASKP_RSQN5` | LP매도호가잔량5 | string | Y | 1 |  |
|  | `LP_BIDP_RSQN6` | LP매수호가잔량6 | string | Y | 1 |  |
|  | `LP_ASKP_RSQN6` | LP매도호가잔량6 | string | Y | 1 |  |
|  | `LP_BIDP_RSQN7` | LP매수호가잔량7 | string | Y | 1 |  |
|  | `LP_ASKP_RSQN7` | LP매도호가잔량7 | string | Y | 1 |  |
|  | `LP_ASKP_RSQN8` | LP매도호가잔량8 | string | Y | 1 |  |
|  | `LP_BIDP_RSQN8` | LP매수호가잔량8 | string | Y | 1 |  |
|  | `LP_ASKP_RSQN9` | LP매도호가잔량9 | string | Y | 1 |  |
|  | `LP_BIDP_RSQN9` | LP매수호가잔량9 | string | Y | 1 |  |
|  | `LP_ASKP_RSQN10` | LP매도호가잔량10 | string | Y | 1 |  |
|  | `LP_BIDP_RSQN10` | LP매수호가잔량10 | string | Y | 1 |  |
|  | `LP_BIDP_RSQN1` | LP매수호가잔량1 | string | Y | 1 |  |
|  | `LP_TOTAL_ASKP_RSQN` | LP총매도호가잔량 | string | Y | 1 |  |
|  | `LP_BIDP_RSQN2` | LP매수호가잔량2 | string | Y | 1 |  |
|  | `LP_TOTAL_BIDP_RSQN` | LP총매수호가잔량 | string | Y | 1 |  |
|  | `LP_BIDP_RSQN3` | LP매수호가잔량3 | string | Y | 1 |  |
|  | `ANTC_VOL` | 예상거래량 | string | Y | 1 |  |

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
                           "tr_id":"H0EWASP0",
                           "tr_key":"57JN53"
                  }
         }
}
```

### Response Example
```
# 연결 확인
{
    "header": {
        "tr_id": "H0EWASP0", 
        "tr_key": "57JN53", 
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
0|H0EWASP0|001|57JN53^090333^0^270^275^280^285^290^295^300^305^310
^315^265^260^255^250^245^240^235^230^225^220^132730^144770^53560^139510^104910^16386
0^111580^41530^66600^41040^119950^176460^142150^218620^148250^160210^154250^141660^1
40270^160640^1000090^1562460^0^0^3^0^0.00^0^0^0^0^0^0^0^0^0^0^0^0^0^0^0^0^0^0^0^0^0^
0^0
```


---
## 우리 코드 위치
_(사용 위치 기록)_
