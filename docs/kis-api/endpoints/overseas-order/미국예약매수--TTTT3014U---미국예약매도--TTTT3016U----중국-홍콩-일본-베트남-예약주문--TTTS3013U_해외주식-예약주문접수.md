# (미국예약매수) TTTT3014U  (미국예약매도) TTTT3016U   (중국/홍콩/일본/베트남 예약주문) TTTS3013U — 해외주식 예약주문접수

> KIS Open API 공식 docs 자동 변환. [GOTCHAS.md](../../GOTCHAS.md) 참조.

## Metadata

| 항목 | 값 |
|---|---|
| API 명 | 해외주식 예약주문접수 |
| 실전 TR_ID | `(미국예약매수) TTTT3014U  (미국예약매도) TTTT3016U   (중국/홍콩/일본/베트남 예약주문) TTTS3013U` |
| 모의 TR_ID | (미국예약매수) VTTT3014U  (미국예약매도) VTTT3016U   (중국/홍콩/일본/베트남 예약주문) VTTS3013U |
| URL | `/uapi/overseas-stock/v1/trading/order-resv` |

## 개요

미국거래소 운영시간 외 미국주식을 예약 매매하기 위한 API입니다.

* 해외주식 서비스 신청 후 이용 가능합니다. (아래 링크 3번 해외증권 거래신청 참고)
https://securities.koreainvestment.com/main/bond/research/_static/TF03ca010001.jsp

※ POST API의 경우 BODY값의 key값들을 대문자로 작성하셔야 합니다.
   (EX. "CANO" : "12345678", "ACNT_PRDT_CD": "01",...)

* 아래 각 국가의 시장별 예약주문 접수 가능 시간을 확인하시길 바랍니다.

미국 예약주문 접수시간
1) 10:00 ~ 23:20 / 10:00 ~ 22:20 (서머타임 시)
2) 주문제한 : 16:30 ~ 16:45 경까지 (사유 : 시스템 정산작업시간)
3) 23:30 정규장으로 주문 전송 (서머타임 시 22:30 정규장 주문 전송)
4) 미국 거래소 운영시간(한국시간 기준) : 23:30 ~ 06:00 (썸머타임 적용 시 22:30 ~ 05:00)

홍콩 예약주문 접수시간
1) 09:00 ~ 10:20 접수, 10:30 주문전송
2) 10:40 ~ 13:50 접수, 14:00 주문전송

중국 예약주문 접수시간
1) 09:00 ~ 10:20 접수, 10:30 주문전송
2) 10:40 ~ 13:50 접수, 14:00 주문전송

일본 예약주문 접수시간
1) 09:10 ~ 12:20 까지 접수, 12:30 주문전송

베트남 예약주문 접수시간
1) 09:00 ~ 11:00 까지 접수, 11:15 주문전송
2) 11:20 ~ 14:50 까지 접수, 15:00 주문전송

* 예약주문 유의사항
1) 예약주문 유효기간 : 당일
 - 미국장 마감 후, 미체결주문은 자동취소
 - 미국휴장 시, 익 영업일로 이전
   (미국예약주문화면에서 취소 가능)
2) 증거금 및 잔고보유 : 체크 안함
3) 주문전송 불가사유
 - 매수증거금 부족: 수수료 포함 매수금액부족, 환전, 시세이용료 출금, 인출에 의한 증거금 부족
 - 기타 매수증거금 부족, 매도가능수량 부족, 주권변경 등 권리발생으로 인한 주문불가사유 발생
4) 지정가주문만 가능
* 단 미국 예약매도주문(TTTT3016U)의 경우, MOO(장개시시장가)로 주문 접수 가능

