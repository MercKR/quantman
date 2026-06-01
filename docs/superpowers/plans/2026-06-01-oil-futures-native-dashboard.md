# 원유선물 전용 대시보드 (네이티브) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** heuije fork의 WTI 원유선물 분석을 원본 아키텍처(yfinance 캐시 데이터층·인증·디자인)에 맞춰 네이티브 전용 대시보드로 재구현한다.

**Architecture:** core 분석 4모듈(backtest/signals/metrics/optimizer)은 순수 함수라 그대로 재사용한다. CSV 로더·CLI·investing.com 스크래핑은 폐기하고, 데이터는 플랫폼이 이미 캐시하는 `원유선물`(CL=F)·`VIX`·`달러지수` parquet 시리즈를 `data_cache.get_raw_dataset()`로 소비한다. 서버 라우터는 데이터 입력만 교체하고 인증 게이트·버전키 캐시를 더한다. 웹 페이지는 재사용하고 디자인 토큰만 정합한다.

**Tech Stack:** Python(FastAPI, pandas) / React+TS+Vite(recharts) / pytest.

**선행 기준 브랜치:** 현재 `origin/main`(검증 시점 `ff54e09` 이후 최신). 그래프트 브랜치 `feature/oil-futures`(검증·push 완료)는 **재사용 코드의 출처**로만 쓴다.

**스펙:** `docs/superpowers/specs/2026-06-01-oil-futures-native-dashboard-design.md`

---

## File Structure

생성/수정 파일과 책임:

- `core/quant_core/oil_futures/__init__.py` — 패키지 공개 API. `load_wti` 제거, `prepare_wti` 추가.
- `core/quant_core/oil_futures/data.py` — **책임 변경**: "CSV 로드" → "원시 OHLCV 프레임 정제"(`prepare_wti`). 순수 함수, server 비의존.
- `core/quant_core/oil_futures/{backtest,signals,metrics,optimizer}.py` — 재사용(변경 없음).
- `core/quant_core/oil_futures/cli.py` — **삭제**(rich 의존, 제품 불필요).
- `core/tests/test_oil_futures.py` — CSV 의존 → 합성 픽스처.
- `core/tests/test_oil_futures_data.py` — **신규**: `prepare_wti` 정제 단위 테스트.
- `server/app/routers/oil_futures.py` — `_df()`/`_macro_df()`/`latest_price` 데이터원 교체, 스크래핑 제거, 인증 게이트.
- `server/app/main.py` — 라우터 등록(import + include).
- `core/pyproject.toml` — `packages`에 `quant_core.oil_futures`.
- `web/src/pages/OilFutures.tsx`, `web/src/api.ts`, `web/src/App.tsx`, `web/src/components/Layout.tsx`, `web/src/index.css` — 재사용 + 출처 표기 + 디자인 정합.
- **폐기(미포함)**: `core/data/wti_daily.csv`, `core/data/macro_daily.csv`.

---

## Task 1: 네이티브 브랜치 생성 + 재사용 자산 가져오기

재사용 코드는 검증된 그래프트(`feature/oil-futures`)에서 가져오되, 폐기 대상(data.py 옛버전·cli.py·CSV)은 제외한다.

**Files:**
- Create(브랜치): `feature/oil-futures-native`
- Bring over: core 분석 4모듈, 웹 페이지/통합 edits

- [ ] **Step 1: 최신 main에서 브랜치 생성**

```bash
git fetch origin
git checkout -b feature/oil-futures-native origin/main
```

- [ ] **Step 2: 재사용 core 분석 모듈 가져오기 (data.py·cli.py 제외)**

```bash
git checkout feature/oil-futures -- \
  core/quant_core/oil_futures/__init__.py \
  core/quant_core/oil_futures/backtest.py \
  core/quant_core/oil_futures/signals.py \
  core/quant_core/oil_futures/metrics.py \
  core/quant_core/oil_futures/optimizer.py \
  server/app/routers/oil_futures.py \
  web/src/pages/OilFutures.tsx
```

