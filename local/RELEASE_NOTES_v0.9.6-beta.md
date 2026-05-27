## 주요 변경 — Hotfix: bundle 적용 후 universe 자동 등록 (매수 0건 영구 원인 fix)

### 🐞 사용자 발견 사건 (2026-05-28 KST 00:30)

증상: v0.9.5-beta 적용 후 dataset bundle download 정상(4468 parquet) +
서버 preview candidates=6 정상 + catch-up cycle 호출 정상 — 그런데 **trader가
모든 후보 종목에 `skip_no_data: "전일 종가 없음 — dataset에 없음"`**.

진단:
```python
qc.load_dataset()  →  total symbols: 51   ← 4459 parquet 있는데 51개만!
"AAPL" in dataset  →  False
"AMD" in dataset   →  False
```

### 원인 — Client universe ↔ server bundle 단절 (PR-2·PR-4 위반)

`core.data_fetcher.load_all()`은 **화이트리스트 기반 종목 로드**:
- `ALL_SYMBOLS` (macro 51개)
- `load_user_stocks()` (사용자 수동 등록)
- `load_managed_kr_codes()` (KRX 자동 등록)
- `load_managed_overseas()` (해외 자동 등록)

`fetch_dataset_bundle`은 4468 parquet을 `data/`에 풀어 저장하지만 **universe
json을 갱신하지 않음**. → 디스크에 AAPL.parquet 있어도 `managed_overseas` json에
"AAPL"이 등록 안 됐으면 `load_all()`이 무시 → dataset dict에 미포함 →
trader가 `dataset.get("AAPL")` = None → skip_no_data.

오늘 사용자 PC: `managed_kr_stocks.json`·`managed_overseas_stocks.json` 둘 다 부재.

PR-2 (Over-engineering): server가 풍부한 dataset 발행하는데 client가 별도
화이트리스트로 또 거름. 두 출처 sync 보장 없음 — single source of truth 원칙 위반.
PR-4 (검증 누락): bundle apply 후 "load_dataset이 실제로 그 종목들 로드하는지"
검증 없음.

### Fix — `fetch_dataset_bundle`이 universe json 자동 갱신

bundle 풀면서 `extracted_symbols` 수집 → KRX(6자리 숫자) / overseas(영문 ticker)로
분류 → `save_managed_kr_codes`·`save_managed_overseas` 자동 호출.

이후 `load_all()`이 디스크의 모든 bundle 종목을 universe에 포함 → trader가
prev_close 정상 조회 가능.

### v0.9.5 사용자 임시 unblock (v0.9.6 받기 전)

PC에서 한 번만:
```bash
python -c "
import os, json
d = os.path.expanduser('~/.quant-platform/data')
kr, ov = [], []
for f in os.listdir(d):
    if not f.endswith('.parquet'): continue
    sym = f[:-8]
    if sym.isdigit() and len(sym) == 6:
        kr.append(sym)
    elif sym[0].isalpha():
        ov.append({'code': sym, 'name': sym})
json.dump(kr, open(os.path.join(d, 'managed_kr_stocks.json'), 'w'),
          ensure_ascii=False, indent=2)
json.dump(ov, open(os.path.join(d, 'managed_overseas_stocks.json'), 'w'),
          ensure_ascii=False, indent=2)
print('OK:', len(kr), 'KRX +', len(ov), 'overseas')
"
```
실행 후 자동매매 재시작 → catch-up 정상 매수 시도.

v0.9.6-beta 자동 업데이트 받으면 위 임시 script 없이 bundle apply마다 자동 등록.

### 내부 변경

**[localapp/sync_client.py](localapp/sync_client.py)** — `fetch_dataset_bundle`:
- bundle 풀면서 `extracted_symbols` 수집
- `save_managed_kr_codes`·`save_managed_overseas` 호출 (macro symbol 제외)
- `log.info("universe 자동 등록 — KRX X종목 · Overseas Y종목")`

**[localapp/__init__.py](localapp/__init__.py)**:
- 버전 0.9.5-beta → 0.9.6-beta
