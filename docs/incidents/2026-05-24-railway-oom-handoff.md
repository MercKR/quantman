# Railway OOM Crash — Hand-off (2026-05-24)

이 문서는 **새 Claude Code 세션이 zero context에서 이 issue를 정확히 fix**할 수 있도록 작성되었다. 진단은 이미 완료, 작업자는 **fix + 검증만** 수행하면 된다.

---

## 0. 한 줄 요약

서버([platform/server/app/main.py](../../server/app/main.py))가 부팅 후 4~10분에 OOM으로 반복 crash. 진짜 원인은 [platform/core/quant_core/data_fetcher.py:265-349](../../core/quant_core/data_fetcher.py) `fetch_korean_stocks`가 4,288개 한국 종목 OHLCV `DataFrame`을 `results` dict에 누적해서 반환하지만, **유일한 호출자([platform/server/app/main.py:258](../../server/app/main.py))가 반환값을 받지 않음** → **~1.5–2 GB dead allocation**. Railway Hobby plan(8 GB)에서 베이스라인이 ~6.3 GB까지 차서 작은 spike만으로도 OOM.

위반 원칙: **PR-2 (Over-engineering)** + **PR-4 (검증 누락)**.

---

## 1. Context (새 세션을 위한 배경)

### 프로젝트
- 한국 주식 자동매매 SaaS 플랫폼 (모노레포 `platform/`).
- 구성: `core/` (공유 quant_core 패키지) + `server/` (FastAPI, Railway) + `web/` (Vite, Vercel) + `local/` (Tkinter PyInstaller).
- 작업 가이드: [platform/CLAUDE.md](../../CLAUDE.md) — 4원칙(근본원인 해결·Over-engineering 금지·Overthinking 금지·검증된 해결책만) 반드시 준수.

### 영향 받은 서비스
- Railway project: **amiable-light** / environment: **production** / service: **quantman**
- Repo: `MercKR/quantman` (private) — server 코드만 자동 deploy.
- URL: `https://quantman-production.up.railway.app`
- Region: `sfo`
- Memory plan: **Hobby = 8 GB 한도**
- Volume: `quantman-volume` @ `/srv/data` (0.5 / 4.9 GB 사용 — 디스크는 문제 없음).
- Dockerfile: [platform/Dockerfile](../../Dockerfile) — `python:3.12-slim` + uvicorn.

### 부팅 흐름 (참고)
[platform/server/app/main.py](../../server/app/main.py) `lifespan()`이 8개 daemon thread를 동시 spawn:
- `_initial_master_refresh` (즉시)
- `_initial_calendar_refresh` (즉시)
- `_initial_krx_refresh` (sleep 45s)
- `_initial_naver_refresh` (sleep 120s)
- `_initial_technical_refresh` (sleep 180s)
- `_initial_dataset_refresh` (sleep 240s) ← **여기서 fetch_korean_stocks 호출됨, 메모리 폭증 지점**
- `_initial_us_market_caps` (sleep 360s)

`_initial_dataset_refresh` → `_refresh_dataset_all` → `_refresh_kr_dataset` → **`data_fetcher.fetch_korean_stocks(kr_codes)`**.

---

## 2. 증상 (관측된 사실)

### 사용자 보고
> "새벽 3시에 Railway에서 out of memory 사유로 crash 됐다고 뜬다"

### 실제 패턴: 24h 동안 OOM 9회+ (시간대 무관)

`railway deployment list` + `railway metrics --memory --since 24h --raw --json`로 분 단위 매칭 확인.