- [ ] **Step 3: 웹 통합 edits + api.ts 블록 가져오기**

```bash
git checkout feature/oil-futures -- \
  web/src/api.ts web/src/App.tsx \
  web/src/components/Layout.tsx web/src/index.css
```

- [ ] **Step 4: 폐기 대상이 안 따라왔는지 확인 (CSV·cli.py·data.py 옛버전)**

Run: `git status --short && ls core/data/ 2>/dev/null | grep -E "wti_daily|macro_daily" || echo "CSV 없음 OK"`
Expected: oil_futures에 `cli.py` 없음, `core/data/wti_daily.csv`·`macro_daily.csv` 없음. (Step 2에서 명시하지 않았으므로 안 따라옴)

- [ ] **Step 5: 커밋**

```bash
git add -A
git commit -m "chore(oil-futures): 네이티브 브랜치 — 재사용 분석모듈+웹 가져오기(CSV/CLI 제외)"
```

---

## Task 2: `prepare_wti` — 원시 프레임 정제 (TDD)

옛 `data.py`(CSV 로더)를 순수 정제 함수로 대체한다. 입력은 `get_raw_dataset()["원유선물"]`(Date 인덱스, 대문자 OHLCV) 같은 원시 프레임.

**Files:**
- Modify(전체 교체): `core/quant_core/oil_futures/data.py`
- Test: `core/tests/test_oil_futures_data.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# core/tests/test_oil_futures_data.py
import pandas as pd
import numpy as np
import pytest
from quant_core.oil_futures.data import prepare_wti


def _raw():
    # Date 인덱스 + 대문자 컬럼(플랫폼 캐시 형식), 비정렬 + 음수 + NaN 포함
    idx = pd.to_datetime(["2020-04-21", "2020-04-20", "2020-04-17", "2020-04-22"])
    return pd.DataFrame(
        {"Open": [10.0, 18.0, 25.0, 14.0],
         "High": [13.0, 20.0, 26.0, 16.0],
         "Low":  [6.0, -40.3, 24.0, 12.0],
         "Close":[11.0, -37.6, 25.0, 13.0],   # 2020-04-20 음수
         "Volume":[1.0, 2.0, 3.0, np.nan]},
        index=idx,
    )


def test_prepare_wti_normalizes_and_sorts():
    out = prepare_wti(_raw())
    assert list(out.columns)[:5] == ["date", "open", "high", "low", "close"]
    assert out["date"].is_monotonic_increasing
    assert str(out["date"].dtype).startswith("datetime")


def test_prepare_wti_drops_nonpositive_close():
    out = prepare_wti(_raw())
    assert (out["close"] > 0).all()
    assert pd.Timestamp("2020-04-20") not in set(out["date"])


def test_prepare_wti_accepts_lowercase_date_column():
    raw = _raw().reset_index().rename(columns={"index": "Date"})
    out = prepare_wti(raw)
    assert len(out) == 3  # 음수 1건 제거
```

- [ ] **Step 2: 실패 확인**

Run: `cd core && python -m pytest tests/test_oil_futures_data.py -q`
Expected: FAIL (`prepare_wti` 미정의 / 옛 data.py는 load_wti만 있음)

- [ ] **Step 3: data.py 전체 교체 (prepare_wti 구현)**

