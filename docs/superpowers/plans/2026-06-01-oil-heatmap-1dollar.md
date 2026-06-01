# 원유 히트맵 $1 임계가격 + 행-헤더 샘플수 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** PnL 히트맵의 임계가격을 $10→$1 단위로 노출하고, 임계가격별 표본수(n)를 행 헤더에 `$10 (n=6)` 형식으로 표시한다. $1(854셀)은 백그라운드 사전계산·버전키 캐시로 서빙해 사용자 대기 0.

**Architecture:**
- core: `run_backtest`/`grid_search`에 `light` 모드 추가 — 그리드가 쓰지 않는 per-trade MAE/MFE 장중 스캔 + portfolio mark-to-market 곡선을 건너뛴다(검증: net_pnl·win_rate·sharpe·mdd는 realized equity 기반이라 동일, MAE/MFE/portfolio만 0).
- server: 히트맵 grid 기본을 $1(`GRID_SHORTS/LONGS`)로, `light=True`로 계산, `_GRID_CACHE` 키에 데이터 버전 포함, daemon 워머 루프가 startup·버전변경마다 기본 grid를 미리 채운다. walk-forward는 coarse $10·full 유지(과적합 검증 표준 + 빠름).
- web: 히트맵 행/열을 grid 응답에서 파생(하드코딩 상수 제거), 행 헤더에 `$임계 (n=표본)` 표기.

**Tech Stack:** Python(pandas)·FastAPI·React+TS(Vite)·recharts. 격리 클론 `_analysis/original`, branch `feature/oil-heatmap-1dollar`(off origin/main 88d1837).

**금지:** 공유 schema/lockfile/루트 config 수정 금지. git commit/push 금지(컨트롤러가 검증 후 처리). walk-forward 동작 변경 금지. /backtest 상세(MAE/MFE·portfolio) 동작 변경 금지.

---

### Task 1: core — `light` 모드 (backtest + grid_search)

**Files:**
- Modify: `core/quant_core/oil_futures/backtest.py` (`run_backtest`)
- Modify: `core/quant_core/oil_futures/optimizer.py` (`grid_search`)
- Test: `core/tests/test_oil_futures.py` (light 동등성 테스트 추가)

**설계:**
- `run_backtest(..., light: bool = False)`. `light=True`면:
  - per-trade MAE/MFE 장중 스캔(`held = df.iloc[entry_i:exit_i+1]; .max()/.min()`) 건너뛰고 `mae_usd=0.0, mfe_usd=0.0`.
  - `_compute_portfolio_mtm` 호출 생략 → `portfolio_equity_curve=pd.Series(dtype=float)`, `portfolio_mdd_usd=0.0`.
  - 그 외(진입/청산/net_pnl/return/realized equity_curve/롤오버)는 동일.
- `grid_search(..., light: bool = False)` → 내부 `run_backtest(..., light=light)`로 전달.
- 기본값 `light=False`라 기존 호출부(/backtest, walk_forward) 동작 불변.

- [ ] **Step 1: 실패 테스트** — `test_oil_futures.py`에 추가: 합성 `small_df`(기존 픽스처)로 동일 (side, threshold, horizon) 백테스트를 light=False/True로 돌려, `summarize()` 결과의 `n_trades / win_rate / avg_return / sharpe_annualized / max_drawdown_usd / total_net_pnl_usd / profit_factor / gross_profit_usd / gross_loss_usd`가 **동일**하고, light=True 결과의 모든 trade `mae_usd==0 and mfe_usd==0`, `result.portfolio_equity_curve.empty and result.portfolio_mdd_usd==0.0`임을 assert.
- [ ] **Step 2: 실패 확인** — `cd core; python -m pytest tests/test_oil_futures.py -k light -q` → FAIL(`light` 인자 없음).
- [ ] **Step 3: 구현** — backtest.py: `light` 파라미터 추가, MAE/MFE 블록을 `if not light:`로 감싸 light면 0.0, portfolio 블록도 `if light: curve=empty,mdd=0 else: _compute_portfolio_mtm(...)`. optimizer.py: `grid_search`에 `light` 추가·전달.
- [ ] **Step 4: 통과 확인** — `python -m pytest tests/test_oil_futures.py -q` 전부 PASS(기존 14 + 신규).
- [ ] **Step 5: 회귀** — `python -m pytest tests/test_oil_futures_data.py -q` PASS.

### Task 2: server — $1 기본 grid + 버전키 캐시 + 워머

**Files:**
- Modify: `server/app/routers/oil_futures.py`
- Modify: `server/app/main.py` (lifespan에 워머 thread 시작)

**설계:**
- 상수: `DEFAULT_SHORTS/LONGS/HORIZONS`(현 $10·walk-forward용) **유지**. 신규
  `GRID_SHORTS = list(range(80, 151))`, `GRID_LONGS = list(range(10, 61))` ($1, 히트맵용). `$10 OOM` 주석을 "백그라운드 사전계산·light 모드로 $1 서빙"으로 갱신.
