# KIS API Endpoint Index

전체 132 endpoint 색인. **작업 전 `grep -i <키워드> INDEX.md`로 후보 찾기.**
상세는 `endpoints/{category}/{TR_ID}_*.md` 참조.

## 국내주식 — 기본시세 (22 endpoints, [raw](raw/국내주식_기본시세.xlsx))

| TR_ID | API 명 | 모의 |
|---|---|---|
| [`FHKST01010100`](endpoints/domestic-quote/FHKST01010100_주식현재가-시세.md) | 주식현재가 시세 | ✓ |
| [`FHPST01010000`](endpoints/domestic-quote/FHPST01010000_주식현재가-시세2.md) | 주식현재가 시세2 | ✗ |
| [`FHKST01010300`](endpoints/domestic-quote/FHKST01010300_주식현재가-체결.md) | 주식현재가 체결 | ✓ |
| [`FHKST01010400`](endpoints/domestic-quote/FHKST01010400_주식현재가-일자별.md) | 주식현재가 일자별 | ✓ |
| [`FHKST01010200`](endpoints/domestic-quote/FHKST01010200_주식현재가-호가-예상체결.md) | 주식현재가 호가/예상체결 | ✓ |
| [`FHKST01010900`](endpoints/domestic-quote/FHKST01010900_주식현재가-투자자.md) | 주식현재가 투자자 | ✓ |
| [`FHKST01010600`](endpoints/domestic-quote/FHKST01010600_주식현재가-회원사.md) | 주식현재가 회원사 | ✓ |
| [`FHKST03010100`](endpoints/domestic-quote/FHKST03010100_국내주식기간별시세-일-주-월-년.md) | 국내주식기간별시세(일/주/월/년) | ✓ |
| [`FHKST03010200`](endpoints/domestic-quote/FHKST03010200_주식당일분봉조회.md) | 주식당일분봉조회 | ✓ |
| [`FHKST03010230`](endpoints/domestic-quote/FHKST03010230_주식일별분봉조회.md) | 주식일별분봉조회 | ✗ |
| [`FHPST01060000`](endpoints/domestic-quote/FHPST01060000_주식현재가-당일시간대별체결.md) | 주식현재가 당일시간대별체결 | ✓ |
| [`FHPST02320000`](endpoints/domestic-quote/FHPST02320000_주식현재가-시간외일자별주가.md) | 주식현재가 시간외일자별주가 | ✓ |
| [`FHPST02310000`](endpoints/domestic-quote/FHPST02310000_주식현재가-시간외시간별체결.md) | 주식현재가 시간외시간별체결 | ✓ |
| [`FHPST02300000`](endpoints/domestic-quote/FHPST02300000_국내주식-시간외현재가.md) | 국내주식 시간외현재가 | ✗ |
| [`FHPST02300400`](endpoints/domestic-quote/FHPST02300400_국내주식-시간외호가.md) | 국내주식 시간외호가 | ✗ |
| [`FHKST117300C0`](endpoints/domestic-quote/FHKST117300C0_국내주식-장마감-예상체결가.md) | 국내주식 장마감 예상체결가 | ✗ |
| [`FHPST02400000`](endpoints/domestic-quote/FHPST02400000_ETF-ETN-현재가.md) | ETF/ETN 현재가 | ✗ |
| [`FHKST121600C0`](endpoints/domestic-quote/FHKST121600C0_ETF-구성종목시세.md) | ETF 구성종목시세 | ✗ |
| [`FHPST02440000`](endpoints/domestic-quote/FHPST02440000_NAV-비교추이-종목.md) | NAV 비교추이(종목) | ✗ |
| [`FHPST02440200`](endpoints/domestic-quote/FHPST02440200_NAV-비교추이-일.md) | NAV 비교추이(일) | ✗ |
| [`FHPST02440100`](endpoints/domestic-quote/FHPST02440100_NAV-비교추이-분.md) | NAV 비교추이(분) | ✗ |
| [`FHPST02400200`](endpoints/domestic-quote/FHPST02400200_ETF-현재가-호가.md) | ETF 현재가 호가 | ✗ |

