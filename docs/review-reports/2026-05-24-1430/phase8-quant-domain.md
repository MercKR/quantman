# Phase 8 — System Trading 도메인 + 자동매매 가이드라인 baseline

## 1. 골든 백테스트

```
pytest tests/golden_backtest.py -v → 15 passed, 1 skipped, 2 warnings in 397.97s
```

직전(2108) 동일 — **회귀 0** ✅. Phase 47~49 변경 후에도 백테스트 엔진 안정.

## 2. QUANT_DOMAIN_CHECKLIST 7 카테고리 — 직전(2108) 대비

| # | 카테고리 | 2108 | 1430 | 변화 |
|---|---|---|---|---|
| 1 | 백테스트 정확성 (look-ahead, 슬리피지, 배당, 분할) | ✅ | ✅ | 0 |
| 2 | 시그널→주문 idempotency (Phase 47 사이징 통합) | ✅ | ✅ | 0 |
| 3 | 모의↔실전 일관성 | ✅ | ✅ | 0 |
| 4 | 리스크 관리 (kill switch, drawdown, 단일종목 한도) | ✅ | **✅★** | **Phase 48 P1 보강** — 일시정지·KIS health·슬리피지·일일한도 |
| 5 | KIS↔ledger 정합성 | ✅ | ✅ | 0 |
| 6 | 자격증명 분리 | ✅ | ✅ | 0 (SC-1은 별도 — JWT 길이) |
| 7 | 한국 시장 특수성 (시간·휴장·호가) | ✅ | **⚠️★** | **VI·CB·권리락·배당락 미구현 surface** |

### 변화 상세

**카테고리 4 — Phase 48 P1 보강 ✅★**
- P1-A 전략 레벨 즉시 일시정지 (mode=draft 1탭, 보유 종목은 청산 규칙 계속)
- P1-B KIS maintenance window 자동 인식 (토 17h ~ 월 07h, 평일 03-06h skip)
- P1-C 슬리피지 임계 초과 알림 (avg_bps > 임계 + 표본 ≥5 + cooldown 1h)
- P1-D 일일 거래 한도 (turnover_krw + trade_count, 0=비활성)
- P0-4 거래정지·관리종목 자동 차단 (1차 dataset metrics + 2차 KIS 거부)

**카테고리 7 — VI·CB·권리락·배당락 미구현 ⚠️★**
- `local/localapp/` 에 VI(volatility interruption)·CB(circuit breaker) 0 매치
- 권리락·배당락 캘린더 없음 — KRX 코퍼레이트 액션 cron 미구현
- 위 두 항목 commit body 7c4bac3에 "VI·CB는 다음 cycle" 명시
- 표면 영향: VI 발동 시 KIS 거래 자동 정지 (broker level 차단) — 그러나 **클라이언트 인지 없음** = 신호 fire인데 발주 실패 lol → trader가 이유 모르고 retry. 사용자 UX 손상.

## 3. 자동매매 가이드라인 baseline (메모리 + Phase 48 baseline 매핑)

이전 cycle Phase 48에서 도입된 12 disclaimer/safeguards 항목 별 현황:

| # | 항목 | 구현 | 상태 |
|---|---|---|---|
| G-01 | 약관·개인정보처리방침·이용안내 페이지 | `web/src/pages/Legal.tsx` | ✅ |
| G-02 | 가입 시 3중 동의 체크박스 (약관·개인정보·자문아님) | `Login.tsx` disabled 게이트 | ✅ |
| G-03 | 사이드바·푸터 법적 페이지 링크 | `Layout.tsx` 사이드바 푸터 | ✅ |
| G-04 | 전략 빌더 self-direction 배너 ("자문 아님") | `Backtest.tsx` 상단 | ✅ |
| G-05 | 실전 승격 모달 자문 재고지 | `Strategies.tsx` PromoteModal step 2 | ✅ |
| G-06 | 백테스트 NFA 2-29 disclaimer (hypothetical-banner) | `Backtest.tsx` ResultTab | ✅ |
| G-07 | 거래정지·관리종목 자동 차단 (1차 dataset + 2차 KIS) | `trader.py:_try_buy_one_symbol` | ✅ |
| G-08 | VI 발동 자동 차단 | — | ❌ **미구현** |
| G-09 | CB 발동 자동 차단 | — | ❌ **미구현** |
| G-10 | KIS rate limit throttle (1초 10건/20건) | `kis_broker.py` `_calls` 자체 페이싱 | ✅ |
| G-11 | KIS maintenance window cycle skip | `trader._in_kis_maintenance_window` | ✅ |
| G-12 | 일일 거래 한도 (turnover·count) | `UserSettings.daily_turnover_limit_krw` | ✅ |
| G-13 | 슬리피지 임계 알림 | webhook | ✅ |
| G-14 | 5년 로그 보존 (자본시장법 + FINRA RN 15-09) | `order_log.py` docstring 명시 (실제 retention 정책은 운영 영역) | ⚠️ |
| G-15 | 카피트레이딩 미제공 정책 | Backtest 마켓플레이스 placeholder | ✅ |
| G-16 | 권리락·배당락 ex-date 처리 | — | ❌ **미구현** |
| G-17 | 부분 체결 / 미체결 대기열 (실전 엔진) | — | ⚠️ **부분** (단일 종목·전액 가정) |
| G-18 | 섹터 분산 한도 | — | ❌ **미구현** (Q-02 이월) |
| G-19 | 백테스트 vs 라이브 bps drift 가시화 | — | ⚠️ **측정만 (UI 노출 부재, Q-03 이월)** |

