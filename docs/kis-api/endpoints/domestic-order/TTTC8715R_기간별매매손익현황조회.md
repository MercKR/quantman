# TTTC8715R — 기간별매매손익현황조회

> KIS Open API 공식 docs 자동 변환. 시행착오는 [GOTCHAS.md](../../GOTCHAS.md) 참조.

## Metadata

| 항목 | 값 |
|---|---|
| API 명 | 기간별매매손익현황조회 |
| API ID | v1_국내주식-060 |
| 실전 TR_ID | `TTTC8715R` |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | `GET` |
| URL | `/uapi/domestic-stock/v1/trading/inquire-period-trade-profit` |
| 실전 Domain | `https://openapi.koreainvestment.com:9443` |
| 모의 Domain | 모의투자 미지원 |

## 개요

기간별매매손익현황조회 API입니다.
한국투자 HTS(eFriend Plus) &gt; [0856] 기간별 매매손익 화면 에서 "종목별" 클릭 시의 기능을 API로 개발한 사항으로, 해당 화면을 참고하시면 기능을 이해하기 쉽습니다.

## Request / Response

| 구분 | Element | 한글명 | Type | Required | Length | Description |
|---|---|---|---|---|---|---|
| Request Header | `content-type` | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
|  | `authorization` | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token  일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용)  법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차 |
|  | `appkey` | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
|  | `appsecret` | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
|  | `personalseckey` | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
|  | `tr_id` | 거래ID | string | Y | 13 | TTTC8715R |
|  | `tr_cont` | 연속 거래 여부 | string | N | 1 | 공백 : 초기 조회 N : 다음 데이터 조회 (output header의 tr_cont가 M일 경우) |
|  | `custtype` | 고객 타입 | string | Y | 1 | B : 법인  P : 개인 |
|  | `seq_no` | 일련번호 | string | N | 2 | [법인 필수] 001 |
|  | `mac_address` | 맥주소 | string | N | 12 | 법인고객 혹은 개인고객의 Mac address 값 |
|  | `phone_number` | 핸드폰번호 | string | N | 12 | [법인 필수] 제휴사APP을 사용하는 경우 사용자(회원) 핸드폰번호  ex) 01011112222 (하이픈 등 구분값 제거) |
|  | `ip_addr` | 접속 단말 공인 IP | string | N | 12 | [법인 필수] 사용자(회원)의 IP Address |
|  | `gt_uid` | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |
| Request Query Parameter | `CANO` | 종합계좌번호 | string | Y | 8 |  |
|  | `SORT_DVSN` | 정렬구분 | string | Y | 2 | 00: 최근 순, 01: 과거 순, 02: 최근 순 |
|  | `ACNT_PRDT_CD` | 계좌상품코드 | string | Y | 2 |  |
|  | `PDNO` | 상품번호 | string | Y | 12 | ""공란입력 시, 전체 |
|  | `INQR_STRT_DT` | 조회시작일자 | string | Y | 8 |  |
|  | `INQR_END_DT` | 조회종료일자 | string | Y | 8 |  |
|  | `CTX_AREA_NK100` | 연속조회키100 | string | Y | 100 |  |
|  | `CBLC_DVSN` | 잔고구분 | string | Y | 2 | 00: 전체 |
|  | `CTX_AREA_FK100` | 연속조회검색조건100 | string | Y | 100 |  |
| Response Header | `content-type` | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
|  | `tr_id` | 거래ID | string | Y | 13 | 요청한 tr_id |
|  | `tr_cont` | 연속 거래 여부 | string | N | 1 | F or M : 다음 데이터 있음 D or E : 마지막 데이터 |
|  | `gt_uid` | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |
| Response Body | `rt_cd` | 성공 실패 여부 | string | Y | 1 |  |
|  | `msg_cd` | 응답코드 | string | Y | 8 |  |
|  | `msg1` | 응답메세지 | string | Y | 80 |  |
|  | `ctx_area_nk100` | 연속조회키100 | string | Y | 100 |  |
|  | `ctx_area_fk100` | 연속조회검색조건100 | string | Y | 100 |  |
|  | `output1` | 응답상세 | object array | Y |  | array |
|  | `trad_dt` | 매매일자 | string | Y | 8 |  |
|  | `pdno` | 상품번호 | string | Y | 12 | 종목번호(뒤 6자리만 해당) |
|  | `prdt_name` | 상품명 | string | Y | 60 |  |
|  | `trad_dvsn_name` | 매매구분명 | string | Y | 60 |  |
|  | `loan_dt` | 대출일자 | string | Y | 8 |  |
|  | `hldg_qty` | 보유수량 | string | Y | 19 |  |
|  | `pchs_unpr` | 매입단가 | string | Y | 19 |  |
|  | `buy_qty` | 매수수량 | string | Y | 10 |  |
|  | `buy_amt` | 매수금액 | string | Y | 19 |  |
|  | `sll_pric` | 매도가격 | string | Y | 10 |  |
|  | `sll_qty` | 매도수량 | string | Y | 10 |  |
|  | `sll_amt` | 매도금액 | string | Y | 19 |  |
|  | `rlzt_pfls` | 실현손익 | string | Y | 19 |  |
|  | `pfls_rt` | 손익률 | string | Y | 238 |  |
|  | `fee` | 수수료 | string | Y | 19 |  |
|  | `tl_tax` | 제세금 | string | Y | 19 |  |
|  | `loan_int` | 대출이자 | string | Y | 19 |  |
|  | `output2` | 응답상세2 | object | Y |  |  |
|  | `sll_qty_smtl` | 매도수량합계 | string | Y | 19 |  |
|  | `sll_tr_amt_smtl` | 매도거래금액합계 | string | Y | 19 |  |
|  | `sll_fee_smtl` | 매도수수료합계 | string | Y | 19 |  |
|  | `sll_tltx_smtl` | 매도제세금합계 | string | Y | 19 |  |
|  | `sll_excc_amt_smtl` | 매도정산금액합계 | string | Y | 19 |  |
|  | `buyqty_smtl` | 매수수량합계 | string | Y | 8 |  |
|  | `buy_tr_amt_smtl` | 매수거래금액합계 | string | Y | 19 |  |
|  | `buy_fee_smtl` | 매수수수료합계 | string | Y | 19 |  |
|  | `buy_tax_smtl` | 매수제세금합계 | string | Y | 19 |  |
|  | `buy_excc_amt_smtl` | 매수정산금액합계 | string | Y | 19 |  |
|  | `tot_qty` | 총수량 | string | Y | 10 |  |
|  | `tot_tr_amt` | 총거래금액 | string | Y | 19 |  |
|  | `tot_fee` | 총수수료 | string | Y | 19 |  |
|  | `tot_tltx` | 총제세금 | string | Y | 19 |  |
|  | `tot_excc_amt` | 총정산금액 | string | Y | 19 |  |
|  | `tot_rlzt_pfls` | 총실현손익 | string | Y | 19 |  |
|  | `loan_int` | 대출이자 | string | Y | 19 |  |
|  | `tot_pftrt` | 총수익률 | string | Y | 238 |  |