## 국내주식 — 실시간시세 (29 endpoints, [raw](raw/국내주식_실시간시세.xlsx))

| TR_ID | API 명 | 모의 |
|---|---|---|
| [`H0STCNT0`](endpoints/domestic-realtime/H0STCNT0_국내주식-실시간체결가--KRX.md) | 국내주식 실시간체결가 (KRX) | ✓ |
| [`H0STASP0`](endpoints/domestic-realtime/H0STASP0_국내주식-실시간호가--KRX.md) | 국내주식 실시간호가 (KRX) | ✓ |
| [`H0STCNI0`](endpoints/domestic-realtime/H0STCNI0_국내주식-실시간체결통보.md) | 국내주식 실시간체결통보 | ✓ |
| [`H0STANC0`](endpoints/domestic-realtime/H0STANC0_국내주식-실시간예상체결--KRX.md) | 국내주식 실시간예상체결 (KRX) | ✗ |
| [`H0STMBC0`](endpoints/domestic-realtime/H0STMBC0_국내주식-실시간회원사--KRX.md) | 국내주식 실시간회원사 (KRX) | ✗ |
| [`H0STPGM0`](endpoints/domestic-realtime/H0STPGM0_국내주식-실시간프로그램매매--KRX.md) | 국내주식 실시간프로그램매매 (KRX) | ✗ |
| [`H0STMKO0`](endpoints/domestic-realtime/H0STMKO0_국내주식-장운영정보--KRX.md) | 국내주식 장운영정보 (KRX) | ✗ |
| [`H0STOAA0`](endpoints/domestic-realtime/H0STOAA0_국내주식-시간외-실시간호가--KRX.md) | 국내주식 시간외 실시간호가 (KRX) | ✗ |
| [`H0STOUP0`](endpoints/domestic-realtime/H0STOUP0_국내주식-시간외-실시간체결가--KRX.md) | 국내주식 시간외 실시간체결가 (KRX) | ✗ |
| [`H0STOAC0`](endpoints/domestic-realtime/H0STOAC0_국내주식-시간외-실시간예상체결--KRX.md) | 국내주식 시간외 실시간예상체결 (KRX) | ✗ |
| [`H0UPCNT0`](endpoints/domestic-realtime/H0UPCNT0_국내지수-실시간체결.md) | 국내지수 실시간체결 | ✗ |
| [`H0UPANC0`](endpoints/domestic-realtime/H0UPANC0_국내지수-실시간예상체결.md) | 국내지수 실시간예상체결 | ✗ |
| [`H0UPPGM0`](endpoints/domestic-realtime/H0UPPGM0_국내지수-실시간프로그램매매.md) | 국내지수 실시간프로그램매매 | ✗ |
| [`H0EWASP0`](endpoints/domestic-realtime/H0EWASP0_ELW-실시간호가.md) | ELW 실시간호가 | ✗ |
| [`H0EWCNT0`](endpoints/domestic-realtime/H0EWCNT0_ELW-실시간체결가.md) | ELW 실시간체결가 | ✗ |
| [`H0EWANC0`](endpoints/domestic-realtime/H0EWANC0_ELW-실시간예상체결.md) | ELW 실시간예상체결 | ✗ |
| [`H0STNAV0`](endpoints/domestic-realtime/H0STNAV0_국내ETF-NAV추이.md) | 국내ETF NAV추이 | ✗ |
| [`H0UNCNT0`](endpoints/domestic-realtime/H0UNCNT0_국내주식-실시간체결가--통합.md) | 국내주식 실시간체결가 (통합) | ✗ |
| [`H0UNASP0`](endpoints/domestic-realtime/H0UNASP0_국내주식-실시간호가--통합.md) | 국내주식 실시간호가 (통합) | ✗ |
| [`H0UNANC0`](endpoints/domestic-realtime/H0UNANC0_국내주식-실시간예상체결--통합.md) | 국내주식 실시간예상체결 (통합) | ✗ |
| [`H0UNMBC0`](endpoints/domestic-realtime/H0UNMBC0_국내주식-실시간회원사--통합.md) | 국내주식 실시간회원사 (통합) | ✗ |
| [`H0UNPGM0`](endpoints/domestic-realtime/H0UNPGM0_국내주식-실시간프로그램매매--통합.md) | 국내주식 실시간프로그램매매 (통합) | ✗ |
| [`H0UNMKO0`](endpoints/domestic-realtime/H0UNMKO0_국내주식-장운영정보--통합.md) | 국내주식 장운영정보 (통합) | ✗ |
| [`H0NXCNT0`](endpoints/domestic-realtime/H0NXCNT0_국내주식-실시간체결가--NXT.md) | 국내주식 실시간체결가 (NXT) | ✗ |
| [`H0NXASP0`](endpoints/domestic-realtime/H0NXASP0_국내주식-실시간호가--NXT.md) | 국내주식 실시간호가 (NXT) | ✗ |
| [`H0NXANC0`](endpoints/domestic-realtime/H0NXANC0_국내주식-실시간예상체결--NXT.md) | 국내주식 실시간예상체결 (NXT) | ✗ |
| [`H0NXMBC0`](endpoints/domestic-realtime/H0NXMBC0_국내주식-실시간회원사--NXT.md) | 국내주식 실시간회원사 (NXT) | ✗ |
| [`H0NXPGM0`](endpoints/domestic-realtime/H0NXPGM0_국내주식-실시간프로그램매매--NXT.md) | 국내주식 실시간프로그램매매 (NXT) | ✗ |
| [`H0NXMKO0`](endpoints/domestic-realtime/H0NXMKO0_국내주식-장운영정보--NXT.md) | 국내주식 장운영정보 (NXT) | ✗ |

