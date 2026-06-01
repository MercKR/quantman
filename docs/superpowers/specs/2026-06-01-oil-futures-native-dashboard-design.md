# 원유선물 전용 대시보드 — 네이티브 재구현 설계

- 날짜: 2026-06-01
- 출처: `heuije/quantman` fork(원본 `v0.9.4-beta`에서 분기, ~64커밋 뒤처짐)의 원유선물 기능을 **참고**해, 원본 `MercKR/quantman` 현재 아키텍처에 맞게 **네이티브로 재구현**한다.
- 선행 작업: fork를 그대로 이식한 `feature/oil-futures` 브랜치(검증 완료, origin push됨)가 존재. 본 설계는 그 그래프트를 **대체**한다.

---

## 1. 의도 / 목표 / 비-목표

**의도.** WTI 원유선물에 대한 **고정 목적 전용 대시보드**. "유가가 임계값 X를 돌파하면 N일 보유" 같은 룰을 격자(grid)로 백테스트하고 결과를 시각화한다.

**핵심 구분 (명시):**
- **전략연구소(IrBuilder)** = 사용자가 자유자재로 전략을 만들고 백테스트·시각화하는 범용 빌더.
- **원유선물** = 사용자가 조립하지 않는, WTI 전용 분석을 보여주는 **고정 대시보드**.

**목표.**
- fork가 제공하던 분석 **전체 패리티**: 가격차트, grid 히트맵(임계값×보유기간, short/long), 돌파 signals, 단일 백테스트(자산곡선·체결·요약), SL/TP 시뮬, 선물 롤오버 시뮬, 워크포워드, 계절성(월·요일), MAE/MFE·streak, 매크로(VIX/DXY) 레짐.
- 데이터·인증·캐싱·디자인을 **원본 컨벤션에 정합**.
- 정식 제품 기능으로 **장기 유지** 가능한 형태.

**비-목표.**
- 전략연구소/IR 엔진에 원유선물을 **편입하지 않는다**(결이 다름 — 단일선물·임계돌파·롤오버).
- 원유 외 상품(천연가스·금 등) 일반화는 범위 밖(데이터는 이미 캐시되어 있으나 본 작업은 WTI만).
- 인트라데이 실시간가는 범위 밖(일배치 마지막 종가 사용).

---

## 2. 가장 큰 결정 — 데이터 소싱

**WTI = yfinance `CL=F` 단일 라이브 소스.** 원본 플랫폼이 이미 `fetch_all()` cron으로 아래를 parquet 원자적 캐시 중이므로, **신규 데이터 수집 코드는 0**이다(소비만 한다):

| 용도 | 캐시 심볼명 | ticker | 등록 위치 |
|---|---|---|---|
| WTI 가격 | `원유선물` | `CL=F` | `data_fetcher.YFINANCE_SYMBOLS` |
| 변동성 | `VIX` | `^VIX` | `MACRO_YF_SYMBOLS` |
| 달러 | `달러지수` | `DX-Y.NYB` | `MACRO_YF_SYMBOLS` |

소비 경로: 서버는 `server/app/data_cache.get_dataset()` → `dict[심볼명, DataFrame]`에서 위 3개를 읽는다(기존 `market.py`가 `"VIX"`를 같은 방식으로 소비 중 — 검증된 패턴).

**fork 대비 폐기되는 것:** 정적 `wti_daily.csv`·`macro_daily.csv`(약 11k줄), `oil_futures/data.py`(CSV 로더), 라우터의 `investing.com` 스크래핑.

**수용한 트레이드오프 (검증 완료):** yfinance `CL=F`는 fork가 쓰던 investing.com 시리즈와 **2017–2026 구간에서 다르다**(롤 타이밍·인접월 스프레드 차이, 2020-04-20 음수정산 −37.63 vs +20.43, 연 ~12일 결측). 즉 백테스트 수치가 heuije 엑셀과 **일치하지 않는다**(틀린 게 아니라 다른 시리즈). 플랫폼 정책(US=yfinance 단일 라이브, 정적 CSV 지양)과 정합하므로 채택.

**필수 후속 정제(데이터 어댑터):** 임계값-돌파 로직이 깨지지 않도록
1. 비양수 종가(예: 2020-04-20 음수) 행 제거,
2. 결측 거래일 처리(거래일 인덱스 정렬, 필요한 분석에서 ffill 금지 — 결측은 결측으로),
3. front-month 롤 점프는 그대로 둔다(현물 아님을 UI에 명시).

---

## 3. 아키텍처 — 재사용 / 재배선 / 폐기 / 신규

| 구분 | 대상 |
|---|---|
| ✅ 재사용(로직 거의 그대로) | `core/quant_core/oil_futures/{backtest,signals,metrics,optimizer}.py`, 웹 `pages/OilFutures.tsx` + `api.ts`의 `oilApi`(이미 공유 `req<T>` 사용) |
| 🔧 재배선 | 서버 `routers/oil_futures.py` — 데이터 입력을 `get_dataset()`로 교체, 스크래핑 제거, 인증 추가, 캐시 버전키 연동 |
| ❌ 폐기 | `wti_daily.csv`, `macro_daily.csv`, `oil_futures/data.py`, `oil_futures/cli.py`(rich 의존), investing.com 스크래핑, `.xlsx`(소스 데이터, 미포함) |
| ➕ 신규(소량) | (a) 캐시 시리즈→백테스트 입력 어댑터 + 정제, (b) 라우터 인증 의존성, (c) 합성 테스트 픽스처 |

