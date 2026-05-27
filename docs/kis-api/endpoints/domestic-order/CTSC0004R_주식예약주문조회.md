# CTSC0004R — 주식예약주문조회

> KIS Open API 공식 docs 자동 변환. 시행착오는 [GOTCHAS.md](../../GOTCHAS.md) 참조.

## Metadata

| 항목 | 값 |
|---|---|
| API 명 | 주식예약주문조회 |
| API ID | v1_국내주식-020 |
| 실전 TR_ID | `CTSC0004R` |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | `GET` |
| URL | `/uapi/domestic-stock/v1/trading/order-resv-ccnl` |
| 실전 Domain | `https://openapi.koreainvestment.com:9443` |
| 모의 Domain | 모의투자 미지원 |

## 개요

국내예약주문 처리내역 조회 API 입니다.
실전계좌/모의계좌의 경우, 한 번의 호출에 최대 20건까지 확인 가능하며, 이후의 값은 연속조회를 통해 확인하실 수 있습니다.

## Request / Response

| 구분 | Element | 한글명 | Type | Required | Length | Description |
|---|---|---|---|---|---|---|
| Request Header | `content-type` | 컨텐츠타입 | string | N | 40 | application/json; charset=utf-8 |
|  | `authorization` | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token  일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용)  법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차 |
|  | `appkey` | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
|  | `appsecret` | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appsecret (절대 노출되지 않도록 주의해주세요.) |
|  | `personalseckey` | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
|  | `tr_id` | 거래ID | string | Y | 13 | [실전투자] CTSC0004R : 국내주식예약주문조회 * 모의투자 사용 불가 |
|  | `tr_cont` | 연속 거래 여부 | string | N | 1 | 공백 : 초기 조회 N : 다음 데이터 조회 (output header의 tr_cont가 M일 경우) |
|  | `custtype` | 고객타입 | string | N | 1 | B : 법인  P : 개인 |
|  | `seq_no` | 일련번호 | string | N | 2 | [법인 필수] 001 |
|  | `mac_address` | 맥주소 | string | N | 12 | 법인고객 혹은 개인고객의 Mac address 값 |
|  | `phone_number` | 핸드폰번호 | string | N | 12 | [법인 필수] 제휴사APP을 사용하는 경우 사용자(회원) 핸드폰번호  ex) 01011112222 (하이픈 등 구분값 제거) |
|  | `ip_addr` | 접속 단말 공인 IP | string | N | 12 | [법인 필수] 사용자(회원)의 IP Address |
|  | `gt_uid` | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |
| Request Query Parameter | `RSVN_ORD_ORD_DT` | 예약주문시작일자 | string | Y | 8 |  |
|  | `RSVN_ORD_END_DT` | 예약주문종료일자 | string | Y | 8 |  |
|  | `RSVN_ORD_SEQ` | 예약주문순번 | string | Y | 10 |  |
|  | `TMNL_MDIA_KIND_CD` | 단말매체종류코드 | string | Y | 2 | "00" 입력 |
|  | `CANO` | 종합계좌번호 | string | Y | 8 | 계좌번호 체계(8-2)의 앞 8자리 |
|  | `ACNT_PRDT_CD` | 계좌상품코드 | string | Y | 2 | 계좌번호 체계(8-2)의 뒤 2자리 |
|  | `PRCS_DVSN_CD` | 처리구분코드 | string | Y | 2 | 0: 전체 1: 처리내역 2: 미처리내역 |
|  | `CNCL_YN` | 취소여부 | string | Y | 1 | "Y" 유효한 주문만 조회 |
|  | `PDNO` | 상품번호 | string | Y | 12 | 종목코드(6자리) (공백 입력 시 전체 조회) |
|  | `SLL_BUY_DVSN_CD` | 매도매수구분코드 | string | Y | 2 |  |
|  | `CTX_AREA_FK200` | 연속조회검색조건200 | string | Y | 200 | 다음 페이지 조회시 사용 |
|  | `CTX_AREA_NK200` | 연속조회키200 | string | Y | 200 | 다음 페이지 조회시 사용 |
| Response Header | `content-type` | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
|  | `tr_id` | 거래ID | string | Y | 13 | 요청한 tr_id |
|  | `tr_cont` | 연속 거래 여부 | string | Y | 1 | F or M : 다음 데이터 있음 D or E : 마지막 데이터 |
|  | `gt_uid` | Global UID | string | Y | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |
| Response Body | `rt_cd` | 성공 실패 여부 | string | Y | 1 | 0 : 성공  0 이외의 값 : 실패 |
|  | `msg_cd` | 응답코드 | string | Y | 8 |  |
|  | `msg1` | 응답메세지 | string | Y | 80 |  |
|  | `output` | 응답상세 | array | Y |  |  |
|  | `rsvn_ord_seq` | 예약주문 순번 | string | N | 10 |  |
|  | `rsvn_ord_ord_dt` | 예약주문주문일자 | string | N | 8 |  |
|  | `rsvn_ord_rcit_dt` | 예약주문접수일자 | string | N | 8 |  |
|  | `pdno` | 상품번호 | string | N | 12 |  |
|  | `ord_dvsn_cd` | 주문구분코드 | string | N | 2 |  |
|  | `ord_rsvn_qty` | 주문예약수량 | string | N | 10 |  |
|  | `tot_ccld_qty` | 총체결수량 | string | N | 10 |  |
|  | `cncl_ord_dt` | 취소주문일자 | string | N | 8 |  |
|  | `ord_tmd` | 주문시각 | string | N | 6 |  |
|  | `ctac_tlno` | 연락전화번호 | string | N | 20 |  |
|  | `rjct_rson2` | 거부사유2 | string | N | 200 |  |
|  | `odno` | 주문번호 | string | N | 10 |  |
|  | `rsvn_ord_rcit_tmd` | 예약주문접수시각 | string | N | 6 |  |
|  | `kor_item_shtn_name` | 한글종목단축명 | string | N | 60 |  |
|  | `sll_buy_dvsn_cd` | 매도매수구분코드 | string | N | 2 |  |
|  | `ord_rsvn_unpr` | 주문예약단가 | string | N | 19 |  |
|  | `tot_ccld_amt` | 총체결금액 | string | N | 19 |  |
|  | `loan_dt` | 대출일자 | string | N | 8 |  |
|  | `cncl_rcit_tmd` | 취소접수시각 | string | N | 6 |  |
|  | `prcs_rslt` | 처리결과 | string | N | 60 |  |
|  | `ord_dvsn_name` | 주문구분명 | string | N | 60 |  |
|  | `tmnl_mdia_kind_cd` | 단말매체종류코드 | string | N | 2 |  |
|  | `rsvn_end_dt` | 예약종료일자 | string | N | 8 |  |