## 국내주식 — 주문/계좌 (23 endpoints, [raw](raw/국내주식_주문_계좌.xlsx))

| TR_ID | API 명 | 모의 |
|---|---|---|
| [`(매도) TTTC0011U (매수) TTTC0012U`](endpoints/domestic-order/(매도) TTTC0011U (매수) TTTC0012U_주식주문-현금.md) | 주식주문(현금) | ✓ |
| [`(매도) TTTC0051U (매수) TTTC0052U`](endpoints/domestic-order/(매도) TTTC0051U (매수) TTTC0052U_주식주문-신용.md) | 주식주문(신용) | ✗ |
| [`TTTC0013U`](endpoints/domestic-order/TTTC0013U_주식주문-정정취소.md) | 주식주문(정정취소) | ✓ |
| [`TTTC0084R`](endpoints/domestic-order/TTTC0084R_주식정정취소가능주문조회.md) | 주식정정취소가능주문조회 | ✗ |
| [`(3개월이내) TTTC0081R (3개월이전) CTSC9215R`](endpoints/domestic-order/(3개월이내) TTTC0081R (3개월이전) CTSC9215R_주식일별주문체결조회.md) | 주식일별주문체결조회 | ✓ |
| [`TTTC8434R`](endpoints/domestic-order/TTTC8434R_주식잔고조회.md) | 주식잔고조회 | ✓ |
| [`TTTC8908R`](endpoints/domestic-order/TTTC8908R_매수가능조회.md) | 매수가능조회 | ✓ |
| [`TTTC8408R`](endpoints/domestic-order/TTTC8408R_매도가능수량조회.md) | 매도가능수량조회 | ✗ |
| [`TTTC8909R`](endpoints/domestic-order/TTTC8909R_신용매수가능조회.md) | 신용매수가능조회 | ✗ |
| [`CTSC0008U`](endpoints/domestic-order/CTSC0008U_주식예약주문.md) | 주식예약주문 | ✗ |
| [`(예약취소) CTSC0009U (예약정정) CTSC0013U`](endpoints/domestic-order/(예약취소) CTSC0009U (예약정정) CTSC0013U_주식예약주문정정취소.md) | 주식예약주문정정취소 | ✗ |
| [`CTSC0004R`](endpoints/domestic-order/CTSC0004R_주식예약주문조회.md) | 주식예약주문조회 | ✗ |
| [`TTTC2202R`](endpoints/domestic-order/TTTC2202R_퇴직연금-체결기준잔고.md) | 퇴직연금 체결기준잔고 | ✗ |
| [`TTTC2201R(기존 KRX만 가능), TTTC2210R (KRX,NXT/SOR)`](endpoints/domestic-order/TTTC2201R-기존-KRX만-가능---TTTC2210R--KRX-NXT-SOR_퇴직연금-미체결내역.md) | 퇴직연금 미체결내역 | ✗ |
| [`TTTC0503R`](endpoints/domestic-order/TTTC0503R_퇴직연금-매수가능조회.md) | 퇴직연금 매수가능조회 | ✗ |
| [`TTTC0506R`](endpoints/domestic-order/TTTC0506R_퇴직연금-예수금조회.md) | 퇴직연금 예수금조회 | ✗ |
| [`TTTC2208R`](endpoints/domestic-order/TTTC2208R_퇴직연금-잔고조회.md) | 퇴직연금 잔고조회 | ✗ |
| [`TTTC8494R`](endpoints/domestic-order/TTTC8494R_주식잔고조회_실현손익.md) | 주식잔고조회_실현손익 | ✗ |
| [`CTRP6548R`](endpoints/domestic-order/CTRP6548R_투자계좌자산현황조회.md) | 투자계좌자산현황조회 | ✗ |
| [`TTTC8708R`](endpoints/domestic-order/TTTC8708R_기간별손익일별합산조회.md) | 기간별손익일별합산조회 | ✗ |
| [`TTTC8715R`](endpoints/domestic-order/TTTC8715R_기간별매매손익현황조회.md) | 기간별매매손익현황조회 | ✗ |
| [`TTTC0869R`](endpoints/domestic-order/TTTC0869R_주식통합증거금-현황.md) | 주식통합증거금 현황 | ✗ |
| [`CTRGA011R`](endpoints/domestic-order/CTRGA011R_기간별계좌권리현황조회.md) | 기간별계좌권리현황조회 | ✗ |