### 3.1 Core (`quant_core.oil_futures`)
- `backtest.py`·`signals.py`·`metrics.py`·`optimizer.py`는 **순수 함수**(입력=가격 DataFrame). 로직 변경 없음.
- `data.py`(CSV 로더) **삭제**. 대신 호출자(서버)가 `get_dataset()["원유선물"]`을 정제해 DataFrame을 주입.
- `cli.py` **삭제**(제품은 웹; rich 의존 제거 → 코어 deps 추가 불필요).
- `pyproject.toml`: `packages`에 `quant_core.oil_futures` 추가(서브패키지 인식). 데이터 파일 package-data 불필요(더 이상 CSV 미포함).

### 3.2 Server (`routers/oil_futures.py`)
- 9개 endpoint(`/oil-futures/{data-info,latest-price,prices,grid,signals,backtest,walkforward,seasonality,macro-context}`) 유지.
- `latest-price` = 캐시 마지막 종가(+ 직전 대비 변화). **investing.com 스크래핑 제거**, `requests` 의존 제거.
- 모든 endpoint에 `Depends(get_current_user)` 추가(타 라우터 정합, 무거운 grid/backtest 공개노출 방지).
- 캐싱: `lru_cache` 산발 사용 → `data_cache.get_version()` 버전키 기반(데이터 갱신 시 자동 무효화)으로 정합. 무거운 grid/backtest 결과는 (입력 파라미터 + 데이터 버전) 키로 캐시.
- 매크로 컨텍스트: `VIX`·`달러지수` 캐시 시리즈로 레짐·상관 계산.

### 3.3 Web
- `OilFutures.tsx`·`oilApi`·라우트(`/oil-futures`)·네비("원유 분석") 재사용.
- `index.css`의 원유 전용 +390줄을 `DESIGN.md` 토큰(색·간격·타이포)과 1회 정합 패스. 오프-시스템 색/간격 제거.
- recharts 이미 의존성에 존재(버전 동일) — package.json 변경 없음.

---

## 4. 데이터 흐름

```
fetch_all() cron ── (기존) ──▶ parquet 캐시(원유선물·VIX·달러지수)
                                      │
server data_cache.get_dataset() ◀─────┘   (버전키 get_version)
        │  dict[심볼명, DataFrame]
        ▼
routers/oil_futures.py
   ├─ 정제 어댑터(비양수 제거·거래일 정렬)
   ├─ quant_core.oil_futures.{signals,backtest,optimizer,metrics}
   └─ 인증(Depends get_current_user) + 버전키 캐시
        │  JSON
        ▼
web: oilApi(req<T>) ──▶ OilFutures.tsx (recharts 시각화)
```

---

## 5. 테스트 / 검증

- **단위(core):** `test_oil_futures.py`를 CSV 의존에서 **소형 합성 가격 픽스처**로 전환 → 오프라인·결정적. 백테스트·signals·metrics·optimizer 회귀 보장.
- **데이터 어댑터:** 음수·결측·롤 점프가 포함된 합성 시리즈로 정제 동작 단위 테스트.
- **서버:** 라우터 인증(미인증 401), endpoint 응답 스키마, 캐시 무효화(버전 변경 시 재계산) 테스트.
- **통합·검증 신호:** core 테스트 통과, 서버 라우터 import + 인증 동작, 웹 `tsc -b && vite build` 통과, 브라우저로 "원유 분석" 탭 렌더·차트 표시 확인(로그인 후).

---

## 6. 그래프트(`feature/oil-futures`)와의 관계 / 마이그레이션

- 기존 그래프트 브랜치는 **참고용으로 보존**하되 병합하지 않는다(데이터 군더더기 포함).
- 네이티브 작업은 별도 브랜치(예: `feature/oil-futures-native`)에서 현재 `main` 위에 진행.
- 그래프트에서 가져올 자산: 4개 core 분석 모듈 + 웹 페이지/`oilApi` + CSS(정합 후). 그래프트에서 **버릴 것**: CSV 2종, `data.py`, `cli.py`, 스크래핑 코드.

---

## 7. 리스크 / 미해결

- **R1 데이터 시리즈 변경:** yfinance 채택으로 백테스트 수치가 heuije 엑셀과 다름(수용 결정됨). UI에 "데이터: Yahoo CL=F front-month" 출처·한계(롤 점프) 표기 권장.
- **R2 Railway 메모리:** grid/walk-forward 계산이 무거움(fork에 OOM 이력). 버전키 캐시 + grid 파라미터 상한으로 완화. 배포 후 Railway 로그 모니터링.
- **R3 결측·롤:** 정제 정책(비양수 제거·결측 유지)이 일부 분석(계절성·MAE/MFE)의 표본을 바꿀 수 있음 — 테스트 픽스처로 경계 확인.
- **R4 캐시 의존:** 데이터가 아직 한 번도 수집되지 않은 환경에서 `원유선물` 키 부재 시 graceful 메시지(빈 상태) 필요 — fallback 데이터는 두지 않음(원칙: 단일 소스).

---

## 8. 작업 범위 요약 (구현 계획 입력)

1. core: `data.py`·`cli.py` 삭제, 분석 4모듈 정리, 데이터 입력 인터페이스 정의.
2. 데이터 어댑터: `get_dataset` 시리즈 → 정제 → 백테스트 입력.
3. server: 라우터 재배선(dataset 소비) + 인증 + 버전키 캐시 + 스크래핑/`requests` 제거.
4. web: 페이지/`oilApi` 이식 + CSS 디자인 정합 + 출처 표기.
5. test: 합성 픽스처 전환 + 어댑터·인증·캐시 테스트.
6. 검증: core/서버/웹 빌드 + 브라우저 확인.
