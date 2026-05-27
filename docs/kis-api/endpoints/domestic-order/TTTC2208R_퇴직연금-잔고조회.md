# TTTC2208R — 퇴직연금 잔고조회

> KIS Open API 공식 docs 자동 변환. 시행착오는 [GOTCHAS.md](../../GOTCHAS.md) 참조.

## Metadata

| 항목 | 값 |
|---|---|
| API 명 | 퇴직연금 잔고조회 |
| API ID | v1_국내주식-036 |
| 실전 TR_ID | `TTTC2208R` |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | `GET` |
| URL | `/uapi/domestic-stock/v1/trading/pension/inquire-balance` |
| 실전 Domain | `https://openapi.koreainvestment.com:9443` |
| 모의 Domain | 모의투자 미지원 |

## 개요

주식, ETF, ETN만 조회 가능하며 펀드는 조회 불가합니다.

​※ 55번 계좌(DC가입자계좌)의 경우 해당 API 이용이 불가합니다.
KIS Developers API의 경우 HTS ID에 반드시 연결되어있어야만 API 신청 및 앱정보 발급이 가능한 서비스로 개발되어서 실물계좌가 아닌 55번 계좌는 API 이용이 불가능한 점 양해 부탁드립니다.

## Request / Response

| 구분 | Element | 한글명 | Type | Required | Length | Description |
|---|---|---|---|---|---|---|
| Request Header | `content-type` | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
|  | `authorization` | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token  일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용)  법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차 |
|  | `appkey` | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
|  | `appsecret` | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
|  | `personalseckey` | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
|  | `tr_id` | 거래ID | string | Y | 13 | TTTC2208R |
|  | `tr_cont` | 연속 거래 여부 | string | N | 1 | 공백 : 초기 조회 N : 다음 데이터 조회 (output header의 tr_cont가 M일 경우) |
|  | `custtype` | 고객 타입 | string | Y | 1 | B : 법인  P : 개인 |
|  | `seq_no` | 일련번호 | string | N | 2 | [법인 필수] 001 |
|  | `mac_address` | 맥주소 | string | N | 12 | 법인고객 혹은 개인고객의 Mac address 값 |
|  | `phone_number` | 핸드폰번호 | string | N | 12 | [법인 필수] 제휴사APP을 사용하는 경우 사용자(회원) 핸드폰번호  ex) 01011112222 (하이픈 등 구분값 제거) |
|  | `ip_addr` | 접속 단말 공인 IP | string | N | 12 | [법인 필수] 사용자(회원)의 IP Address |
|  | `gt_uid` | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |
| Request Query Parameter | `CANO` | 종합계좌번호 | string | Y | 8 |  |
|  | `ACNT_PRDT_CD` | 계좌상품코드 | string | Y | 2 | 29 |
|  | `ACCA_DVSN_CD` | 적립금구분코드 | string | Y | 2 | 00 |
|  | `INQR_DVSN` | 조회구분 | string | Y | 2 | 00 : 전체 |
|  | `CTX_AREA_FK100` | 연속조회검색조건100 | string | Y | 100 |  |
|  | `CTX_AREA_NK100` | 연속조회키100 | string | Y | 100 |  |
| Response Header | `content-type` | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
|  | `tr_id` | 거래ID | string | Y | 13 | 요청한 tr_id |
|  | `tr_cont` | 연속 거래 여부 | string | N | 1 | F or M : 다음 데이터 있음 D or E : 마지막 데이터 |
|  | `gt_uid` | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |
| Response Body | `rt_cd` | 성공 실패 여부 | string | Y | 1 |  |
|  | `msg_cd` | 응답코드 | string | Y | 8 |  |
|  | `msg1` | 응답메세지 | string | Y | 80 |  |
|  | `output1` | 응답상세 | object array | Y |  | Array |
|  | `cblc_dvsn_name` | 잔고구분명 | string | Y | 60 |  |
|  | `prdt_name` | 상품명 | string | Y | 60 |  |
|  | `pdno` | 상품번호 | string | Y | 12 |  |
|  | `item_dvsn_name` | 종목구분명 | string | Y | 60 |  |
|  | `thdt_buyqty` | 금일매수수량 | string | Y | 10 |  |
|  | `thdt_sll_qty` | 금일매도수량 | string | Y | 10 |  |
|  | `hldg_qty` | 보유수량 | string | Y | 19 |  |
|  | `ord_psbl_qty` | 주문가능수량 | string | Y | 10 |  |
|  | `pchs_avg_pric` | 매입평균가격 | string | Y | 184 |  |
|  | `pchs_amt` | 매입금액 | string | Y | 19 |  |
|  | `prpr` | 현재가 | string | Y | 19 |  |
|  | `evlu_amt` | 평가금액 | string | Y | 19 |  |
|  | `evlu_pfls_amt` | 평가손익금액 | string | Y | 19 |  |
|  | `evlu_erng_rt` | 평가수익율 | string | Y | 238 |  |
|  | `output2` | 응답상세2 | object | Y |  |  |
|  | `dnca_tot_amt` | 예수금총금액 | string | Y | 19 |  |
|  | `nxdy_excc_amt` | 익일정산금액 | string | Y | 19 |  |
|  | `prvs_rcdl_excc_amt` | 가수도정산금액 | string | Y | 19 |  |
|  | `thdt_buy_amt` | 금일매수금액 | string | Y | 19 |  |
|  | `thdt_sll_amt` | 금일매도금액 | string | Y | 19 |  |
|  | `thdt_tlex_amt` | 금일제비용금액 | string | Y | 19 |  |
|  | `scts_evlu_amt` | 유가평가금액 | string | Y | 19 |  |
|  | `tot_evlu_amt` | 총평가금액 | string | Y | 19 |  |

## Example

### Request Example (Python)
```
{
	"CANO":"12345678",
	"ACNT_PRDT_CD":"29",
	"ACCA_DVSN_CD":"00",
	"INQR_DVSN":"00",
	"CTX_AREA_FK100":"",
	"CTX_AREA_NK100":""
}
```

### Response Example
```
{
    "ctx_area_fk100": "12345678^29^00^00^                                                                                  ",
    "ctx_area_nk100": "                                                                                                    ",
    "output1": [
        {
            "cblc_dvsn_name": "사용자",
            "prdt_name": "ACE 미국S&P500",
            "pdno": "360200",
            "item_dvsn_name": "현금",
            "thdt_buyqty": "5",
            "thdt_sll_qty": "0",
            "hldg_qty": "5",
            "ord_psbl_qty": "5",
            "pchs_avg_pric": "13235.0000",
            "pchs_amt": "66175",
            "prpr": "13235",
            "evlu_amt": "66175",
            "evlu_pfls_amt": "0",
            "evlu_erng_rt": "0.00000000"
        }
    ],
    "output2": {
        "dnca_tot_amt": "100000",
        "nxdy_excc_amt": "100000",
        "prvs_rcdl_excc_amt": "33825",
        "thdt_buy_amt": "66175",
        "thdt_sll_amt": "0",
        "thdt_tlex_amt": "0",
        "scts_evlu_amt": "66175",
        "tot_evlu_amt": "100000"
    },
    "rt_cd": "0",
    "msg_cd": "KIOK0510",
    "msg1": "조회가 완료되었습니다                                                           "
}
```


---
## 우리 코드 위치
_(사용 위치 기록)_