## 국내주식 — 순위분석 (22 endpoints, [raw](raw/국내주식_순위분석.xlsx))

| TR_ID | API 명 | 모의 |
|---|---|---|
| [`FHPST01710000`](endpoints/domestic-ranking/FHPST01710000_거래량순위.md) | 거래량순위 | ✗ |
| [`FHPST01700000`](endpoints/domestic-ranking/FHPST01700000_국내주식-등락률-순위.md) | 국내주식 등락률 순위 | ✗ |
| [`FHPST01720000`](endpoints/domestic-ranking/FHPST01720000_국내주식-호가잔량-순위.md) | 국내주식 호가잔량 순위 | ✗ |
| [`FHPST01730000`](endpoints/domestic-ranking/FHPST01730000_국내주식-수익자산지표-순위.md) | 국내주식 수익자산지표 순위 | ✗ |
| [`FHPST01740000`](endpoints/domestic-ranking/FHPST01740000_국내주식-시가총액-상위.md) | 국내주식 시가총액 상위 | ✗ |
| [`FHPST01750000`](endpoints/domestic-ranking/FHPST01750000_국내주식-재무비율-순위.md) | 국내주식 재무비율 순위 | ✗ |
| [`FHPST01760000`](endpoints/domestic-ranking/FHPST01760000_국내주식-시간외잔량-순위.md) | 국내주식 시간외잔량 순위 | ✗ |
| [`FHPST01770000`](endpoints/domestic-ranking/FHPST01770000_국내주식-우선주-괴리율-상위.md) | 국내주식 우선주/괴리율 상위 | ✗ |
| [`FHPST01780000`](endpoints/domestic-ranking/FHPST01780000_국내주식-이격도-순위.md) | 국내주식 이격도 순위 | ✗ |
| [`FHPST01790000`](endpoints/domestic-ranking/FHPST01790000_국내주식-시장가치-순위.md) | 국내주식 시장가치 순위 | ✗ |
| [`FHPST01680000`](endpoints/domestic-ranking/FHPST01680000_국내주식-체결강도-상위.md) | 국내주식 체결강도 상위 | ✗ |
| [`FHPST01800000`](endpoints/domestic-ranking/FHPST01800000_국내주식-관심종목등록-상위.md) | 국내주식 관심종목등록 상위 | ✗ |
| [`FHPST01820000`](endpoints/domestic-ranking/FHPST01820000_국내주식-예상체결-상승-하락상위.md) | 국내주식 예상체결 상승/하락상위 | ✗ |
| [`FHPST01860000`](endpoints/domestic-ranking/FHPST01860000_국내주식-당사매매종목-상위.md) | 국내주식 당사매매종목 상위 | ✗ |
| [`FHPST01870000`](endpoints/domestic-ranking/FHPST01870000_국내주식-신고-신저근접종목-상위.md) | 국내주식 신고/신저근접종목 상위 | ✗ |
| [`HHKDB13470100`](endpoints/domestic-ranking/HHKDB13470100_국내주식-배당률-상위.md) | 국내주식 배당률 상위 | ✗ |
| [`FHKST190900C0`](endpoints/domestic-ranking/FHKST190900C0_국내주식-대량체결건수-상위.md) | 국내주식 대량체결건수 상위 | ✗ |
| [`FHKST17010000`](endpoints/domestic-ranking/FHKST17010000_국내주식-신용잔고-상위.md) | 국내주식 신용잔고 상위 | ✗ |
| [`FHPST04820000`](endpoints/domestic-ranking/FHPST04820000_국내주식-공매도-상위종목.md) | 국내주식 공매도 상위종목 | ✗ |
| [`FHPST02340000`](endpoints/domestic-ranking/FHPST02340000_국내주식-시간외등락율순위.md) | 국내주식 시간외등락율순위 | ✗ |
| [`FHPST02350000`](endpoints/domestic-ranking/FHPST02350000_국내주식-시간외거래량순위.md) | 국내주식 시간외거래량순위 | ✗ |
| [`HHMCM000100C0`](endpoints/domestic-ranking/HHMCM000100C0_HTS조회상위20종목.md) | HTS조회상위20종목 | ✗ |