## Example

### Request Example (Python)
```
{
"CANO":"12345678",
"ACNT_PRDT_CD":"01",
"PDNO":"",
"INQR_STRT_DT":"20240216",
"INQR_END_DT":"20240216",
"SORT_DVSN":"02",
"CBLC_DVSN":"00",
"CTX_AREA_FK100":""
"CTX_AREA_FK100":""
}
```

### Response Example
```
{
    "ctx_area_fk100": "                                                                                                    ",
    "ctx_area_nk100": "20240216^00000A000120^300^0^00000000^                                                               ",
    "output1": [
        {
            "trad_dt": "20240216",
            "pdno": "000J2552221D",
            "prdt_name": "SG 17WR",
            "trad_dvsn_name": "현금",
            "loan_dt": "",
            "hldg_qty": "2",
            "pchs_unpr": "135",
            "buy_qty": "2",
            "buy_amt": "271",
            "sll_pric": "0",
            "sll_qty": "0",
            "sll_amt": "0",
            "rlzt_pfls": "0",
            "pfls_rt": "0.00000000",
            "fee": "0",
            "tl_tax": "0",
            "loan_int": "0"
        },
        {
            "trad_dt": "20240216",
            "pdno": "000J00532219",
            "prdt_name": "국동 9WR",
            "trad_dvsn_name": "현금",
            "loan_dt": "",
            "hldg_qty": "10",
            "pchs_unpr": "130",
            "buy_qty": "10",
            "buy_amt": "1300",
            "sll_pric": "0",
            "sll_qty": "0",
            "sll_amt": "0",
            "rlzt_pfls": "0",
            "pfls_rt": "0.00000000",
            "fee": "0",
            "tl_tax": "0",
            "loan_int": "0"
        },
        {
            "trad_dt": "20240216",
            "pdno": "00000Q520057",
            "prdt_name": "미래에셋 인버스 2X 코스닥150 선물 ETN",
            "trad_dvsn_name": "현금",
            "loan_dt": "",
            "hldg_qty": "1",
            "pchs_unpr": "9365",
            "buy_qty": "1",
            "buy_amt": "9365",
            "sll_pric": "0",
            "sll_qty": "0",
            "sll_amt": "0",
            "rlzt_pfls": "0",
            "pfls_rt": "0.00000000",
            "fee": "0",
            "tl_tax": "0",
            "loan_int": "0"
        },
        {
            "trad_dt": "20240216",
            "pdno": "00000A900270",
            "prdt_name": "헝셩그룹",
            "trad_dvsn_name": "현금",
            "loan_dt": "",
            "hldg_qty": "66",
            "pchs_unpr": "322",
            "buy_qty": "66",
            "buy_amt": "21252",
            "sll_pric": "0",
            "sll_qty": "0",
            "sll_amt": "0",
            "rlzt_pfls": "0",
            "pfls_rt": "0.00000000",
            "fee": "0",
            "tl_tax": "0",
            "loan_int": "0"
        },
        {
            "trad_dt": "20240216",
            "pdno": "00000A402340",
            "prdt_name": "SK스퀘어",
            "trad_dvsn_name": "현금",
            "loan_dt": "",
            "hldg_qty": "10",
            "pchs_unpr": "59000",
            "buy_qty": "10",
            "buy_amt": "590000",
            "sll_pric": "0",
            "sll_qty": "0",
            "sll_amt": "0",
            "rlzt_pfls": "0",
            "pfls_rt": "0.000
```


---
## 우리 코드 위치
_(사용 위치 기록)_
