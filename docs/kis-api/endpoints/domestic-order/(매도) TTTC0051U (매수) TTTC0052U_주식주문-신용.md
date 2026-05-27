# (매도) TTTC0051U (매수) TTTC0052U — 주식주문(신용)

> KIS Open API 공식 docs 자동 변환. 시행착오는 [GOTCHAS.md](../../GOTCHAS.md) 참조.

## Metadata

| 항목 | 값 |
|---|---|
| API 명 | 주식주문(신용) |
| API ID | v1_국내주식-002 |
| 실전 TR_ID | `(매도) TTTC0051U (매수) TTTC0052U` |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | `POST` |
| URL | `/uapi/domestic-stock/v1/trading/order-credit` |
| 실전 Domain | `https://openapi.koreainvestment.com:9443` |
| 모의 Domain | 모의투자 미지원 |

## 개요

국내주식주문(신용) API입니다. 
※ 모의투자는 사용 불가합니다.

※ POST API의 경우 BODY값의 key값들을 대문자로 작성하셔야 합니다.
   (EX. "CANO" : "12345678", "ACNT_PRDT_CD": "01",...)

## Request / Response

| 구분 | Element | 한글명 | Type | Required | Length | Description |
|---|---|---|---|---|---|---|
| Request Header | `content-type` | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
|  | `authorization` | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token  일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용)  법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차 |
|  | `appkey` | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
|  | `appsecret` | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
|  | `personalseckey` | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
|  | `tr_id` | 거래ID | string | Y | 13 | '※ 구TR은 사전고지 없이 막힐 수 있으므로 반드시 신TR로 변경이용 부탁드립니다. [실전투자] 매도 : (구)TTTC0851U → (신)TTTC0051U 매수 : (구)TTTC0852U → (신)TTTC0052U ' |
|  | `tr_cont` | 연속 거래 여부 | string | N | 1 | tr_cont를 이용한 다음조회 불가 API |
|  | `custtype` | 고객 타입 | string | Y | 1 | B : 법인  P : 개인 |
|  | `seq_no` | 일련번호 | string | N | 2 | [법인 필수] 001 |
|  | `mac_address` | 맥주소 | string | N | 12 | 법인고객 혹은 개인고객의 Mac address 값 |
|  | `phone_number` | 핸드폰번호 | string | N | 12 | [법인 필수] 제휴사APP을 사용하는 경우 사용자(회원) 핸드폰번호  ex) 01011112222 (하이픈 등 구분값 제거) |
|  | `ip_addr` | 접속 단말 공인 IP | string | N | 12 | [법인 필수] 사용자(회원)의 IP Address |
|  | `gt_uid` | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |
| Request Body | `CANO` | 종합계좌번호 | string | Y | 8 | 계좌번호 체계(8-2)의 앞 8자리 |
|  | `ACNT_PRDT_CD` | 계좌상품코드 | string | Y | 2 | 계좌번호 체계(8-2)의 뒤 2자리 |
|  | `PDNO` | 상품번호 | string | Y | 5 | 종목코드(6자리) |
|  | `SLL_TYPE` | 매도유형 | string | N | 10 | 공란 입력 |
|  | `CRDT_TYPE` | 신용유형 | string | Y | 2 | [매도] 22 : 유통대주신규, 24 : 자기대주신규, 25 : 자기융자상환, 27 : 유통융자상환 [매수] 21 : 자기융자신규, 23 : 유통융자신규 , 26 : 유통대주상환, 28 : 자기대주상환 |
|  | `LOAN_DT` | 대출일자 | string | Y | 2 | [신용매수]  신규 대출로, 오늘날짜(yyyyMMdd)) 입력   [신용매도]  매도할 종목의 대출일자(yyyyMMdd)) 입력 |
|  | `ORD_DVSN` | 주문구분 | string | Y | 8 | [KRX] 00 : 지정가 01 : 시장가 02 : 조건부지정가 03 : 최유리지정가 04 : 최우선지정가 05 : 장전 시간외 06 : 장후 시간외 07 : 시간외 단일가 11 : IOC지정가 (즉시체결,잔량취소) 12 : FOK지정가 (즉시체결,전량취소) 13 : IOC시장가 (즉시체결,잔량취소) 14 : FOK시장가 (즉시체결,전 |
|  | `ORD_QTY` | 주문수량 | string | Y | 2 |  |
|  | `ORD_UNPR` | 주문단가 | string | Y | 5 | 1주당 가격  * 장전 시간외, 장후 시간외, 시장가의 경우 1주당 가격을 공란으로 비우지 않음 "0"으로 입력 권고 |
|  | `RSVN_ORD_YN` | 예약주문여부 | string | N | 2 | 정규 증권시장이 열리지 않는 시간 (15:10분 ~ 익일 7:30분) 에 주문을 미리 설정 하여 다음 영업일 또는 설정한 기간 동안 아침 동시 호가에 주문하는 것  Y : 예약주문  N : 신용주문 |
|  | `EMGC_ORD_YN` | 비상주문여부 | string | N | 2 |  |
|  | `PGTR_DVSN` | 프로그램매매구분 | string | N | 10 |  |
|  | `MGCO_APTM_ODNO` | 운용사지정주문번호 | string | N | 19 |  |
|  | `LQTY_TR_NGTN_DTL_NO` | 대량거래협상상세번호 | string | N | 1 |  |
|  | `LQTY_TR_AGMT_NO` | 대량거래협정번호 | string | N | 20 |  |
|  | `LQTY_TR_NGTN_ID` | 대량거래협상자Id | string | N | 19 |  |
|  | `LP_ORD_YN` | LP주문여부 | string | N | 3 |  |
|  | `MDIA_ODNO` | 매체주문번호 | string | N | 10 |  |
|  | `ORD_SVR_DVSN_CD` | 주문서버구분코드 | string | N | 19 |  |
|  | `PGM_NMPR_STMT_DVSN_CD` | 프로그램호가신고구분코드 | string | N | 1 |  |
|  | `CVRG_SLCT_RSON_CD` | 반대매매선정사유코드 | string | N | 20 |  |
|  | `CVRG_SEQ` | 반대매매순번 | string | N | 19 |  |
|  | `EXCG_ID_DVSN_CD` | 거래소ID구분코드 | string | N | 3 | 한국거래소 : KRX 대체거래소 (넥스트레이드) : NXT SOR (Smart Order Routing) : SOR → 미입력시 KRX로 진행되며, 모의투자는 KRX만 가능 |
|  | `CNDT_PRIC` | 조건가격 | string | N | 19 | 스탑지정가호가에서 사용 |
| Response Header | `content-type` | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| Response Body | `rt_cd` | 성공 실패 여부 | string | Y | 1 |  |
|  | `msg_cd` | 응답코드 | string | Y | 8 |  |
|  | `msg1` | 응답메세지 | string | Y | 80 |  |
|  | `output` | 응답상세 | object | Y |  | single |
|  | `krx_fwdg_ord_orgno` | 한국거래소전송주문조직번호 | string | Y | 5 |  |
|  | `odno` | 주문번호 | string | Y | 10 |  |
|  | `ord_tmd` | 주문시간 | string | Y | 6 |  |

## Example

### Request Example (Python)
```
{
    "CANO": "810XXXXX",
    "ACNT_PRDT_CD": "01",
    "PDNO": "009150",
    "CRDT_TYPE": "21",
    "LOAN_DT": "20211103",
    "ORD_DVSN": "00",
    "ORD_QTY": "1",
    "ORD_UNPR": "130000",
    "RSVN_ORD_YN": "N"
}
```

### Response Example
```
{
  "rt_cd": "0",
  "msg_cd": "APBK0013",
  "msg1": "주문 전송 완료 되었습니다.",
  "output": {
    "KRX_FWDG_ORD_ORGNO": "06010",
    "ODNO": "0001569138",
    "ORD_TMD": "131421"
  }
}
```


---
## 우리 코드 위치
_(사용 위치 기록)_