```python
# core/quant_core/oil_futures/data.py
"""WTI 원시 OHLCV 프레임 정제.

입력: 플랫폼 데이터 캐시(get_raw_dataset)의 원시 프레임 — Date 인덱스(또는 date/Date
컬럼) + OHLCV(대/소문자 무관). 출력: 백테스트 엔진이 기대하는 표준 형식
(date 컬럼[datetime, ASC] + open/high/low/close/volume[float]).

정제: 비양수 종가(예: 2020-04-20 CL=F −37.63 음수정산) 제거, 가격 NaN 행 제거.
front-month 롤 점프는 보존(현물 아님 — UI에서 명시). fallback 데이터는 두지 않는다.
"""
from __future__ import annotations

import pandas as pd

REQUIRED = ("open", "high", "low", "close")


def prepare_wti(raw: pd.DataFrame) -> pd.DataFrame:
    if raw is None or len(raw) == 0:
        raise ValueError("WTI 원시 데이터 비어있음")

    df = raw.copy()
    # Date 인덱스를 컬럼으로
    if "date" not in (c.lower() for c in df.columns):
        df = df.reset_index()
    # 컬럼명 소문자 정규화
    df.columns = [str(c).lower() for c in df.columns]
    if "index" in df.columns and "date" not in df.columns:
        df = df.rename(columns={"index": "date"})

    missing = set(REQUIRED) - set(df.columns)
    if missing:
        raise ValueError(f"WTI 필수 컬럼 누락: {missing}")
    if "volume" not in df.columns:
        df["volume"] = float("nan")

    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    for c in REQUIRED:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=list(REQUIRED))
    df = df[df["close"] > 0]                       # 음수·0 정산 제거
    df = df.sort_values("date").reset_index(drop=True)
    return df[["date", "open", "high", "low", "close", "volume"]]
```

- [ ] **Step 4: 통과 확인**

Run: `cd core && python -m pytest tests/test_oil_futures_data.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: 커밋**

```bash
git add core/quant_core/oil_futures/data.py core/tests/test_oil_futures_data.py
git commit -m "feat(oil-futures): prepare_wti — CSV로더 대체, 캐시 프레임 정제(음수·NaN 제거)"
```

---

## Task 3: 패키지 공개 API 갱신

`__init__.py`가 옛 `load_wti`를 export하므로 import 에러가 난다. `prepare_wti`로 교체.

**Files:**
- Modify: `core/quant_core/oil_futures/__init__.py`

- [ ] **Step 1: import 실패 확인**

Run: `cd core && python -c "import quant_core.oil_futures"`
Expected: FAIL (`cannot import name 'load_wti' from ... data`)

- [ ] **Step 2: __init__.py의 data import 줄 교체**

`core/quant_core/oil_futures/__init__.py`에서:

```python
from .data import load_wti
```
를 다음으로 교체:
```python
from .data import prepare_wti
```
그리고 같은 파일의 `__all__`(있다면)에서 `"load_wti"` → `"prepare_wti"`로 교체.

- [ ] **Step 3: import 통과 확인**

Run: `cd core && python -c "import quant_core.oil_futures as o; print(hasattr(o, 'prepare_wti'))"`
Expected: `True`

- [ ] **Step 4: 커밋**

```bash
git add core/quant_core/oil_futures/__init__.py
git commit -m "refactor(oil-futures): 공개 API load_wti→prepare_wti"
```

---

## Task 4: 엔진 테스트를 합성 픽스처로 전환 (TDD)

`test_oil_futures.py`는 `load_wti()`(CSV)에 의존한다. 오프라인·결정적 합성 시리즈로 교체한다.

**Files:**
- Modify: `core/tests/test_oil_futures.py`

- [ ] **Step 1: 현재 CSV 의존 지점 확인**

Run: `cd core && grep -n "load_wti\|wti_daily\|DEFAULT_CSV\|read_csv" tests/test_oil_futures.py`
Expected: `load_wti` 등 CSV 의존 호출 위치 목록.

- [ ] **Step 2: 공통 합성 픽스처 추가 (파일 상단)**

`core/tests/test_oil_futures.py` 상단 import 직후에 추가:

```python
import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def wti_df():
    """결정적 합성 WTI 일봉 — 추세+사인 변동, 양수 보장. (실데이터/CSV 비의존)"""
    n = 600
    dates = pd.bdate_range("2018-01-01", periods=n)
    base = 50 + np.linspace(0, 40, n) + 8 * np.sin(np.arange(n) / 18.0)
    close = base
    openp = np.r_[close[0], close[:-1]]
    high = np.maximum(openp, close) + 1.0
    low = np.minimum(openp, close) - 1.0
    return pd.DataFrame({
        "date": dates, "open": openp, "high": high,
        "low": low, "close": close, "volume": 1000.0,
    })
