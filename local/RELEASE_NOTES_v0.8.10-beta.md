## 주요 변경 — DPI 흐림 fix + GUI 풀 timeline 패널

### 🔧 텍스트 흐림 해결 — Windows 고DPI awareness

**증상:** 4K 모니터·Windows 디스플레이 scaling 125%+ 환경에서 모든 텍스트가
blurry — Tkinter 기본은 96 DPI 가정 → OS가 저해상도로 렌더 후 stretching.

**Fix:** [desktop.py](desktop.py)에 `ctypes.windll.shcore.SetProcessDpiAwareness(1)`
호출 (Tk root 생성 *이전*). PROCESS_SYSTEM_DPI_AWARE 모드로 system DPI를
Tk가 인지하게. shcore 없는 구버전엔 `user32.SetProcessDPIAware()` fallback.

→ 재시작 후 모든 텍스트·아이콘 sharp 렌더.

### 🆕 GUI 풀 timeline 패널 — 웹앱과 동일 정보

이전 mini timeline(4줄)을 **웹앱 /monitor TradingTimeline과 동일 레이아웃**으로
업그레이드. hero 바로 아래에 패널 노출.

```
자동매매 상태                                    ● 정상 · 로컬앱 12초 전
─ 어제 · 2026.05.26. (화) ────────────────────────
  18:15  미장 매매 후보 결정          ✓ US 2건
─ 오늘 · 2026.05.27. (수) ────────────────────────
  07:30  국장 매매 후보 결정          ✓ KRX 5건 · US 2건
  08:55  국장 자동매매 시작           ✗ 누락
  15:35  국장 자동매매 종료           ⏳ 4h 후
  18:15  미장 매매 후보 결정          ⏳ 7h 후
  22:25  미장 자동매매 시작           ⏳ 11h 후
─ 내일 · 2026.05.28. (목) ────────────────────────
  05:05  미장 자동매매 종료           ⏳ 18h 후
  07:30  국장 매매 후보 결정          ⏳ 20h 후
  08:55  국장 자동매매 시작           ⏳ 22h 후
```

**구현:**
- 서버 신규 endpoint [`GET /sync/timeline`](server/app/routers/sync.py)
  (device-authed mirror of `/trading/timeline`).
- 로컬 [`sync_client.pull_timeline()`](localapp/sync_client.py) 추가.
- GUI [`SettingsApp._render_timeline`](localapp/gui.py) — 어제·오늘·내일 그룹 +
  6 종류 event(국장/미장 × 후보결정·시작·종료) + status icon + hover tooltip.
- 매 60s 자동 갱신 (`_schedule_minute_tick`).

**웹·로컬 동일 단일 출처**: 서버 trading.py의 `_krx_events`·`_us_events`·
`_preview_events` 헬퍼를 두 endpoint(`/trading/timeline`·`/sync/timeline`)
모두 재사용 — 표시 결과 항상 일치.

### v0.8.9 사용자 자동 업데이트

v0.8.9의 focus event 기반 update check가 GitHub에 v0.8.10 publish 직후 감지 →
amber 배너 → [지금 업데이트] 클릭으로 자동 적용.

업데이트 후 hero에 `v0.8.10-beta · floo.korea@gmail.com` 표시되면 정상 install.