## Request / Response
| 구분 | Element | 한글명 | Type | Required | Length | Description |
|---|---|---|---|---|---|---|
| Request Header | `content-type` | 컨텐츠타입 | string | N | 40 | application/json; charset=utf-8 |
|  | `authorization` | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token 일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) 법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를  |
|  | `appkey` | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
|  | `appsecret` | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appsecret (절대 노출되지 않도록 주의해주세요.) |
|  | `personalseckey` | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
|  | `tr_id` | 거래ID | string | Y | 13 | [실전투자] TTTT3016U : 미국 매도 예약 주문 TTTT3014U : 미국 매수 예약 주문 TTTS3013U : 중국/홍콩/일본/베트남 예약 매수/매도/취소 주문  [모의투자] VTTT3016U : 미국 매도 예약 주문 VTTT3014U : 미국 매수 예약 주문 VTTS3013U : 중국/홍콩/일본/베트남 예약 매수/매도/취소 주문 |
|  | `tr_cont` | 연속 거래 여부 | string | N | 1 | tr_cont를 이용한 다음조회 불가 API |
|  | `custtype` | 고객타입 | string | N | 1 | B : 법인 P : 개인 |
|  | `seq_no` | 일련번호 | string | N | 2 | [법인 필수] 001 |
|  | `mac_address` | 맥주소 | string | N | 12 | 법인고객 혹은 개인고객의 Mac address 값 |
|  | `phone_number` | 핸드폰번호 | string | N | 12 | [법인 필수] 제휴사APP을 사용하는 경우 사용자(회원) 핸드폰번호 ex) 01011112222 (하이픈 등 구분값 제거) |
|  | `ip_addr` | 접속 단말 공인 IP | string | N | 12 | [법인 필수] 사용자(회원)의 IP Address |
|  | `gt_uid` | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |
| Request Body | `CANO` | 종합계좌번호 | string | Y | 8 | 계좌번호 체계(8-2)의 앞 8자리 |
|  | `ACNT_PRDT_CD` | 계좌상품코드 | string | Y | 2 | 계좌번호 체계(8-2)의 뒤 2자리 |
|  | `SLL_BUY_DVSN_CD` | 매도매수구분코드 | string | N | 2 | tr_id가 TTTS3013U(중국/홍콩/일본/베트남 예약 주문)인 경우만 사용 01 : 매도 02 : 매수 |
|  | `RVSE_CNCL_DVSN_CD` | 정정취소구분코드 | string | Y | 2 | tr_id가 TTTS3013U(중국/홍콩/일본/베트남 예약 주문)인 경우만 사용 00 : "매도/매수 주문"시 필수 항목 02 : 취소 |
|  | `PDNO` | 상품번호 | string | Y | 12 |  |
|  | `PRDT_TYPE_CD` | 상품유형코드 | string | Y | 3 | tr_id가 TTTS3013U(중국/홍콩/일본/베트남 예약 주문)인 경우만 사용 515 : 일본 501 : 홍콩 / 543 : 홍콩CNY / 558 : 홍콩USD 507 : 베트남 하노이거래소 / 508 : 베트남 호치민거래소 551 : 중국 상해A / 552 : 중국 심천A |
|  | `OVRS_EXCG_CD` | 해외거래소코드 | string | Y | 4 | NASD : 나스닥 NYSE : 뉴욕 AMEX : 아멕스 SEHK : 홍콩 SHAA : 중국상해 SZAA : 중국심천 TKSE : 일본 HASE : 베트남 하노이 VNSE : 베트남 호치민 |
|  | `FT_ORD_QTY` | FT주문수량 | string | Y | 10 |  |
|  | `FT_ORD_UNPR3` | FT주문단가3 | string | Y | 27 |  |
|  | `ORD_SVR_DVSN_CD` | 주문서버구분코드 | string | N | 1 | "0"(Default) |
|  | `RSVN_ORD_RCIT_DT` | 예약주문접수일자 | string | N | 8 | tr_id가 TTTS3013U(중국/홍콩/일본/베트남 예약 주문)인 경우만 사용 |
|  | `ORD_DVSN` | 주문구분 | string | N | 20 | tr_id가 TTTT3014U(미국 예약 매수 주문)인 경우만 사용 00 : 지정가 35 : TWAP 36 : VWAP  tr_id가 TTTT3016U(미국 예약 매도 주문)인 경우만 사용 00 : 지정가 31 : MOO(장개시시장가) 35 : TWAP 36 : VWAP |
|  | `OVRS_RSVN_ODNO` | 해외예약주문번호 | string | N | 10 | tr_id가 TTTS3013U(중국/홍콩/일본/베트남 예약 주문)인 경우만 사용 |
|  | `ALGO_ORD_TMD_DVSN_CD` | 알고리즘주문시간구분코드 | string | N | 2 | ※ TWAP, VWAP 주문에서만 사용. 예약주문은 시간입력 불가하여 02로 값 고정 ※ 정규장 종료 10분전까지 가능 |
| Response Header | `content-type` | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| Response Body | `rt_cd` | 성공 실패 여부 | string | Y | 1 | 0 : 성공  0 이외의 값 : 실패 |
|  | `msg_cd` | 응답코드 | string | Y | 8 | 응답코드 |
|  | `msg1` | 응답메세지 | string | Y | 80 | 응답메세지 |
|  | `output` | 응답상세 | object | Y |  |  |
|  | `ODNO` | 한국거래소전송주문조직번호 | string | Y | 10 | tr_id가 TTTT3016U(미국 예약 매도 주문) / TTTT3014U(미국 예약 매수 주문)인 경우만 출력 |
|  | `RSVN_ORD_RCIT_DT` | 예약주문접수일자 | string | Y | 8 | tr_id가 TTTS3013U(중국/홍콩/일본/베트남 예약 주문)인 경우만 출력 |
|  | `OVRS_RSVN_ODNO` | 해외예약주문번호 | string | Y | 10 | tr_id가 TTTS3013U(중국/홍콩/일본/베트남 예약 주문)인 경우만 출력 |