종합 baseline 충족률: **12/19 ✅ + 3 ⚠️ + 4 ❌ ≈ 71%** 

가이드라인 paste 도착 시 위 매핑을 paste 본문과 1:1 재대조해 G-XX 보강.

## 4. 발견 결함 / 도메인 갭

### High

**DM-1 [High]** VI·CB 자동 차단 미구현 (G-08·G-09)
- 위치: `local/localapp/` (검증 grep 0 매치)
- 현재: VI 발동 종목에 매수 시도 시 KIS broker가 거부 (2차 안전망). 클라이언트는 이유 모르고 retry 가능 → KIS rate limit 부담 + 사용자 혼란.
- 정확한 baseline: KRX 정보데이터시스템 API로 VI·CB 상태 polling → 클라이언트 직접 차단.
- 의존: 사용자 KRX API 키 발급 필요. **사용자 결정 게이트**.

**DM-2 [High]** 권리락·배당락 캘린더 미구현 (G-16)
- 위치: dataset / trader
- 현재: dataset이 FDR adjusted 가격을 받으므로 백테스트 자동 OK. 라이브 KIS도 자동 평단 조정. 다만 **갭 발생 시 사용자 인지 없음** + ex-date 매수 차단 없음.
- best practice 조사 완료 (memory). 구현: KRX 코퍼레이트 액션 cron + ex-date 알림 + (옵션) ex-date 매수 차단.

### Medium

**DM-3 [Medium]** 섹터 분산 한도 미구현 (Q-02 이월, G-18)
- 직전 cycle 그대로. 단일종목 한도(`max_position_pct`)는 있으나 섹터 묶음 분산 없음.
- 입력: dataset에 섹터 분류 필요 (FDR·KRX).

**DM-4 [Medium]** 백테스트 vs 라이브 bps drift 측정만 — UI 노출 부재 (Q-03 이월, G-19)
- Phase 48 P1-C로 슬리피지 알림 도입됨. 그러나 backtest cost 가정 vs 라이브 실 측정의 누적 비교 대시보드는 부재.

**DM-5 [Medium]** 부분 체결 / 미체결 큐 처리 한정 (G-17)
- 백테스트: 단일 종목·전액 가정 (부분 체결 없음).
- 라이브 (`local/`): KIS 부분 체결 응답 시 처리는 broker layer에 있을 가능성 — 미검증.

## 5. 새 surface (Phase 47~49 도입)

| Surface | 위치 | 검증 |
|---|---|---|
| 매수액 4지 모드 (정률·정액·균등·ATR) | `core/quant_core/exec_defaults.py:sizing_mode` + UI sizing-cards | ✅ |
| 매수액 수정자 (×N modifier) | `ExecutionPolicy.size_modifiers` + SizeModifiersPanel | ✅ |
| 분할매수 N차 + 평단 가중평균 | `ExecutionPolicy.split_buy` + SplitBuyPanel | ✅ |
| 시장가 매수 (use_limit=false) | Phase 49 — `trader.py:480` 분기 + BuyPricePanel | ✅ (해외 종목 자동 limit 변환 D49-02) |
| 자동매매 가이드라인 12 baseline | Phase 48 P0/P1/P2 | ✅★ (~71% 충족, 미구현 4건) |

## 6. 4원칙 자기검토 (Phase 8)

| 원칙 | 자기검토 |
|---|---|
| 근본원인 | DM-1/DM-2는 외부 데이터 의존 — 사용자 결정 게이트 surface ✅ |
| Over-eng | 섹터 한도 자동 도입 없음 (게이트) ✅ |
| Over-think | 19항목 baseline 매핑 표로 single source ✅ |
| 검증된 해결책 | golden 15 pass + 명령 출력 + grep 결과 인용 ✅ |

## 7. Phase 9 전달

- **DM-1** VI·CB 자동 차단 (High, 사용자 결정 게이트)
- **DM-2** 권리락·배당락 캘린더 (High, 외부 KRX API 의존)
- **DM-3** 섹터 한도 (Medium, dataset 보강 의존)
- **DM-4** 백테스트 vs 라이브 bps 대시보드 (Medium)
- **DM-5** 부분 체결 / 미체결 큐 (Medium)
- 회귀: 0