| KST | UTC | Memory peak → drop (GB) | 비고 |
|---|---|---|---|
| 15:24 | 06:24 | 7.16 → 3.71 | drop = OOM kill |
| 16:32 | 07:32 | 5.76 → 3.85 | |
| 19:44 | 10:44 | 6.76 → 3.78 | |
| **20:48** | **11:48** | **8.67 → 3.84** | **8 GB 한도 직접 초과** |
| 21:04 | 12:04 | 4.24 → 3.79 | 부팅 1분만에 또 죽음 |
| 00:20 (5/24) | 15:20 | 5.99 → 0.25 | |
| 01:24 | 16:24 | 6.73 → 0.64 | |
| 02:48 | 17:48 | 6.89 → 0.59 | |
| **03:08** | **18:08** | **6.63 → 0.82** | **사용자가 본 새벽 3시 crash** |

베이스라인 메모리 **5.7–6.3 GB**가 Hobby 8 GB의 **~75%**를 상시 차지 → spike 1.5 GB만 들어와도 OOM.

### Crash deployment의 직접 로그
`railway logs 56d06873-5639-4601-a11b-0ef3386557ec -d -n 500` (03:08 KST에 죽은 deployment) 결과:

```
Mounting volume on: /var/lib/containers/.../vol_7v64s5uw2j0d26ii
Starting Container
INFO:     Waiting for application startup.
INFO:     Started server process [2]
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080
한국 종목 fetch 완료: 총 4288 → 성공 0 · 신규없음 3889 · 실패 399
Killed                                                    ← OOM kill
[재시작]
한국 종목 fetch 완료: 총 4288 → 성공 0 · 신규없음 3889 · 실패 399
Stopping Container
```

**핵심:** "성공 0 · 신규없음 3889" — 새 데이터를 **거의 받지도 않았는데도** OOM. 즉 fetch 자체의 network 부담이 아니라 **메모리에 누적되는 dict 때문**.

---

## 3. Root Cause (정확한 코드 위치)

### 문제 함수
[platform/core/quant_core/data_fetcher.py:265-349](../../core/quant_core/data_fetcher.py)

```python
def fetch_korean_stocks(codes: list[str], start: str = "2015-01-01",
                         verbose: bool = False) -> dict[str, pd.DataFrame]:
    # ...
    results: dict[str, pd.DataFrame] = {}           # ← 4,288개 누적용
    n_ok = n_skip = n_fail = 0
    for i, code in enumerate(codes):
        if i > 0 and i % 100 == 0:
            gc.collect()                            # ← results dict reference 때문에 무의미
        existing = _load_existing(code)
        if not existing.empty:
            last_date = existing.index[-1].date()
            if last_date >= last_closed_market_date:
                results[code] = existing            # ← line 318: skip인데도 메모리 적재
                n_skip += 1
                continue
        s = (existing.index[-1] + timedelta(days=1)).strftime("%Y-%m-%d") \
            if not existing.empty else start
        try:
            df = fdr.DataReader(code, s)
        except Exception as e:
            if verbose:
                print(f"  [{i+1}/{len(codes)}] {code}: 오류 {e}")
            n_fail += 1
            if not existing.empty:
                results[code] = existing            # ← line 331: fallback도 적재
            continue
        if df.empty:
            if not existing.empty:
                results[code] = existing            # ← line 336: 신규 없으면 적재
            n_skip += 1
            continue
        # ... (compute merged)
        results[code] = merged                      # ← line 344: 성공도 적재
        n_ok += 1
    print(f"한국 종목 fetch 완료: 총 {len(codes)} → 성공 {n_ok} · 신규없음 {n_skip} · 실패 {n_fail}")
    return results                                  # ← return하지만 호출자가 안 씀
```

### 유일한 호출자
[platform/server/app/main.py:258](../../server/app/main.py)

```python
# _refresh_kr_dataset() 내부
data_fetcher.fetch_korean_stocks(kr_codes, verbose=False)   # ← 반환값 받지 않음
```

**그 외 호출자 없음.** 검증:
```powershell
# 새 세션에서 직접 재검증할 명령
Grep -r "fetch_korean_stocks" platform/
# 기대 출력: 정의(data_fetcher.py:265) + 호출(server/app/main.py:258) 두 곳만
```

