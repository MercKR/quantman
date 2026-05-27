## 주요 변경 — Hotfix: Auto-updater 좀비 인스턴스·:FAIL 결함 fix

### 🐞 사용자 발견 사건 (2026-05-28 KST 02:33)

v0.9.6-beta → v0.9.7-beta 자동 업데이트 시도 시 **"그냥 종료되고 업데이트 안 됨"**.
사용자는 amber 배너 [지금 업데이트] 클릭 후 16번 재시도 → 임시 폴더 16개 누적.

### 원인 — 3가지 결함이 연쇄

진단 (PID/parent tree + robocopy log 확인):

| # | 결함 | 본질 |
|---|---|---|
| 1 | `taskkill /F /PID <one_pid>` 단일 PID만 kill | `single_instance.acquire()` 실패 시 띄우는 `mb.showinfo` 좀비 dialog 인스턴스(다른 PID)가 `.exe`·`.dll` 메모리 매핑 유지 → robocopy 무한 retry → 사용자가 "멈춤"으로 인식 |
| 2 | `mb.showinfo` blocking modal → 좀비 영구 잔존 | 사용자가 [확인] 안 누르면 process 안 죽음 → .exe 클릭마다 좀비 1개씩 누적 → DLL 잠금도 누적 |
| 3 | `:FAIL` 분기에서 `rmdir`이 MessageBox **전에** 실행 + robocopy `/R:30 /W:2` retry 60s/파일 | 사용자가 그 사이 강제 종료 → :FAIL 도달 못 함 → MessageBox 미출력 + 임시 폴더 누적 |

### Fix

#### A) `_write_updater_bat` — image name + tree로 모든 인스턴스 kill

[localapp/updater.py](localapp/updater.py)
```python
# 옛 (v0.9.7-beta까지)
f'taskkill /F /PID {parent_pid} > nul 2>&1\r\n'

# 새 (v0.9.8-beta)
f'taskkill /F /IM "{app_exe.name}" /T > nul 2>&1\r\n'
```

`/IM` = 이미지 이름 (모든 인스턴스), `/T` = process tree 통째. 좀비 dialog까지 일소.
함수 시그니처에서 `parent_pid` 파라미터 제거, 호출자에서 `os.getpid()` 인자 제거.

#### B) `single_instance` 좀비 dialog 5초 자동 종료

[desktop.py](desktop.py)
```python
# 옛
mb.showinfo("퀀트 플랫폼", "로컬앱이 이미 실행 중입니다.")  # blocking 모달

# 새
_show_already_running_dialog()  # tk root + after(5000, root.destroy)
```

사용자가 [확인] 안 눌러도 5초 후 process 자가 종료 → 좀비 누적 차단.

#### C) `:FAIL` 분기 — MessageBox 먼저, rmdir 나중 + 경로 안내

[localapp/updater.py](localapp/updater.py)
- `robocopy /R:30 /W:2` → `/R:5 /W:1` (60s → 10s per file). /IM /T kill 후 잠금
  풀려있을 게 정상이므로 길게 retry할 이유 없음. 실패면 즉시 사용자에게 알림이 옳음.
- `:FAIL` 순서 swap — MessageBox 띄움이 먼저, src 폴더 정리는 나중.
- fail_msg에 src 경로 명시 → 사용자가 수동 설치 가능.

#### D) `_cleanup_stale_update_dirs` — 24h 이상 임시 폴더 정리

[desktop.py](desktop.py)
```python
def _cleanup_stale_update_dirs() -> None:
    cutoff = time.time() - 86400
    for p in glob.glob(os.path.join(tempfile.gettempdir(), "quantman-update-*")):
        if os.path.getmtime(p) < cutoff:
            shutil.rmtree(p, ignore_errors=True)
```

`main()` 시작 시 호출. updater :FAIL 또는 강제 종료 시 누적 방지 (이전 16개 누적 사례).

### PR-1 정당화 — 외부 시스템 한계만

PyInstaller `--onedir` 모드 + Windows file lock 동작은 우리가 바꿀 수 없는 외부 시스템.
- A) `/IM /T` — Windows taskkill의 표준 옵션 (image name + tree).
- C) `/R:5` — 외부 잠금이 진짜로 풀릴 거면 5초 안에 풀린다는 휴리스틱 (PyInstaller bootloader가 child 종료 후 잠금 푸는 데 보통 ~1초).

### 4원칙 자가검토

- **근본**: ✓ 좀비 누적·PID-only·`:FAIL` 순서 모두 *원인*을 고침 (증상 봉합 아님).
- **Over-eng 금지**: ✓ 새 옵션·플래그 0개. `parent_pid` dead 파라미터 제거.
- **Overthinking 금지**: ✓ taskkill 한 줄 + tk after(5000) + glob/shutil 5줄. 다단 계층 없음.
- **검증**: 빌드 후 직접 update 시도 → robocopy log·MessageBox·5초 dialog 모두 실측.

### 내부 변경

**[localapp/updater.py](localapp/updater.py)**
- `_write_updater_bat`: `parent_pid` 파라미터 제거, `/IM /T` kill, `/R:5 /W:1` retry, `:FAIL` 순서 swap, fail_msg에 src 경로 추가.
- `perform_update`: `os.getpid()` 인자 제거, `import os` 정리.

**[desktop.py](desktop.py)**
- `_cleanup_stale_update_dirs()` 신규 — 24h 이상 임시 폴더 정리.
- `_show_already_running_dialog()` 신규 — 5초 timeout 자가 종료 dialog.
- `main()`: 두 함수 호출 추가, `mb.showinfo` 제거.

**[localapp/__init__.py](localapp/__init__.py)**
- 버전 0.9.7-beta → 0.9.8-beta