## 해외주식 — 기본시세 (14 endpoints, [raw](raw/해외주식_기본시세.xlsx))

| TR_ID | API 명 | 모의 |
|---|---|---|
| [`HHDFS76200200`](endpoints/overseas-quote/HHDFS76200200_해외주식-현재가상세.md) | 해외주식 현재가상세 | ✗ |
| [`HHDFS76200100`](endpoints/overseas-quote/HHDFS76200100_해외주식-현재가-호가.md) | 해외주식 현재가 호가 | ✗ |
| [`HHDFS00000300`](endpoints/overseas-quote/HHDFS00000300_해외주식-현재체결가.md) | 해외주식 현재체결가 | ✓ |
| [`HHDFS76200300`](endpoints/overseas-quote/HHDFS76200300_해외주식-체결추이.md) | 해외주식 체결추이 | ✗ |
| [`HHDFS76950200`](endpoints/overseas-quote/HHDFS76950200_해외주식분봉조회.md) | 해외주식분봉조회 | ✗ |
| [`FHKST03030200`](endpoints/overseas-quote/FHKST03030200_해외지수분봉조회.md) | 해외지수분봉조회 | ✗ |
| [`HHDFS76240000`](endpoints/overseas-quote/HHDFS76240000_해외주식-기간별시세.md) | 해외주식 기간별시세 | ✓ |
| [`FHKST03030100`](endpoints/overseas-quote/FHKST03030100_해외주식-종목-지수-환율기간별시세-일-주-월-년.md) | 해외주식 종목/지수/환율기간별시세(일/주/월/년) | ✓ |
| [`HHDFS76410000`](endpoints/overseas-quote/HHDFS76410000_해외주식조건검색.md) | 해외주식조건검색 | ✓ |
| [`CTOS5011R`](endpoints/overseas-quote/CTOS5011R_해외결제일자조회.md) | 해외결제일자조회 | ✗ |
| [`CTPF1702R`](endpoints/overseas-quote/CTPF1702R_해외주식-상품기본정보.md) | 해외주식 상품기본정보 | ✗ |
| [`HHDFS76370000`](endpoints/overseas-quote/HHDFS76370000_해외주식-업종별시세.md) | 해외주식 업종별시세 | ✗ |
| [`HHDFS76370100`](endpoints/overseas-quote/HHDFS76370100_해외주식-업종별코드조회.md) | 해외주식 업종별코드조회 | ✗ |
| [`HHDFS76220000`](endpoints/overseas-quote/HHDFS76220000_해외주식-복수종목-시세조회.md) | 해외주식 복수종목 시세조회 | ✗ |