### 메모리 산출
- 4,288 종목 (KOSPI + KOSDAQ + ETF/REITs, KIS 마스터 기반)
- 종목당 2015-01-01 ~ 현재 OHLCV ≈ 2,500 행 × 5 컬럼 (OHLCV) × 8 byte (float64)
- 인덱스(DatetimeIndex) 오버헤드 포함 = 종목당 ~150 KB
- **총 ~600 MB**(순수 데이터) + pandas DataFrame 오버헤드 = **~1.5–2 GB 실제 RSS 증가**

부팅 후 240초(`_initial_dataset_refresh` sleep) + 한국 종목 4,288개 iterate = **부팅 약 4~7분 만에 ~2 GB 추가** → 베이스라인 5–6 GB 위에서 OOM 트리거.

### 왜 cron이 아닌 부팅이 문제인가
crash deployment 로그에서 보듯, fetch 직후 **첫 사이클**에서 죽는다. cron이 도는 시각(15:45, 17:00, 17:15, 18:15 KST)이 아니라 **부팅 + 4분 = 매번 OOM**. 따라서 03:00 KST `calendars` cron은 trigger와 무관 — 03:08 deployment도 부팅 직후 fetch가 killer였다.

---

## 4. Fix #1 — `fetch_korean_stocks` (필수)

### 변경 원칙 (4원칙 준수)
- PR-2 (Over-engineering 제거): 사용 안 되는 results dict 자체를 만들지 말 것.
- PR-3 (Overthinking 제거): `gc.collect()` 빈도 호출도 results dict가 없어지면 의미 ↓ → 그대로 두되 cleanup만.
- 반환 타입은 **호출자가 안 쓰므로** count dict로 단순화 (또는 `None`). count dict가 verbose 로그·테스트에 유용할 수 있어 권장.

### 변경 대상 함수 시그니처
```python
def fetch_korean_stocks(
    codes: list[str],
    start: str = "2015-01-01",
    verbose: bool = False,
) -> dict[str, int]:                # ← dict[str, pd.DataFrame] 에서 변경
```

### 변경 후 함수 본문 (전체 교체)
[platform/core/quant_core/data_fetcher.py:265-349](../../core/quant_core/data_fetcher.py) 전체를 다음으로 교체:

```python
def fetch_korean_stocks(codes: list[str], start: str = "2015-01-01",
                         verbose: bool = False) -> dict[str, int]:
    """한국 거래소 종목 OHLC 일괄 수집 (FinanceDataReader, KRX 직접 소스).

    각 코드(예: "005930")로 fdr.DataReader 호출 → parquet incremental append.
    실패한 종목은 skip하고 로그 — 한 종목 실패가 전체를 막지 않는다.
    호출자(서버 cron)가 한국 거래 가능 종목 ~4,300개를 매일 1회 호출.

    **컬럼 의미** — FDR(NAVER 백엔드)의 OHLC는 모두 정규장(09:00~15:30) 기준:
      Open/High/Low/Close = 정규장 시초가/고가/저가/마감가
      Volume              = 정규장 거래량 (시간외 거래량 미포함)
      Change              = 정규장 종가 전일 대비 등락률
    시간외 단일가(16:00~18:00)는 별도 endpoint이며 본 fetch에 포함되지 않음.

    저장은 종목별 parquet에 직접 — in-memory aggregation은 하지 않는다(메모리
    누적이 4,000+ 종목 × ~2,500행 DataFrame으로 ~2 GB까지 dead allocation 발생).
    호출자는 결과 DataFrame을 받지 않고, count 통계만 받는다.

    Args:
        codes: KRX 종목 코드 리스트 (6자리)
        start: 새 종목 첫 fetch 시 시작일. 기존 parquet 있으면 무시되고 이어받음.
    Returns:
        {"ok": int, "skip": int, "fail": int} — count 통계만
    """
    import gc
    from datetime import timezone

    # KST 기준 마지막 마감된 거래일 구하기
    tz_kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(tz_kst)
    today_kst = now_kst.date()
    market_closed = now_kst.time() >= datetime.strptime("15:40:00", "%H:%M:%S").time()

    if today_kst.weekday() < 5:  # 월~금
        if market_closed:
            last_closed_market_date = today_kst
        else:
            days_to_subtract = 3 if today_kst.weekday() == 0 else 1
            last_closed_market_date = today_kst - timedelta(days=days_to_subtract)
    elif today_kst.weekday() == 5:  # 토요일
        last_closed_market_date = today_kst - timedelta(days=1)  # 금요일
    else:  # 일요일
        last_closed_market_date = today_kst - timedelta(days=2)  # 금요일

    n_ok = n_skip = n_fail = 0
    for i, code in enumerate(codes):
        if i > 0 and i % 100 == 0:
            gc.collect()

        existing = _load_existing(code)

        # 지능형 최신 상태 체크 (이미 마지막 마감장 데이터까지 다 갖고 있다면 fdr 호출 스킵)
        if not existing.empty:
            last_date = existing.index[-1].date()
            if last_date >= last_closed_market_date:
                n_skip += 1
                del existing
                continue

        s = (existing.index[-1] + timedelta(days=1)).strftime("%Y-%m-%d") \
            if not existing.empty else start
        try:
            df = fdr.DataReader(code, s)
        except Exception as e:
            if verbose:
                print(f"  [{i+1}/{len(codes)}] {code}: 오류 {e}")
            n_fail += 1
            del existing
            continue
        if df.empty:
            n_skip += 1
            del existing, df
            continue
        cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
        df = df[cols].copy()
        df.index = pd.to_datetime(df.index).tz_localize(None)
        merged = _merge(existing, df)
        _save(code, merged)
        n_ok += 1
        del existing, df, merged

        if verbose and (i + 1) % 200 == 0:
            print(f"  진행: {i+1}/{len(codes)} (성공 {n_ok} · 신규없음 {n_skip} · 실패 {n_fail})")

    print(f"한국 종목 fetch 완료: 총 {len(codes)} → 성공 {n_ok} · 신규없음 {n_skip} · 실패 {n_fail}")
    return {"ok": n_ok, "skip": n_skip, "fail": n_fail}
```

### 핵심 차이점
| Before | After |
|---|---|
| `results: dict[str, pd.DataFrame] = {}` | (제거) |
| `results[code] = existing` (4곳) | (모두 제거) |
| `results[code] = merged` | (제거) |
| `return results` | `return {"ok": ..., "skip": ..., "fail": ...}` |
| 시그니처 `-> dict[str, pd.DataFrame]` | `-> dict[str, int]` |
| (없음) | `del existing, df, merged` 명시적 해제 |

### 호출자 영향 — 변경 불필요
[platform/server/app/main.py:258](../../server/app/main.py) `data_fetcher.fetch_korean_stocks(kr_codes, verbose=False)`는 반환값을 받지 않아 그대로 동작. 단, 향후 count 통계를 활용하고 싶다면 로그 추가 가능(선택, 필수 아님):
```python
result = data_fetcher.fetch_korean_stocks(kr_codes, verbose=False)
_log.info("한국 종목 cron 결과: %s", result)
```

---

## 5. Fix #2 — 동일 패턴 점검 (`fetch_managed_overseas` 등)

### 점검 대상
[platform/core/quant_core/data_fetcher.py:420](../../core/quant_core/data_fetcher.py) `fetch_managed_overseas`도 동일한 anti-pattern일 가능성 매우 높음. **fix 전에 반드시 코드를 직접 읽고 확인**.

### 점검 절차
1. 함수 본문 읽기 — `results: dict[str, pd.DataFrame] = {}` 또는 유사 누적 패턴 있는지.
2. 호출자 검색:
   ```powershell
   Grep -r "fetch_managed_overseas" platform/
   ```
