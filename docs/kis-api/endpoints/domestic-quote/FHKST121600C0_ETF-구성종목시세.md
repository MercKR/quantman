# FHKST121600C0 — ETF 구성종목시세

> KIS Open API 공식 docs 자동 변환. 시행착오는 [GOTCHAS.md](../../GOTCHAS.md) 참조.

## Metadata

| 항목 | 값 |
|---|---|
| API 명 | ETF 구성종목시세 |
| API ID | 국내주식-073 |
| 실전 TR_ID | `FHKST121600C0` |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | `GET` |
| URL | `/uapi/etfetn/v1/quotations/inquire-component-stock-price` |
| 실전 Domain | `https://openapi.koreainvestment.com:9443` |
| 모의 Domain | 모의투자 미지원 |

## 개요

ETF 구성종목시세 API입니다. 
한국투자 HTS(eFriend Plus) &gt; [0245] ETF/ETN 구성종목시세 화면의 기능을 API로 개발한 사항으로, 해당 화면을 참고하시면 기능을 이해하기 쉽습니다.

## Request / Response

| 구분 | Element | 한글명 | Type | Required | Length | Description |
|---|---|---|---|---|---|---|
| Request Header | `content-type` | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
|  | `authorization` | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token  일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용)  법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차 |
|  | `appkey` | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
|  | `appsecret` | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
|  | `personalseckey` | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
|  | `tr_id` | 거래ID | string | Y | 13 | FHKST121600C0 |
|  | `tr_cont` | 연속 거래 여부 | string | N | 1 | tr_cont를 이용한 다음조회 불가 API |
|  | `custtype` | 고객 타입 | string | Y | 1 | B : 법인  P : 개인 |
|  | `seq_no` | 일련번호 | string | N | 2 | [법인 필수] 001 |
|  | `mac_address` | 맥주소 | string | N | 12 | 법인고객 혹은 개인고객의 Mac address 값 |
|  | `phone_number` | 핸드폰번호 | string | N | 12 | [법인 필수] 제휴사APP을 사용하는 경우 사용자(회원) 핸드폰번호  ex) 01011112222 (하이픈 등 구분값 제거) |
|  | `ip_addr` | 접속 단말 공인 IP | string | N | 12 | [법인 필수] 사용자(회원)의 IP Address |
|  | `gt_uid` | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |
| Request Query Parameter | `FID_COND_MRKT_DIV_CODE` | 조건시장분류코드 | string | Y | 2 | 시장구분코드 (J) |
|  | `FID_INPUT_ISCD` | 입력종목코드 | string | Y | 12 | 종목코드 |
|  | `FID_COND_SCR_DIV_CODE` | 조건화면분류코드 | string | Y | 5 | Unique key( 11216 ) |
| Response Header | `content-type` | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
|  | `tr_id` | 거래ID | string | Y | 13 | 요청한 tr_id |
|  | `tr_cont` | 연속 거래 여부 | string | N | 1 | tr_cont를 이용한 다음조회 불가 API |
|  | `gt_uid` | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |
| Response Body | `rt_cd` | 성공 실패 여부 | string | Y | 1 |  |
|  | `msg_cd` | 응답코드 | string | Y | 8 |  |
|  | `msg1` | 응답메세지 | string | Y | 80 |  |
|  | `output1` | 응답상세 | object | Y |  |  |
|  | `stck_prpr` | 주식 현재가 | string | Y | 10 |  |
|  | `prdy_vrss` | 전일 대비 | string | Y | 10 |  |
|  | `prdy_vrss_sign` | 전일 대비 부호 | string | Y | 1 |  |
|  | `prdy_ctrt` | 전일 대비율 | string | Y | 82 |  |
|  | `etf_cnfg_issu_avls` | ETF구성종목시가총액 | string | Y | 18 |  |
|  | `nav` | NAV | string | Y | 112 |  |
|  | `nav_prdy_vrss_sign` | NAV 전일 대비 부호 | string | Y | 1 |  |
|  | `nav_prdy_vrss` | NAV 전일 대비 | string | Y | 112 |  |
|  | `nav_prdy_ctrt` | NAV 전일 대비율 | string | Y | 84 |  |
|  | `etf_ntas_ttam` | ETF 순자산 총액 | string | Y | 22 |  |
|  | `prdy_clpr_nav` | NAV전일종가 | string | Y | 112 |  |
|  | `oprc_nav` | NAV시가 | string | Y | 112 |  |
|  | `hprc_nav` | NAV고가 | string | Y | 112 |  |
|  | `lprc_nav` | NAV저가 | string | Y | 112 |  |
|  | `etf_cu_unit_scrt_cnt` | ETF CU 단위 증권 수 | string | Y | 18 |  |
|  | `etf_cnfg_issu_cnt` | ETF 구성 종목 수 | string | Y | 18 |  |
|  | `output2` | 응답상세 | object array | Y |  | array |
|  | `stck_shrn_iscd` | 주식 단축 종목코드 | string | Y | 9 |  |
|  | `hts_kor_isnm` | HTS 한글 종목명 | string | Y | 40 |  |
|  | `stck_prpr` | 주식 현재가 | string | Y | 10 |  |
|  | `prdy_vrss` | 전일 대비 | string | Y | 10 |  |
|  | `prdy_vrss_sign` | 전일 대비 부호 | string | Y | 1 |  |
|  | `prdy_ctrt` | 전일 대비율 | string | Y | 82 |  |
|  | `acml_vol` | 누적 거래량 | string | Y | 18 |  |
|  | `acml_tr_pbmn` | 누적 거래 대금 | string | Y | 18 |  |
|  | `tday_rsfl_rate` | 당일 등락 비율 | string | Y | 52 |  |
|  | `prdy_vrss_vol` | 전일 대비 거래량 | string | Y | 18 |  |
|  | `tr_pbmn_tnrt` | 거래대금회전율 | string | Y | 82 |  |
|  | `hts_avls` | HTS 시가총액 | string | Y | 18 |  |
|  | `etf_cnfg_issu_avls` | ETF구성종목시가총액 | string | Y | 18 |  |
|  | `etf_cnfg_issu_rlim` | ETF구성종목비중 | string | Y | 72 |  |
|  | `etf_vltn_amt` | ETF구성종목내평가금액 | string | Y | 18 |  |

