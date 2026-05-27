## 주요 변경 — Hotfix: dataset bundle 다운로드 영구 실패 fix

### 🐞 v0.9.0~v0.9.4 회귀 — 자동매매 후보 있어도 **매수 0건 영구 누적**

증상: 자동매매 시작·catch-up 동작 → 후보 6건 평가됐지만 모든 종목 `skip_no_data`:
```
{"action":"skip_no_data","symbol":"AAPL","reason":"전일 종가 없음 — 매수 대상 종목이 dataset에 없음 (서버 dataset 갱신 대기)"}
```

진범: `sync_client.fetch_dataset_bundle`이 서버 dataset bundle을 받지 못하고
**영구 디코드 실패**:
```
WARNING localapp.datafetch dataset sync 실패 — 기존 로컬 캐시로 진행:
  zstd decompress error: Unknown frame descriptor
```

서버는 정상 (154MB tar.zst, 4,468 parquet, AAPL·AMD·GOOGL·TSLA 다 포함).
검증으로 같은 PC에서 파일 통째 받아 디코드 → 328MB 정상 추출.

### 진짜 원인 — `r.raw` stream + Transfer-Encoding chunked 충돌

```
Railway 서버 응답:
  Content-Type: application/zstd
  Transfer-Encoding: chunked   ← 핵심
                ↓
requests.get(stream=True).raw 의 raw bytes에 chunk header (hex digit + CRLF)
가 포함된 채 노출됨
                ↓
zstandard.stream_reader(r.raw) → zstd magic (28 b5 2f fd) 앞에 chunk hex가
끼어 "Unknown frame descriptor" 영구 실패
                ↓
로컬 캐시 (stale, US 종목 없음) fallback → trader가 prev_close 못 찾음
                ↓
매수 후보 신호 통과해도 모두 skip_no_data → 매수 0건
```

4원칙 위반: PR-4 (검증 누락). `stream=True` + `r.raw` 패턴이 chunked
transfer encoding에 동작 안 되는 걸 빌드 시 통합 검증 안 함. v0.9.0부터
US 종목 추가된 시점부터 모든 사용자가 dataset 미적용 상태였음.

### Fix — chunk를 임시 파일로 받은 후 디코드 ([sync_client.py:38](localapp/sync_client.py))

```python
# 변경 전: 깨진 stream 직접 디코드
with dctx.stream_reader(r.raw) as zr, tarfile.open(fileobj=zr, mode="r|") as tar:
    ...

# 변경 후: 임시 파일 경유 (chunked transfer 안전)
with tempfile.NamedTemporaryFile(delete=False, suffix=".zst") as tmp:
    for chunk in r.iter_content(chunk_size=1024 * 1024):
        if chunk:
            tmp.write(chunk)
    tmp_path = tmp.name
try:
    with open(tmp_path, "rb") as f, \
            dctx.stream_reader(f) as zr, \
            tarfile.open(fileobj=zr, mode="r|") as tar:
        ...
finally:
    if tmp_path and os.path.exists(tmp_path):
        os.unlink(tmp_path)
```

`iter_content`가 chunked transfer를 transparent 해제하므로 임시 파일엔
순수 zstd payload만 저장. 그 다음 디스크 파일을 stream_reader에 넘기면
안전. 154MB이라 메모리에 안 올리고 디스크 경유 → CI·Windows·macOS 모두 안전.

### 사용자 영향

- v0.9.0~v0.9.4 사용자: 매수 후보 있어도 매수 0건이었던 게 본 release로 해결
- 자동 catch-up이 dataset 정상 적용 후 prev_close 확보 → 시초가 limit 변환 발주 가능

### 자동 업데이트

v0.9.3-beta의 강화된 updater가 본 release 감지 → amber 배너 → [지금 업데이트]
1회로 v0.9.5-beta 자동 적용.

### 내부 변경

**[localapp/sync_client.py](localapp/sync_client.py)**:
- `fetch_dataset_bundle`이 `r.iter_content`로 chunk를 임시 파일로 받은 후
  `dctx.stream_reader(file)`로 디코드. `tempfile.NamedTemporaryFile` 사용.
- `finally` 블록에서 임시 파일 cleanup 보장.

**[localapp/__init__.py](localapp/__init__.py)**:
- 버전 0.9.4-beta → 0.9.5-beta