```

- [ ] **Step 3: load_wti() 호출을 픽스처로 치환**

기존 테스트에서 `df = load_wti(...)` 형태를 각 테스트 함수가 `wti_df` 픽스처를 인자로 받아 쓰도록 바꾼다. 예:

```python
# 변경 전
def test_grid_search_runs():
    df = load_wti()
    cells = grid_search(df, [100], [20], [60], CostModel())
    assert len(cells) >= 1

# 변경 후
def test_grid_search_runs(wti_df):
    cells = grid_search(wti_df, [100], [20], [60], CostModel())
    assert len(cells) >= 1
```

그리고 파일 상단의 `from quant_core.oil_futures.data import load_wti`(또는 `... import load_wti`)와 모든 `load_wti(` 호출을 제거한다.

- [ ] **Step 4: 통과 확인**

Run: `cd core && python -m pytest tests/test_oil_futures.py -q`
Expected: PASS (전 테스트 통과, CSV 비의존)

- [ ] **Step 5: 커밋**

```bash
git add core/tests/test_oil_futures.py
git commit -m "test(oil-futures): CSV 의존 제거 — 합성 픽스처로 결정적 테스트"
```

---

## Task 5: 라우터 `_df()` 재배선 — 캐시 데이터 소비 + 버전키

`_df()`는 9개 endpoint 단일 관문. `load_wti()`(CSV)를 `get_raw_dataset()["원유선물"]` + `prepare_wti`로 교체하고, `lru_cache`(절대 갱신 안 됨) 대신 데이터 버전키 캐시를 쓴다.

**Files:**
- Modify: `server/app/routers/oil_futures.py`

- [ ] **Step 1: import 교체**

`server/app/routers/oil_futures.py` 상단 import 영역에서 `from quant_core.oil_futures import (...)` 블록은 유지하되, `load_wti`를 빼고(있다면) 다음을 추가:

```python
from quant_core.oil_futures import prepare_wti
from ..data_cache import get_raw_dataset, get_version
```

(`HTTPException`은 기존 `from fastapi import APIRouter, HTTPException`에 이미 있으므로 재import 불필요.)

- [ ] **Step 2: `_df()` 본문 교체**

기존:
```python
@lru_cache(maxsize=1)
def _df() -> pd.DataFrame:
    return load_wti()
```
교체:
```python
_WTI_CACHE: dict = {"version": None, "df": None}

def _df() -> pd.DataFrame:
    """캐시된 '원유선물'(CL=F) 시리즈를 정제해 반환. 데이터 버전 변경 시 자동 갱신."""
    v = get_version()
    if _WTI_CACHE["version"] != v:
        ds = get_raw_dataset()
        raw = ds.get("원유선물")
        if raw is None or raw.empty:
            raise HTTPException(status_code=503, detail="원유 데이터 미수집 — 데이터 수집 후 이용 가능")
        _WTI_CACHE["df"] = prepare_wti(raw)
        _WTI_CACHE["version"] = v
    return _WTI_CACHE["df"]
```

- [ ] **Step 3: 서버 import·동작 확인 (수동 검증)**

Run: `cd server && PYTHONPATH=../core python -c "from app.routers import oil_futures; print('ok', [r.path for r in oil_futures.router.routes][:3])"`
Expected: `ok [...]` (import 성공, 라우트 노출)

- [ ] **Step 4: 커밋**

```bash
git add server/app/routers/oil_futures.py
git commit -m "feat(oil-futures): _df() — 정적 CSV→캐시 '원유선물' 시리즈(버전키)"
```

---

## Task 6: 라우터 `_macro_df()` 재배선 — VIX·달러지수 캐시 소비

`macro_daily.csv` 대신 캐시된 `VIX`·`달러지수` 시리즈로 `date·vix_close·dxy_close` 프레임을 만든다(기존 merge 형식 유지).

**Files:**
- Modify: `server/app/routers/oil_futures.py`

- [ ] **Step 1: `_MACRO_CSV` 상수 + 옛 `_macro_df()` 교체**

기존(라우터 하단):
```python
from pathlib import Path  # noqa: E402

_MACRO_CSV = Path(__file__).resolve().parents[3] / "core" / "data" / "macro_daily.csv"


@lru_cache(maxsize=1)
def _macro_df() -> Optional[pd.DataFrame]:
    if not _MACRO_CSV.exists():
        return None
    m = pd.read_csv(_MACRO_CSV, parse_dates=["date"])
    return m
```
교체:
```python
def _macro_df() -> Optional[pd.DataFrame]:
    """캐시된 VIX·달러지수 종가로 date·vix_close·dxy_close 프레임 생성."""
    ds = get_raw_dataset()
    vix = ds.get("VIX")
    dxy = ds.get("달러지수")
    if vix is None or vix.empty or dxy is None or dxy.empty:
        return None
    v = vix["Close"].rename("vix_close")
    d = dxy["Close"].rename("dxy_close")
    m = pd.concat([v, d], axis=1).reset_index()
    m = m.rename(columns={m.columns[0]: "date"})
    m["date"] = pd.to_datetime(m["date"]).dt.tz_localize(None).dt.normalize()
    return m.dropna(subset=["vix_close", "dxy_close"])
```

(`Path` import가 다른 데서 안 쓰이면 그 줄도 제거. 또한 Task 5·6에서 `_df`·`_macro_df`의 `@lru_cache`가 모두 제거됐으므로, 상단 `from functools import lru_cache`가 더는 안 쓰이면 그 import도 제거.)

- [ ] **Step 2: import 확인**

Run: `cd server && PYTHONPATH=../core python -c "from app.routers import oil_futures; print('ok')"`
Expected: `ok`

- [ ] **Step 3: 커밋**

```bash
git add server/app/routers/oil_futures.py
git commit -m "feat(oil-futures): _macro_df() — macro CSV→캐시 VIX·달러지수"
```

---

## Task 7: `latest-price` — 마지막 종가로 단순화 (스크래핑 제거)

investing.com 스크래핑·yfinance 라이브 fetch를 제거하고 캐시 마지막 종가만 쓴다.

**Files:**
- Modify: `server/app/routers/oil_futures.py`

- [ ] **Step 1: 스크래핑/라이브 코드 삭제**

다음을 **삭제**한다: `_PRICE_CACHE`, `_PRICE_TTL`, `_INVESTING_URL`, `_UA`, 함수 `_fetch_investing()`, `_fetch_yfinance()`. 상단 import에서 다른 데서 안 쓰이면 `import requests`, `import re`, `import time`도 제거.

- [ ] **Step 2: `latest_price` 본문 교체**

```python
@router.get("/latest-price", response_model=LatestPrice)
def latest_price():
    """WTI 최신가 = 캐시 일봉 마지막 종가 (일배치 기준, delayed=True)."""
    df = _df()
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else last
    return LatestPrice(
        price=float(last["close"]),
        change=float(last["close"] - prev["close"]),
        change_pct=float(last["close"] / prev["close"] - 1) if prev["close"] else None,
        source="yahoo-cl=f", delayed=True,
        fetched_at=pd.Timestamp.utcnow().isoformat(),
    )
```

(`LatestPrice.source` 주석의 허용값을 `"yahoo-cl=f"`로 갱신)

- [ ] **Step 3: import·노출 확인**

Run: `cd server && PYTHONPATH=../core python -c "from app.routers import oil_futures; import inspect; print('investing' not in inspect.getsource(oil_futures))"`
Expected: `True` (스크래핑 코드 잔존 없음)

- [ ] **Step 4: 커밋**

```bash
git add server/app/routers/oil_futures.py
git commit -m "feat(oil-futures): latest-price=마지막 종가 — investing.com 스크래핑 제거"
```

---

## Task 8: 인증 게이트 (라우터 레벨)

`/oil-futures/*` 전체에 로그인 인증을 건다(타 라우터 정합).

**Files:**
- Modify: `server/app/routers/oil_futures.py`

- [ ] **Step 1: APIRouter에 dependencies 추가**

상단 fastapi import에 `Depends`를 추가(기존 `from fastapi import APIRouter, HTTPException` → `from fastapi import APIRouter, HTTPException, Depends`)하고, `from ..deps import get_current_user`를 더한다. 그런 다음 라우터 생성부:
```python
router = APIRouter(prefix="/oil-futures", tags=["oil-futures"])
```
를 다음으로 교체:
```python
router = APIRouter(
    prefix="/oil-futures", tags=["oil-futures"],
    dependencies=[Depends(get_current_user)],
)
```

- [ ] **Step 2: import·노출 확인**

Run: `cd server && PYTHONPATH=../core python -c "from app.routers import oil_futures; print(len(oil_futures.router.routes))"`
Expected: `9`

- [ ] **Step 3: 커밋**

```bash
git add server/app/routers/oil_futures.py
git commit -m "feat(oil-futures): 라우터 인증 게이트(Depends get_current_user)"
```

---

## Task 9: 인증 동작 테스트 (미인증 401)

**Files:**
- Test: `server/tests/test_oil_futures_auth.py` (없으면 생성)

- [ ] **Step 1: 실패 테스트 작성**

```python
# server/tests/test_oil_futures_auth.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_oil_endpoints_require_auth():
    # 토큰 없이 호출 → 401/403
    for path in ["/oil-futures/data-info", "/oil-futures/latest-price"]:
        r = client.get(path)
        assert r.status_code in (401, 403), f"{path} → {r.status_code}"
```

- [ ] **Step 2: 실행 (인증 차단 확인)**

Run: `cd server && PYTHONPATH=../core python -m pytest tests/test_oil_futures_auth.py -q`
Expected: PASS (미인증 401/403)

- [ ] **Step 3: 커밋**

```bash
git add server/tests/test_oil_futures_auth.py
git commit -m "test(oil-futures): 미인증 접근 차단(401/403) 검증"
```

---

## Task 10: 라우터 등록 (main.py)

**Files:**
- Modify: `server/app/main.py`

- [ ] **Step 1: routers import 튜플에 oil_futures 추가**

`from .routers import (...)` 블록의 알파벳 위치(`market,` 뒤)에 `oil_futures,` 추가.

- [ ] **Step 2: include_router 추가**

`app.include_router(...)` 목록 끝(예: `admin_router.router` 뒤)에 추가:
```python
app.include_router(oil_futures.router)
```

- [ ] **Step 3: 컴파일 확인**

Run: `cd server && python -m py_compile app/main.py && echo OK`
Expected: `OK`

- [ ] **Step 4: 커밋**

```bash
git add server/app/main.py
git commit -m "feat(oil-futures): main.py 라우터 등록"
```

---

## Task 11: pyproject 패키지 등록

**Files:**
- Modify: `core/pyproject.toml`

- [ ] **Step 1: packages에 서브패키지 추가**

```toml
packages = ["quant_core"]
```
를:
```toml
packages = ["quant_core", "quant_core.oil_futures"]
```

- [ ] **Step 2: 설치·import 확인**

Run: `cd core && python -c "import quant_core.oil_futures; print('pkg ok')"`
Expected: `pkg ok`

- [ ] **Step 3: 커밋**

```bash
git add core/pyproject.toml
git commit -m "build(oil-futures): pyproject packages에 서브패키지 등록"
```

---

## Task 12: 웹 — 출처 표기 추가

페이지·`oilApi`·라우트·네비는 Task 1에서 이미 가져옴. 데이터 출처/한계만 명시(R1).

**Files:**
- Modify: `web/src/pages/OilFutures.tsx`

- [ ] **Step 1: 헤더에 출처 캡션 추가**

`OilFutures.tsx`의 페이지 헤더(eyebrow/제목 부근)에 작은 캡션 추가:
```tsx
<div className="oil-source-note">데이터: Yahoo Finance WTI front-month (CL=F) · 일배치 · 롤 점프 포함</div>
```

- [ ] **Step 2: 빌드 확인**

Run: `cd web && npm install --no-audit --no-fund && npm run build`
Expected: `tsc -b && vite build` 성공(에러 0)

- [ ] **Step 3: 커밋**

```bash
git add web/src/pages/OilFutures.tsx
git commit -m "feat(oil-futures): 데이터 출처(Yahoo CL=F)·롤 점프 한계 표기"
```

---

## Task 13: 웹 — 디자인 시스템 정합 패스

`index.css`의 원유 전용 블록(약 390줄)을 `DESIGN.md` 토큰과 정합.

**Files:**
- Modify: `web/src/index.css`
- Reference: `DESIGN.md`

- [ ] **Step 1: DESIGN.md 토큰 확인**

Run: `grep -nE "^\s*--[a-z-]+:|color|spacing|radius|font" DESIGN.md | head -40`
Expected: CSS 변수(예: `--bg`, `--muted`, `--red`, 간격·라운드) 목록.

- [ ] **Step 2: 원유 블록의 하드코딩 값 → 토큰 치환**

`web/src/index.css`에서 `.oil-*` 셀렉터의 하드코딩 색(`#xxxxxx`)·간격(px)·라운드를 DESIGN.md 변수(`var(--…)`)로 치환. 기존 전역 변수를 그대로 쓰는 곳(이미 `var(--muted)` 등)은 유지. 신규 도입 색이 있으면 토큰으로 승격.

- [ ] **Step 3: 시각 회귀 확인 (빌드 + 브라우저)**

Run: `cd web && npm run build`
Expected: 빌드 성공. 이후 dev 서버로 `/oil-futures` 렌더 — 레이아웃·대비 정상.

- [ ] **Step 4: 커밋**

```bash
git add web/src/index.css
git commit -m "style(oil-futures): index.css 원유 블록 DESIGN.md 토큰 정합"
```

---

## Task 14: 전체 검증

**Files:** (검증만)

- [ ] **Step 1: core 테스트**

Run: `cd core && python -m pytest tests/test_oil_futures.py tests/test_oil_futures_data.py -q`
Expected: 전부 PASS

- [ ] **Step 2: 서버 라우터 import + 인증 테스트**

Run: `cd server && PYTHONPATH=../core python -m pytest tests/test_oil_futures_auth.py -q && python -m py_compile app/main.py`
Expected: PASS + 컴파일 OK

- [ ] **Step 3: 웹 빌드**

Run: `cd web && npm run build`
Expected: `tsc -b && vite build` 성공(에러 0)

- [ ] **Step 4: 브라우저 확인 (서버+웹 기동, 로그인 후 /oil-futures)**

서버(`uvicorn app.main:app`)와 웹(`bun run dev` 또는 `npm run dev`)을 띄우고 로그인 → 네비 "원유 분석" 클릭 → 차트·grid·백테스트 동작 확인. 데이터 미수집 환경이면 `/oil-futures/*`가 503(graceful) 반환하는지 확인.

- [ ] **Step 5: 최종 커밋(없으면 skip) + 요약**

```bash
git log --oneline origin/main..HEAD
```
Expected: Task 1~13의 커밋 목록.

---

## 검증 신호 요약

- core: `test_oil_futures.py` + `test_oil_futures_data.py` PASS (합성 픽스처, 오프라인)
- server: 라우터 import OK·9 routes·미인증 401/403·`main.py` 컴파일
- web: `tsc -b && vite build` 에러 0
- 통합: 로그인 후 `/oil-futures` 렌더·동작, 미수집 시 503 graceful
