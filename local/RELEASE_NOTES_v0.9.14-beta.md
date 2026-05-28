## 주요 변경 — macOS tray crash 본질 fix (1건)

v0.9.0~v0.9.13 macOS 빌드는 트레이 아이콘이 메인 스레드 외에서 실행돼
**즉시 SIGTRAP crash**. 실제 macOS 사용자에겐 자동매매 가동 불가 상태였다.

### 🐞 macOS tray crash

**증상**: macOS에서 .app 실행 직후 즉시 종료. Console.app·시스템 crash
report에 `NSUpdateCycleInitialize() is called off the main thread` 메시지.
macOS 26.4+에서 엄격 적용 — 이전 버전에선 묵인되다 최신 macOS가 강제 종료.

**원인**: `tray.py:TrayApp.run`이 `threading.Thread(target=self.icon.run,
daemon=True).start()`로 트레이 아이콘을 데몬 스레드에서 구동.
pystray macOS backend(`_darwin`)는 AppKit/NSStatusItem 기반이고, AppKit은
**반드시 메인 스레드에서 동작**해야 한다. 데몬 스레드에서 `icon.run()` 호출 →
NSUpdateCycleInitialize가 off-main-thread 감지 → SIGTRAP.

Windows/Linux는 backend(pystray._win32/Xlib)가 thread-safe이라 daemon
스레드에서도 정상 — OS별 분기 필요.

**해결**: [localapp/tray.py](localapp/tray.py)
- macOS: `self.icon.run_detached()`로 NSStatusItem 등록만 + tkinter mainloop
  (메인 스레드)가 공유 NSApplication 런루프를 대신 구동
- Windows/Linux: 기존 daemon thread + `icon.run()` 그대로 유지

```python
def run(self):
    if sys.platform == "darwin":
        self.icon.run_detached()
        self.app.run()
    else:
        threading.Thread(target=self.icon.run, daemon=True).start()
        self.app.run()
```

**검증**: 본 fix는 fork(heuije/quantman `macos-tray-fix` 브랜치, commit
`b21bcc9`)에서 macOS 26.4.1(arm64) 소스 실행 + PyInstaller 번들 모두 정상
상주 확인된 상태. 동일 patch를 우리 main에 적용.

### 4원칙 자가검토

- **근본 원인 ✓** — AppKit 메인스레드 제약은 OS 수준 강제. 데몬 스레드는
  Windows/Linux pystray backend 가정으로 작성된 옛 코드라 macOS에서 잘못된
  스레딩 모델. 본질 fix는 OS별 분기.
- **Over-eng 금지 ✓** — 단일 함수 1 if/else 분기. 추가 옵션·계층 0.
- **Overthinking 금지 ✓** — Windows/Linux는 무변경. macOS만 `run_detached()`로
  교체. 단순.
- **검증 ✓** — fork가 macOS 26.4.1에서 소스·번들 둘 다 실측. 우리 build CI는
  macOS 빌드 자체는 v0.9.13까지 성공해왔으므로 spec/workflow 검증은 끝.
  남은 검증: 사용자 PC에서 v0.9.14 macOS zip 실행 확인.

### 내부 변경

**[localapp/tray.py](localapp/tray.py)**
- `import sys` 추가
- module docstring 갱신 — OS별 스레드 모델 명시
- `TrayApp.run`에 `sys.platform == "darwin"` 분기

**[localapp/\_\_init\_\_.py](localapp/__init__.py)**
- 버전 0.9.13-beta → 0.9.14-beta

### Windows 영향

Zero — `sys.platform == "darwin"` 분기 안에만 변경. else 분기는 기존 코드
identical. v0.9.13 → v0.9.14 update는 Windows 사용자에게 no-op이지만
amber 배너 + auto-update 흐름은 정상.