- `_GRID_CACHE` 키에 데이터 버전 포함. 공통 헬퍼:
  ```python
  _grid_lock = threading.Lock()
  def _ensure_grid_cached(s, l, h, commission, slippage):
      df = _df()                       # get_raw_dataset 경유 → _maybe_reload로 일갱신 감지; 데이터 없으면 503
      version = get_version()          # _df 정착 후 읽기
      key = (version, s, l, h, commission, slippage)
      cached = _GRID_CACHE.get(key)
      if cached is not None: return cached
      with _grid_lock:
          cached = _GRID_CACHE.get(key)
          if cached is not None: return cached
          cells = grid_search(df, s, l, h, CostModel(commission, slippage), light=True)
          out = [GridCellOut(... 기존 매핑 ...) for c in cells]
          del cells; gc.collect()
          if len(_GRID_CACHE) >= 4: _GRID_CACHE.pop(next(iter(_GRID_CACHE)))
          _GRID_CACHE[key] = out
          return out
  ```
- `/grid` 엔드포인트: 기본 폴백을 `GRID_SHORTS/GRID_LONGS`로, 본문을 `return _ensure_grid_cached(s, l, h, commission, slippage_ticks)`로 교체.
- 워머:
  ```python
  def _warmer_loop():
      first = True
      while True:
          try:
              _ensure_grid_cached(tuple(GRID_SHORTS), tuple(GRID_LONGS),
                                  tuple(DEFAULT_HORIZONS), 2.5, 1)
              first = False
          except HTTPException:
              pass                      # 데이터 미준비(503) — 다음 틱 재시도
          except Exception:
              import logging; logging.getLogger(__name__).warning(
                  "oil grid 워밍 실패 — 온디맨드로 계산됨", exc_info=True)
              first = False
          time.sleep(20 if first else 300)

  def start_grid_warmer():
      threading.Thread(target=_warmer_loop, daemon=True, name="oil-grid-warm").start()
  ```
  `import threading, time` 추가.
- main.py lifespan: 다른 `_initial_*` thread들 옆에 `from .routers import oil_futures; oil_futures.start_grid_warmer()` 한 줄(로그 포함).

- [ ] **Step 1: 구현(서버 라우터)** — 위 설계대로 oil_futures.py 수정. 기존 GridCellOut 매핑 보존.
- [ ] **Step 2: 워머 hookup** — main.py lifespan에 `start_grid_warmer()` 추가 + `_log.info`.
- [ ] **Step 3: 인증 회귀** — `cd server; python -m pytest tests/test_oil_futures_auth.py -q` PASS(엔드포인트 그대로라 401 유지).
- [ ] **Step 4: import 정합** — `python -c "from app.routers import oil_futures"` (server dir, sys.path) 에러 없음.

### Task 3: web — 데이터 파생 히트맵 + 행 헤더 n

**Files:**
- Modify: `web/src/pages/OilFutures.tsx`

**설계:**
- `heatmaps` useMemo를 grid 데이터에서 파생:
  ```ts
  const heatmaps = useMemo(() => {
    if (!grid) return { short: [], long: [], horizons: [] as number[], max: 1 };
    const max = Math.max(1, ...grid.map((c) => Math.abs(c.net_pnl_usd)));
    const horizons = [...new Set(grid.map((c) => c.horizon))].sort((a, b) => a - b);
    const byKey = new Map(grid.map((c) => [`${c.side}|${c.threshold}|${c.horizon}`, c]));
    const build = (side: "short" | "long") => {
      const ths = [...new Set(grid.filter((c) => c.side === side).map((c) => c.threshold))]
        .sort((a, b) => a - b);
      return ths.map((th) => {
        const cells = horizons.map((h) => byKey.get(`${side}|${th}|${h}`));
        const n = Math.max(0, ...cells.map((c) => c?.n_trades ?? 0));
        return { threshold: th, n, cells };
      });
    };
    return { short: build("short"), long: build("long"), horizons, max };
  }, [grid]);
  ```
- `HeatmapBlock` props에 `horizons: number[]` 추가, `rows` 타입에 `n: number` 추가. 헤더 `DEFAULT_HORIZONS.map` → `horizons.map`. 행 헤더 `<th>${row.threshold}</th>` → `<th>${row.threshold} <span className="heat-n">(n={row.n})</span></th>`(렌더: `$10 (n=6)`).
- 두 호출부(short/long)에 `horizons={heatmaps.horizons}` 전달.
- 이제 미사용된 모듈 상수 `DEFAULT_SHORTS`, `DEFAULT_LONGS`, `DEFAULT_HORIZONS` 제거(다른 참조 없음 확인 후). `index.css`에 `.heat-n{font-weight:400;opacity:.6;font-size:10px;}` 추가(선택).

- [ ] **Step 1: 구현** — 위 설계대로 OilFutures.tsx 수정. `.heat-n` CSS 추가.
- [ ] **Step 2: 상수 미참조 확인** — `grep -n "DEFAULT_SHORTS\|DEFAULT_LONGS\|DEFAULT_HORIZONS" web/src/pages/OilFutures.tsx` → 정의·잔존참조 없음.
- [ ] **Step 3: 타입체크/빌드** — `cd web; bun run build`(또는 tsc) 에러 0.

### Task 4: 검증 (컨트롤러 직접)

- [ ] light $1 컴퓨트 벤치마크(`_bench_grid.py` 확장: light=True 854셀 시간) — 라이브 대비 단축 수치 기록.
- [ ] 로컬 풀스택 E2E(서버+웹, yfinance 3시리즈, 로그인 토큰): 히트맵 $1 행 + 행헤더 `$x (n=y)` 렌더, 워밍 후 즉시, 셀 클릭→백테스트 상세(MAE/MFE·portfolio 정상), walk-forward 정상. 브라우저 스크린샷.
- [ ] 최종 통합 리뷰(서브에이전트) → 사용자 보고 → 병합은 사용자 승인 후.