3. 호출자가 반환값을 사용하는지 확인. 안 쓴다면 Fix #1과 동일 패턴 적용.

### 또 점검할 만한 함수 (낮은 우선순위)
- [platform/core/quant_core/data_fetcher.py:826](../../core/quant_core/data_fetcher.py) `fetch_all` — yfinance/FDR ETF/FRED/Binance 등 매크로 fetch. 종목 수는 적지만(~30) 같은 패턴이면 cleanup.
- 모든 `dict[str, pd.DataFrame]` 반환 함수의 호출자가 진짜로 dict를 사용하는지 grep으로 일괄 점검:
   ```powershell
   Grep -n "dict\[str, pd.DataFrame\]" platform/core/quant_core/data_fetcher.py
   ```

---

## 6. 검증 plan (배포 후 필수 확인)

### 6.1 사전 — 로컬 검증 (선택, 5분)
```powershell
# 인코딩 주의: Windows cp949 환경. UTF-8 명시 필요 시 -Encoding utf8
cd platform
python -c "from quant_core import data_fetcher; print(data_fetcher.fetch_korean_stocks.__annotations__)"
# 기대: {'codes': ..., 'start': ..., 'verbose': ..., 'return': dict[str, int]}
```

### 6.2 commit + push
사용자 명시 허락 받은 뒤(CLAUDE.md §3) 진행:
```powershell
cd platform
git add core/quant_core/data_fetcher.py
git commit -m "fix(memory): fetch_korean_stocks results dict 제거 (Railway OOM root cause)

호출자(server/app/main.py:258)가 반환값을 사용하지 않는데도 4,288개 종목
OHLCV DataFrame을 results dict에 누적 → ~1.5-2 GB dead allocation.
Hobby 8GB plan에서 베이스라인을 임계점으로 끌어올려 OOM 9회/24h 발생.

- results dict 제거, 시그니처 dict[str, pd.DataFrame] → dict[str, int]로 변경
- 각 iteration 끝에 existing/df/merged 명시적 del로 GC 도움
- 호출자 변경 불필요 (이미 반환값 무시 중)

근거: docs/incidents/2026-05-24-railway-oom-handoff.md"
git push
```
Railway가 자동 redeploy.

### 6.3 deploy 직후 — 즉시 신호 (5분 안)
```powershell
# 1) deploy 성공 확인
railway status
# 기대: 새 deployment ID, status: ● Online

# 2) startup logs에서 fetch 완료 메시지가 나오는지 확인
railway logs -d -n 200
# 기대 line: "한국 종목 fetch 완료: 총 4288 → 성공 N · 신규없음 M · 실패 K"
# 그리고 그 직후 "Killed"가 *없어야* 함
```

### 6.4 deploy 후 4시간 — 베이스라인 확인 (필수)
```powershell
railway metrics --memory --since 4h --raw --json | Out-File -FilePath "$env:TEMP\post_fix_memory.json" -Encoding utf8
```
확인 항목:
- 베이스라인이 **~4–5 GB** 이하로 떨어졌는가 (이전 ~6.3 GB)
- 4시간 안에 메모리 drop(컨테이너 재시작 시그니처) **0회**

### 6.5 deploy 후 24시간 — 안정성 (최종)
```powershell
railway deployment list | Select-Object -First 10
# 기대: 새 deployment 1개만 SUCCESS, REMOVED 없음
```

OOM 0회 + 베이스라인 5 GB 미만 = **fix 검증 통과**. 한 번이라도 OOM이 발생하면 Phase 1로 돌아가 추가 패턴 분석 (특히 `data_cache._dataset`의 누적 또는 `fetch_managed_overseas` 동일 패턴 확인).

---

## 7. 롤백 plan

