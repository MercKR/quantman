## 주요 변경 — cycle 시작 지연 본질 fix (Fix A + B1)

2026-05-29 미장·국장 catch-up 모두에서 cycle이 **dataset 로드에 5분+** 묶여 발주가
시장 개장 후로 밀리는 현상 관측. 두 본질 원인을 해결.

### 🐞 Fix B1 — load_dataset 전체 4468종목 → 실제 사용 종목만 (5분 → ~2초)

**근본 원인**: `runner.run_cycle`·`intraday_loop`이 매번 `qc.load_dataset(with_indicators=True)`
호출 → `load_all()`로 managed universe 전체(macro 51 + KRX 3577 + 해외 512 ≈ **4468**)
parquet 읽기 + `compute_all()`로 4468종목 지표(ATR·RSI 등) 계산. 실측 5분+.
v0.9.6 auto-register가 bundle 전체를 universe에 등록하면서 부푼 것.

**로컬이 실제 필요한 종목** (검증):
- **매수**: `_enter_from_preview`가 신호 재평가 **안 함** (server preview가 평가 완료).
  candidate Close만 필요 → 전략 타겟/후보.
- **매도**: `_evaluate_exit → build_signal_mask`가 조건 참조 종목(예: `종목 ≥ S&P500`의
  S&P500)을 `data[symbol]`로 접근. 보유분 자기 정의의 조건에서 참조 종목 추출 필요.

**변경**:
- [core/quant_core/dataset.py](../core/quant_core/dataset.py) — `load_dataset_for(symbols, with_indicators)`
  신규. 요청 종목만 읽기+지표. `load_dataset`(전체)은 server 백테스트·preview용 유지.
- [core/quant_core/analysis.py](../core/quant_core/analysis.py) — `referenced_symbols(conditions)`
  신규. 조건 operand에서 외부 참조 종목 추출 (SELF placeholder·constant 제외, 그룹 재귀).
- [localapp/dataset_scope.py](localapp/dataset_scope.py) — `needed_symbols(strategies, candidates, ledger)`
  = `ALL_SYMBOLS(~51) ∪ 전략타겟/후보 ∪ 보유 ∪ 조건참조`. macro 전체를 안전망으로
  항상 포함 — 지수 참조를 한 종목이라도 놓쳐 빈 mask(신호 미발동)되는 fund-safety
  위험 차단.
- [localapp/runner.py](localapp/runner.py) — load_dataset를 broker·preview 이후로 옮겨
  needed 계산 후 `load_dataset_for`. (보유 ledger·후보를 알아야 scope 계산 가능)
- [localapp/intraday_loop.py](localapp/intraday_loop.py) — loop start + ks-trigger cycle
  둘 다 `load_dataset_for`(보유 + 조건참조 + macro).

**검증**:
- `referenced_symbols` 단위 5케이스 (SELF 제외·constant 제외·중첩 그룹·history operand)
- `load_dataset_for` 단위 2케이스 (scope·미존재 skip·지표 계산·raw 모드)
- 실데이터: 5종목 0.31초 / 63종목(실제 needed 규모) **2.22초** (vs 전체 4468 5분+)
- needed_symbols 실데이터: 타겟·매수조건 S&P500·보유·매도조건 KOSPI200선물·macro 51 모두 포함 확인
- **golden backtest 15 passed** — server 백테스트 무영향 (load_dataset 불변)

### 🐞 Fix A — dataset 동시 다운로드 race 직렬화

**근본 원인**: 기동 시 startup `dataset-initial` 스레드 + catch-up cycle의
`refresh_market_data`가 **동시에** 같은 4468 parquet를 같은 디렉터리에 다운로드·추출
(2026-05-29 02:37·02:38 두 번 적용, 10:27도 동일). 대역폭 2배 + 추출 중 부분
기록 parquet를 load가 읽을 손상 위험.

**변경**: [localapp/datafetch.py](localapp/datafetch.py)
- `refresh_market_data`를 `_REFRESH_LOCK`(threading.Lock)으로 직렬화.
- 두 번째 호출은 첫 다운로드 완료 대기 후 server ETag 304(별도 배포됨)로 즉시 skip.

### 4원칙 자가검토

- **근본 원인 ✓** — 5분 지연의 원인(전체 universe 계산)을 제거. 증상(시각 앞당기기)
  봉합 아님. 사용자가 "시각 앞당기기"보다 "원인 해결"을 명시 요구 → B1으로 응답.
- **Over-eng 금지 ✓** — `load_dataset`(server) 불변, 로컬만 scoped. 추가 캐시 계층 없음.
- **Overthinking 금지 ✓** — needed 집합 계산은 단순 합집합. macro 안전망으로 참조
  추출 누락 리스크까지 흡수 (이중 가드 아님 — 추출은 정확하나 안전 마진).
- **검증 ✓** — 단위·실데이터·golden 모두 통과. cycle 5분 → 2초 실측.

### 사전 검토에서 폐기한 초기안

초기 "held ∪ candidates만 scope"는 **fund-safety 버그**였음 — 매도 조건이 참조하는
S&P500 등이 빠져 `build_signal_mask`가 빈 mask → 신호 기반 매도 미발동. 사전 코드
리뷰로 발견해 `referenced_symbols` 추출 + macro 안전망으로 교정.

### 내부 변경

**[core/quant_core/dataset.py]** `load_dataset_for` 추가, `_parquet_path` import.
**[core/quant_core/analysis.py]** `referenced_symbols` 추가.
**[core/quant_core/\_\_init\_\_.py]** `load_dataset_for`·`referenced_symbols`·`ALL_SYMBOLS` export.
**[localapp/dataset_scope.py]** 신규 — `needed_symbols`·`_refs`.
**[localapp/runner.py]** run_cycle 재순서 + scoped 로드.
**[localapp/intraday_loop.py]** loop start + ks-trigger scoped 로드.
**[localapp/datafetch.py]** `_REFRESH_LOCK` 직렬화.
**[localapp/\_\_init\_\_.py]** 0.9.15-beta → 0.9.16-beta.
**[tests/test_dataset_scope.py]** 신규 — referenced_symbols·load_dataset_for 회귀 7 테스트.

PC 절전(sleep)이 5/29 누락의 1차 원인 — 이 release는 cycle 실행 품질(개장 전 완료)을
회복하지만, **장 시간 PC 절전 해제는 사용자 설정 필요** (절전 중엔 어떤 자동매매도 불가).