## Example

### Request Example (Python)
```
fid_cond_mrkt_div_code:J
fid_input_iscd:069500
fid_cond_scr_div_code:11216
```

### Response Example
```
{
    "output1": {
        "stck_prpr": "37195",
        "prdy_vrss": "-365",
        "prdy_vrss_sign": "5",
        "prdy_ctrt": "-0.97",
        "etf_cnfg_issu_avls": "184153",
        "nav": "37301.11",
        "nav_prdy_vrss_sign": "5",
        "nav_prdy_vrss": "-347.36",
        "nav_prdy_ctrt": "-0.92",
        "etf_ntas_ttam": "68256",
        "prdy_clpr_nav": "37648.47",
        "oprc_nav": "37653.39",
        "hprc_nav": "37720.17",
        "lprc_nav": "37223.93",
        "etf_cu_unit_scrt_cnt": "50000",
        "etf_cnfg_issu_cnt": "201"
    },
    "output2": [
        {
            "stck_shrn_iscd": "005930",
            "hts_kor_isnm": "삼성전자",
            "stck_prpr": "83700",
            "prdy_vrss": "-400",
            "prdy_vrss_sign": "5",
            "prdy_ctrt": "-0.48",
            "acml_vol": "16967184",
            "acml_tr_pbmn": "1421776834400",
            "tday_rsfl_rate": "2.02",
            "prdy_vrss_vol": "-8570824",
            "tr_pbmn_tnrt": "0.28",
            "hts_avls": "4996708",
            "etf_cnfg_issu_avls": "601300800",
            "etf_cnfg_issu_rlim": "32.65",
            "etf_vltn_amt": "604174400"
        },
        {
            "stck_shrn_iscd": "000660",
            "hts_kor_isnm": "SK하이닉스",
            "stck_prpr": "187400",
            "prdy_vrss": "-1000",
            "prdy_vrss_sign": "5",
            "prdy_ctrt": "-0.53",
            "acml_vol": "3042349",
            "acml_tr_pbmn": "575151315700",
            "tday_rsfl_rate": "2.34",
            "prdy_vrss_vol": "-1055882",
            "tr_pbmn_tnrt": "0.42",
            "hts_avls": "1364276",
            "etf_cnfg_issu_avls": "160039600",
            "etf_cnfg_issu_rlim": "8.69",
            "etf_vltn_amt": "160893600"
        },
        {
            "stck_shrn_iscd": "005380",
            "hts_kor_isnm": "현대차",
            "stck_prpr": "238000",
            "prdy_vrss": "-3000",
            "prdy_vrss_sign": "5",
            "prdy_ctrt": "-1.24",
            "acml_vol": "993944",
            "acml_tr_pbmn": "237608070000",
            "tday_rsfl_rate": "1.87",
            "prdy_vrss_vol": "-859847",
            "tr_pbmn_tnrt": "0.47",
            "hts_avls": "503445",
            "etf_cnfg_issu_avls": "50694000",
            "etf_cnfg_issu_rlim": "2.75",
            "etf_vltn_amt": "51333000"
        },
        {
            "stck_shrn_iscd": "068270",
            "hts_kor_isnm": "셀트리온",
            "stck_prpr": "182200",
            "prdy_vrss": "2700",
            "prdy_vrss_sign": "2",
            "prdy_ctrt": "1.50",
            "acml_vol": "473566",
            "acml_tr_pbmn": "85712403800",
            "tday_rsfl_rate": "2.90",
            "prdy_vrss_vol": "-52048",
            "tr_pbmn_tnrt": "0.22",
            "hts_avls": "397287",
            "etf_cnfg_issu_avls": "46643200",
            "etf_cnfg_issu_rlim": "2.53",
            "etf_vltn_amt"
```


---
## 우리 코드 위치
_(사용 위치 기록)_
