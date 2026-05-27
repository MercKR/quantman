# KIS API Knowledge Base Changelog

발견·fix 시계열. release version과 연동.

## 2026-05-28

### KB 확장 — 7 카테고리 132 endpoint 완전 변환 ✓
- 국내주식 기본시세 (22), 실시간시세 (29), 주문/계좌 (23), 순위분석 (22)
- 해외주식 기본시세 (14), 실시간시세 (4), 주문/계좌 (18)
- 모든 endpoint markdown 정상 생성, INDEX.md 132/132 매칭
- 사용자 제공 7 xlsx 모두 `raw/` 보존

### KB 초기 구축 (오늘 KST 02:00)
- `docs/kis-api/` 신설
- 해외주식 기본시세 14 endpoint Excel → markdown 자동 변환
- INDEX.md, GOTCHAS.md, README.md 작성
- CLAUDE.md에 API 작업 룰 추가 (8번 섹션)

### 오늘 release와 연동된 발견 (시간순)

| 시각 (KST) | 발견 | release |
|---|---|---|
| 21:42 | `import websocket` 누락 (requirements.txt) | [v0.9.2-beta](../../local/RELEASE_NOTES_v0.9.2-beta.md) |
| 22:32 | Windows updater race condition + macOS Gatekeeper friction | [v0.9.3-beta](../../local/RELEASE_NOTES_v0.9.3-beta.md) |
| 22:48 | catch-up 회귀 (NameError + TypeError) | [v0.9.4-beta](../../local/RELEASE_NOTES_v0.9.4-beta.md) |
| 23:53 | **Transfer-Encoding chunked + r.raw 충돌** (GOTCHA #4) | [v0.9.5-beta](../../local/RELEASE_NOTES_v0.9.5-beta.md) |
| 00:08 | server preview의 KST cutoff 결함 (별도 server fix) | server commit f10c50b |
| 00:30 | **client load_all universe 화이트리스트 ↔ bundle 단절** | [v0.9.6-beta](../../local/RELEASE_NOTES_v0.9.6-beta.md) |
| 01:19 | **HHDFS00000300 응답에 open 없음** (GOTCHA #1) | [v0.9.7-beta](../../local/RELEASE_NOTES_v0.9.7-beta.md) |

7시간 동안 7번 release. 매 단계마다 한 layer씩 벗겨가며 진짜 진범에 도달.

핵심 교훈:
- **공식 doc + 실측 둘 다 필요**: doc은 출발점, 실측이 fact (HHDFS00000300의 open 필드 X 같은 함정은 doc spec에 명시 안 됨)
- **layer 단절을 의심**: server bundle → client load_all 화이트리스트 같은 sync 결함은 단일 layer 디버그론 안 보임
- **시간대 cutoff은 시장별로 다름**: KST 자정 vs US EDT 16:00 종가 cutoff 분리 필수

### 핵심 사용 endpoint 사용자별 매핑

우리 로컬앱이 사용하는 KIS endpoint와 knowledge base 위치:

| 우리 코드 | endpoint | KB 위치 |
|---|---|---|
| `KisBroker._open_overseas` | HHDFS76200200 | [endpoints/overseas-quote/HHDFS76200200_*](endpoints/overseas-quote/) |
| `KisBroker._price_overseas` | HHDFS00000300 | [endpoints/overseas-quote/HHDFS00000300_*](endpoints/overseas-quote/) |
| `KisBroker._open_domestic`·`_price_domestic` | FHKST01010100 | [endpoints/domestic-quote/FHKST01010100_*](endpoints/domestic-quote/) |
| KIS 매수 발주 | TTTC0012U | [endpoints/domestic-order/](endpoints/domestic-order/) |
| KIS 매도 발주 | TTTC0011U | [endpoints/domestic-order/](endpoints/domestic-order/) |
| KIS 잔고조회 | TTTC8434R | [endpoints/domestic-order/](endpoints/domestic-order/) |
| 해외주식 매수 | TTTT1002U | [endpoints/overseas-order/](endpoints/overseas-order/) |
| 해외주식 매도 | TTTT1006U | [endpoints/overseas-order/](endpoints/overseas-order/) |
| 체결통보 WebSocket | H0STCNI0 | [endpoints/domestic-realtime/H0STCNI0_*](endpoints/domestic-realtime/) |
| 시세 WebSocket | H0STCNT0 | [endpoints/domestic-realtime/H0STCNT0_*](endpoints/domestic-realtime/) |