---
## 우리 코드 위치

미국만 사용 (TTTT3014U 매수 지정가 / TTTT3016U 매도 MOO). 아시아(TTTS3013U)는
접수시간·body 규격이 달라 미지원.

- `platform/local/localapp/kis_broker.py`
  - `_OVERSEAS_RESV_TR` (side,virtual)→TR 매핑 — VTTT3014U/TTTT3014U(매수),
    VTTT3016U/TTTT3016U(매도)
  - `_submit_overseas_resv()` — body 구성(FT_ORD_QTY/FT_ORD_UNPR3/ORD_DVSN),
    `POST /uapi/overseas-stock/v1/trading/order-resv`. 미지원 시장(NAS/NYS/AMS 외)
    조기 차단.
  - `buy_resv_limit()` — 매수 지정가(ORD_DVSN=00)
  - `sell_resv_moo()` — 매도 MOO 장개시시장가(ORD_DVSN=31)
- `platform/local/localapp/trader.py`
  - `_submit_buy()`/`_submit_sell()` — `_reserved_us` True 시 예약 라우팅(매수는
    지정가 강제)
  - `cycle()`/`_cycle_locked()` — `reserved` 파라미터로 `_reserved_us` set
    (try/finally reset; 장중 청산 re-entry는 항상 False)
- `platform/local/localapp/runner.py`
  - `run_cycle(reserved=)` — 예약발주 cycle에 전달
  - `run_post_open_reconcile()` — 개장+5분 예약체결 reconcile(미체결 working 매수
    취소 안 함)
- `platform/local/localapp/scheduler.py`
  - `_plan_us_session()` — us_cycle(개장−20분, reserved=True) +
    us_post_open_reconcile(개장+5분)
- 테스트: `platform/local/tests/test_overseas_reserved_order.py`

### 접수 시간 (스케줄 근거)
예약 접수는 개장 −10분에 마감(서머타임 22:20 / 겨울 23:20)되므로, dataset
다운로드(~130초)+평가 여유를 두고 **개장 −20분**에 발주 cycle을 시작한다.

### 미검증 (live 실측 게이트)
모의투자(VTTT3014U/VTTT3016U) 실제 접수·전송·체결은 접수창(KST 10:00~개장−10분)
에서만 검증 가능 — 코드/단위테스트는 통과했으나 KIS 모의서버 실응답은 다음
접수창에서 1회 확인 후 GOTCHAS에 기록 필요.