## Example

### Request Example (Python)
```
{
	"RSVN_ORD_ORD_DT":"20220520",
	"RSVN_ORD_END_DT":"20220523",
	"RSVN_ORD_SEQ":"",
	"TMNL_MDIA_KIND_CD":"00",
	"CANO":"81019970",
	"ACNT_PRDT_CD":"01",
	
	"PRCS_DVSN_CD":"0",
	"CNCL_YN":"Y",
	"PDNO":"",
	"SLL_BUY_DVSN_CD":"",
	"CTX_AREA_FK200":"",
	"CTX_AREA_NK200":""
}
```

### Response Example
```
{
    "ctx_area_fk200": "20220520!^null!^0!^Y!^!^                                                                                                                                                                                ",
    "ctx_area_nk200": " !^ !^                                                                                                                                                                                                  ",
    "output": [
        {
            "rsvn_ord_seq": "42401",
            "rsvn_ord_ord_dt": "20220523",
            "rsvn_ord_rcit_dt": "20220520",
            "pdno": "005940",
            "ord_dvsn_cd": "01",
            "ord_rsvn_qty": "1",
            "tot_ccld_qty": "0",
            "cncl_ord_dt": "",
            "ord_tmd": "",
            "ctac_tlno": "0",
            "rjct_rson2": "",
            "odno": "",
            "rsvn_ord_rcit_tmd": "165318",
            "kor_item_shtn_name": "NH투자증권",
            "sll_buy_dvsn_cd": "02",
            "ord_rsvn_unpr": "6000",
            "tot_ccld_amt": "0",
            "loan_dt": "",
            "cncl_rcit_tmd": "",
            "prcs_rslt": "미처리",
            "ord_dvsn_name": "현금매수",
            "tmnl_mdia_kind_cd": "31",
            "rsvn_end_dt": "20220523"
        },
        {
            "rsvn_ord_seq": "42405",
            "rsvn_ord_ord_dt": "20220523",
            "rsvn_ord_rcit_dt": "20220520",
            "pdno": "005940",
            "ord_dvsn_cd": "01",
            "ord_rsvn_qty": "1",
            "tot_ccld_qty": "0",
            "cncl_ord_dt": "",
            "ord_tmd": "",
            "ctac_tlno": "0",
            "rjct_rson2": "",
            "odno": "",
            "rsvn_ord_rcit_tmd": "170422",
            "kor_item_shtn_name": "NH투자증권",
            "sll_buy_dvsn_cd": "02",
            "ord_rsvn_unpr": "6000",
            "tot_ccld_amt": "0",
            "loan_dt": "",
            "cncl_rcit_tmd": "",
            "prcs_rslt": "미처리",
            "ord_dvsn_name": "현금매수",
            "tmnl_mdia_kind_cd": "31",
            "rsvn_end_dt": ""
        },
        {
            "rsvn_ord_seq": "42406",
            "rsvn_ord_ord_dt": "20220523",
            "rsvn_ord_rcit_dt": "20220520",
            "pdno": "005940",
            "ord_dvsn_cd": "01",
            "ord_rsvn_qty": "1",
            "tot_ccld_qty": "0",
            "cncl_ord_dt": "",
            "ord_tmd": "",
            "ctac_tlno": "0",
            "rjct_rson2": "",
            "odno": "",
            "rsvn_ord_rcit_tmd": "170453",
            "kor_item_shtn_name": "NH투자증권",
            "sll_buy_dvsn_cd": "02",
            "ord_rsvn_unpr": "6000",
            "tot_ccld_amt": "0",
            "loan_dt": "",
            "cncl_rcit_tmd": "",
            "prcs_rslt": "미처리",
            "ord_dvsn_name": "현금매수",
            "tmnl_mdia_kind_cd": "31",
            "rsvn_end_dt": "20220523"
        }
    ],
    
```


---
## 우리 코드 위치
_(사용 위치 기록)_