만약 fix 후 새로운 문제가 발생하면 (예: 다른 cron이 results 반환값을 암묵적으로 기대 — 가능성 낮음):
```powershell
cd platform
git revert HEAD
git push
```
Railway가 즉시 이전 버전으로 redeploy.

---

## 8. fix와 무관한 관찰 (작업자 참고용, 변경 금지)

다음은 진단 중 발견한 사항이지만 이번 fix의 scope가 아니다. **이번 PR에 끼워 넣지 말 것** (CLAUDE.md §4, "while I'm here" 금지).

1. **`data_cache._dataset`도 ~1.5–2 GB**를 차지하지만, 이는 cache로서 의도된 동작이며 cron 후 의도된 캐싱. fetch_korean_stocks fix 후에도 베이스라인 4–5 GB는 정상.
2. **`exchange_calendars` 라이브러리 누수 가설**: 03:00 cron이 매일 KR/US 캘린더 재빌드. 짧은 peak는 가능하지만 본 issue의 직접 원인 아님 (crash 패턴은 cron timing과 무관).
3. **`_initial_*` 7개 daemon thread 동시 spawn**: 부팅 직후 메모리 압박을 가중시킬 수 있음. 다만 sleep으로 분산되어 있어 fetch_korean_stocks fix 후 영향은 작을 것으로 추정. 후속 작업 후보.
4. **Railway plan 상향 (8 → 32 GB)**: 임시방편 fix지만 4원칙(근본 원인 해결)에 위반. fetch_korean_stocks fix가 우선.

위 항목은 fix 검증이 모두 통과한 후 별도 issue로 분리해 다루는 것이 적절하다.

---

## 9. 검증 환경 메모 (작업자 setup)

### Railway CLI 설치 (Windows)
```powershell
npm install -g @railway/cli
railway --version    # 4.61.1 이상
railway login        # 브라우저 OAuth
```

### 프로젝트 link
```powershell
cd platform/server
railway link --project amiable-light
# environment: production, service: quantman 자동 선택
```

### 자주 쓸 명령
```powershell
railway status                                       # 현재 deployment + service info
railway deployment list                              # 최근 deployment 목록
railway logs -d -n 500                               # 최근 deploy log 500줄
railway logs <DEPLOYMENT_ID> -d -n 500               # 특정 deployment log
railway metrics --memory --since 24h --raw --json    # 메모리 raw time-series
railway metrics --memory --watch                     # live dashboard
```

### 주의 — 권한
`railway variables`는 production env 노출이라 Claude Code auto mode classifier가 차단함. 본 issue는 env 정보 불필요하므로 호출하지 않아도 됨.

---

## 10. 진단 요약 (참고용 timeline)

1. 사용자 보고: "새벽 3시 OOM"
2. [main.py:412-415](../../server/app/main.py) `calendars` cron이 03:00 KST에 트리거 — 1차 의심 후보로 잡혔으나 데이터로 부정.
3. Railway CLI 설치 → `metrics --memory --since 24h --raw --json` 가져옴 → MEMORY_LIMIT_GB=8.0 확정, 24h 안에 OOM 9회+ 확정 (cron timing과 무관).
4. `deployment list` → crash deployment IDs 추출 → 가장 가까운 crash deployment(`56d06873-...`)의 logs 추출.
5. **결정적 단서:** crash log에 "한국 종목 fetch 완료: 총 4288 ... Killed" — fetch 직후 OOM.
6. 코드 조사 → [data_fetcher.py:305-349](../../core/quant_core/data_fetcher.py) `fetch_korean_stocks` results dict가 4,288개 DataFrame 누적, 호출자 main.py:258은 반환값 미사용 확인.
7. Fix scope 확정.

---

**작성자:** Claude (Opus 4.7 1M, 진단 세션 2026-05-24)
**작업 디렉토리:** `C:\Users\USER\Desktop\창업\퀀트\`
**관련 회의/문서:** 없음 (이 문서가 root 진단)
