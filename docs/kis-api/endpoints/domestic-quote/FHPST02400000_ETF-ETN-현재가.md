# FHPST02400000 — ETF/ETN 현재가

> KIS Open API 공식 docs 자동 변환. [GOTCHAS.md](../../GOTCHAS.md) 참조.

## Metadata

| 항목 | 값 |
|---|---|
| API 명 | ETF/ETN 현재가 |
| 실전 TR_ID | `FHPST02400000` |
| 모의 TR_ID | 모의투자 미지원 |
| URL | `/uapi/etfetn/v1/quotations/inquire-price` |

## 개요

ETF/ETN 현재가 API입니다.
한국투자 HTS(eFriend Plus) &gt; [0240] ETF/ETN 현재가 화면의 기능을 API로 개발한 사항으로, 해당 화면을 참고하시면 기능을 이해하기 쉽습니다.

## Request / Response
| 구분 | Element | 한글명 | Type | Required | Length | Description |
|---|---|---|---|---|---|---|
| Request Header | `content-type` | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
|  | `authorization` | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token  일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용)  법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차 |
|  | `appkey` | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
|  | `appsecret` | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
|  | `personalseckey` | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
|  | `tr_id` | 거래ID | string | Y | 13 | FHPST02400000 |
|  | `tr_cont` | 연속 거래 여부 | string | N | 1 | tr_cont를 이용한 다음조회 불가 API |
|  | `custtype` | 고객 타입 | string | Y | 1 | B : 법인  P : 개인 |
|  | `seq_no` | 일련번호 | string | N | 2 | [법인 필수] 001 |
|  | `mac_address` | 맥주소 | string | N | 12 | 법인고객 혹은 개인고객의 Mac address 값 |
|  | `phone_number` | 핸드폰번호 | string | N | 12 | [법인 필수] 제휴사APP을 사용하는 경우 사용자(회원) 핸드폰번호  ex) 01011112222 (하이픈 등 구분값 제거) |
|  | `ip_addr` | 접속 단말 공인 IP | string | N | 12 | [법인 필수] 사용자(회원)의 IP Address |
|  | `gt_uid` | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |
| Request Query Parameter | `fid_input_iscd` | FID 입력 종목코드 | string | Y | 12 | 종목코드 |
|  | `fid_cond_mrkt_div_code` | FID 조건 시장 분류 코드 | string | Y | 2 | J |
| Response Header | `content-type` | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
|  | `tr_id` | 거래ID | string | Y | 13 | 요청한 tr_id |
|  | `tr_cont` | 연속 거래 여부 | string | N | 1 | tr_cont를 이용한 다음조회 불가 API |
|  | `gt_uid` | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |
| Response Body | `rt_cd` | 성공 실패 여부 | string | Y | 1 |  |
|  | `msg_cd` | 응답코드 | string | Y | 8 |  |
|  | `msg1` | 응답메세지 | string | Y | 80 |  |
|  | `output` | 응답상세 | object | Y |  |  |
|  | `stck_prpr` | 주식 현재가 | string | Y | 10 |  |
|  | `prdy_vrss_sign` | 전일 대비 부호 | string | Y | 1 |  |
|  | `prdy_vrss` | 전일 대비 | string | Y | 10 |  |
|  | `prdy_ctrt` | 전일 대비율 | string | Y | 82 |  |
|  | `acml_vol` | 누적 거래량 | string | Y | 18 |  |
|  | `prdy_vol` | 전일 거래량 | string | Y | 18 |  |
|  | `stck_mxpr` | 주식 상한가 | string | Y | 10 |  |
|  | `stck_llam` | 주식 하한가 | string | Y | 10 |  |
|  | `stck_prdy_clpr` | 주식 전일 종가 | string | Y | 10 |  |
|  | `stck_oprc` | 주식 시가2 | string | Y | 10 |  |
|  | `prdy_clpr_vrss_oprc_rate` | 전일 종가 대비 시가2 비율 | string | Y | 84 |  |
|  | `stck_hgpr` | 주식 최고가 | string | Y | 10 |  |
|  | `prdy_clpr_vrss_hgpr_rate` | 전일 종가 대비 최고가 비율 | string | Y | 84 |  |
|  | `stck_lwpr` | 주식 최저가 | string | Y | 10 |  |
|  | `prdy_clpr_vrss_lwpr_rate` | 전일 종가 대비 최저가 비율 | string | Y | 84 |  |
|  | `prdy_last_nav` | 전일 최종 NAV | string | Y | 112 |  |
|  | `nav` | NAV | string | Y | 112 |  |
|  | `nav_prdy_vrss` | NAV 전일 대비 | string | Y | 112 |  |
|  | `nav_prdy_vrss_sign` | NAV 전일 대비 부호 | string | Y | 1 |  |
|  | `nav_prdy_ctrt` | NAV 전일 대비율 | string | Y | 82 |  |
|  | `trc_errt` | 추적 오차율 | string | Y | 82 |  |
|  | `stck_sdpr` | 주식 기준가 | string | Y | 10 |  |
|  | `stck_sspr` | 주식 대용가 | string | Y | 10 |  |
|  | `nmix_ctrt` | 지수 대비율 | string | Y | 135 |  |
|  | `etf_crcl_stcn` | ETF 유통 주수 | string | Y | 18 |  |
|  | `etf_ntas_ttam` | ETF 순자산 총액 | string | Y | 22 |  |
|  | `etf_frcr_ntas_ttam` | ETF 외화 순자산 총액 | string | Y | 22 |  |
|  | `frgn_limt_rate` | 외국인 한도 비율 | string | Y | 84 |  |
|  | `frgn_oder_able_qty` | 외국인 주문 가능 수량 | string | Y | 18 |  |
|  | `etf_cu_unit_scrt_cnt` | ETF CU 단위 증권 수 | string | Y | 18 |  |
|  | `etf_cnfg_issu_cnt` | ETF 구성 종목 수 | string | Y | 18 |  |
|  | `etf_dvdn_cycl` | ETF 배당 주기 | string | Y | 2 |  |
|  | `crcd` | 통화 코드 | string | Y | 4 |  |
|  | `etf_crcl_ntas_ttam` | ETF 유통 순자산 총액 | string | Y | 22 |  |
|  | `etf_frcr_crcl_ntas_ttam` | ETF 외화 유통 순자산 총액 | string | Y | 22 |  |
|  | `etf_frcr_last_ntas_wrth_val` | ETF 외화 최종 순자산 가치 값 | string | Y | 13 |  |
|  | `lp_oder_able_cls_code` | LP 주문 가능 구분 코드 | string | Y | 2 |  |
|  | `stck_dryy_hgpr` | 주식 연중 최고가 | string | Y | 10 |  |
|  | `dryy_hgpr_vrss_prpr_rate` | 연중 최고가 대비 현재가 비율 | string | Y | 84 |  |
|  | `dryy_hgpr_date` | 연중 최고가 일자 | string | Y | 8 |  |
|  | `stck_dryy_lwpr` | 주식 연중 최저가 | string | Y | 10 |  |
|  | `dryy_lwpr_vrss_prpr_rate` | 연중 최저가 대비 현재가 비율 | string | Y | 84 |  |
|  | `dryy_lwpr_date` | 연중 최저가 일자 | string | Y | 8 |  |
|  | `bstp_kor_isnm` | 업종 한글 종목명 | string | Y | 40 | ※ 거래소 정보로 특정 종목은 업종구분이 없어 데이터 미회신 |
|  | `vi_cls_code` | VI적용구분코드 | string | Y | 1 |  |
|  | `lstn_stcn` | 상장 주수 | string | Y | 18 |  |
|  | `frgn_hldn_qty` | 외국인 보유 수량 | string | Y | 18 |  |
|  | `frgn_hldn_qty_rate` | 외국인 보유 수량 비율 | string | Y | 84 |  |
|  | `etf_trc_ert_mltp` | ETF 추적 수익률 배수 | string | Y | 126 |  |
|  | `dprt` | 괴리율 | string | Y | 82 |  |
|  | `mbcr_name` | 회원사 명 | string | Y | 50 |  |
|  | `stck_lstn_date` | 주식 상장 일자 | string | Y | 8 |  |
|  | `mtrt_date` | 만기 일자 | string | Y | 8 |  |
|  | `shrg_type_code` | 분배금형태코드 | string | Y | 2 |  |
|  | `lp_hldn_rate` | LP 보유 비율 | string | Y | 84 |  |
|  | `etf_trgt_nmix_bstp_code` | ETF대상지수업종코드 | string | Y | 4 |  |
|  | `etf_div_name` | ETF 분류 명 | string | Y | 40 |  |
|  | `etf_rprs_bstp_kor_isnm` | ETF 대표 업종 한글 종목명 | string | Y | 40 |  |
|  | `lp_hldn_vol` | ETN LP 보유량 | string | Y | 18 |  |

---
## 우리 코드 위치
_(사용 위치 기록)_