## 해외주식 — 실시간시세 (4 endpoints, [raw](raw/해외주식_실시간시세.xlsx))

| TR_ID | API 명 | 모의 |
|---|---|---|
| [`HDFSASP0`](endpoints/overseas-realtime/HDFSASP0_해외주식-실시간호가.md) | 해외주식 실시간호가 | ✗ |
| [`HDFSASP1`](endpoints/overseas-realtime/HDFSASP1_해외주식-지연호가-아시아.md) | 해외주식 지연호가(아시아) | ✗ |
| [`HDFSCNT0`](endpoints/overseas-realtime/HDFSCNT0_해외주식-실시간지연체결가.md) | 해외주식 실시간지연체결가 | ✗ |
| [`H0GSCNI0`](endpoints/overseas-realtime/H0GSCNI0_해외주식-실시간체결통보.md) | 해외주식 실시간체결통보 | ✓ |

## 해외주식 — 주문/계좌 (18 endpoints, [raw](raw/해외주식_주문_계좌.xlsx))

| TR_ID | API 명 | 모의 |
|---|---|---|
| [`(미국매수) TTTT1002U  (미국매도) TTTT1006U (아시아 국가 하단 규격서 참고)`](endpoints/overseas-order/(미국매수) TTTT1002U  (미국매도) TTTT1006U (아시아 국가 하단 규격서 참고)_해외주식-주문.md) | 해외주식 주문 | ✓ |
| [`(미국 정정·취소) TTTT1004U (아시아 국가 하단 규격서 참고)`](endpoints/overseas-order/(미국 정정·취소) TTTT1004U (아시아 국가 하단 규격서 참고)_해외주식-정정취소주문.md) | 해외주식 정정취소주문 | ✓ |
| [`(미국예약매수) TTTT3014U  (미국예약매도) TTTT3016U   (중국/홍콩/일본/베트남 예약주문) TTTS3013U`](endpoints/overseas-order/(미국 예약주문 취소접수) TTTT3017U (아시아국가 미제공)_해외주식-예약주문접수취소.md) | 해외주식 예약주문접수 | ✓ |
| [`(미국 예약주문 취소접수) TTTT3017U (아시아국가 미제공)`](endpoints/overseas-order/(미국 예약주문 취소접수) TTTT3017U (아시아국가 미제공)_해외주식-예약주문접수취소.md) | 해외주식 예약주문접수취소 | ✓ |
| [`TTTS3007R`](endpoints/overseas-order/TTTS3007R_해외주식-매수가능금액조회.md) | 해외주식 매수가능금액조회 | ✓ |
| [`TTTS3018R`](endpoints/overseas-order/TTTS3018R_해외주식-미체결내역.md) | 해외주식 미체결내역 | ✗ |
| [`TTTS3012R`](endpoints/overseas-order/TTTS3012R_해외주식-잔고.md) | 해외주식 잔고 | ✓ |
| [`TTTS3035R`](endpoints/overseas-order/TTTS3035R_해외주식-주문체결내역.md) | 해외주식 주문체결내역 | ✓ |
| [`CTRP6504R`](endpoints/overseas-order/CTRP6504R_해외주식-체결기준현재잔고.md) | 해외주식 체결기준현재잔고 | ✓ |
| [`(미국) TTTT3039R (일본/중국/홍콩/베트남) TTTS3014R`](endpoints/overseas-order/미국--TTTT3039R--일본-중국-홍콩-베트남--TTTS3014R_해외주식-예약주문조회.md) | 해외주식 예약주문조회 | ✗ |
| [`CTRP6010R`](endpoints/overseas-order/CTRP6010R_해외주식-결제기준잔고.md) | 해외주식 결제기준잔고 | ✗ |
| [`CTOS4001R`](endpoints/overseas-order/CTOS4001R_해외주식-일별거래내역.md) | 해외주식 일별거래내역 | ✗ |
| [`TTTS3039R`](endpoints/overseas-order/TTTS3039R_해외주식-기간손익.md) | 해외주식 기간손익 | ✗ |
| [`TTTC2101R`](endpoints/overseas-order/TTTC2101R_해외증거금-통화별조회.md) | 해외증거금 통화별조회 | ✗ |
| [`(주간매수) TTTS6036U (주간매도) TTTS6037U`](endpoints/overseas-order/(주간매수) TTTS6036U (주간매도) TTTS6037U_해외주식-미국주간주문.md) | 해외주식 미국주간주문 | ✗ |
| [`TTTS6038U`](endpoints/overseas-order/TTTS6038U_해외주식-미국주간정정취소.md) | 해외주식 미국주간정정취소 | ✗ |
| [`TTTS6058R`](endpoints/overseas-order/TTTS6058R_해외주식-지정가주문번호조회.md) | 해외주식 지정가주문번호조회 | ✗ |
| [`TTTS6059R`](endpoints/overseas-order/TTTS6059R_해외주식-지정가체결내역조회.md) | 해외주식 지정가체결내역조회 | ✗ |

---

## 도메인 routing

| 용도 | 모의 사용자 | 실전 사용자 |
|---|---|---|
| 주문·계좌 (`self.base`) | `openapivts.koreainvestment.com:29443` | `openapi.koreainvestment.com:9443` |
| **시세 (`self.quote_base`)** | **`openapi.koreainvestment.com:9443`** ← 항상 실전 | `openapi.koreainvestment.com:9443` |

⚠ doc상 "모의 미지원" 표시여도 quote_base가 실전 도메인이라 동작 가능한 경우 있음. GOTCHAS.md 참조.

## 빠른 사용 가이드

- **해외주식 시초가**: `HHDFS76200200` (모의·실전 둘 다 OK)
- **국내주식 시초가**: `FHKST01010100`의 `stck_oprc`
- **해외주식 현재가**: `HHDFS00000300` (last·base만, OHLC ✗)
- **해외주식 일별 OHLC**: `HHDFS76240000` (모의) / `FHKST03030100` (실전만)
- **국내주식 주문**: `TTTC0011U` (매도) / `TTTC0012U` (매수)
- **해외주식 주문**: `TTTT1002U` (미국 매수) / `TTTT1006U` (미국 매도)