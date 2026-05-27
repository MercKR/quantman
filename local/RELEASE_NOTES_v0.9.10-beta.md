## 주요 변경 — Hotfix: updater bat이 자기 자신을 죽이는 결함

### 🐞 사용자 발견 사건 (2026-05-28 KST 04:06)

v0.9.8 → v0.9.9 update 시도가 또 실패. 사용자: "설치 완료되는 듯하더니 꺼졌습니다.
다시 켰더니 여전히 업데이트가 안되어있어서 다시 업데이트 시도했으나 똑같이 꺼졌습니다."

진단:
- 임시 폴더는 정상 생성·압축 풀기까지 완료 (extracted/QuantPlatformLocal-v0.9.9-beta/).
- 그러나 **`%TEMP%/quantman-update.log`가 03:43:55 옛 시점 그대로** — 새 update의
  robocopy 로그가 갱신 안 됨 = **robocopy 자체가 실행 안 됨**.
- `.exe` mtime도 v0.9.8 GitHub Actions 빌드 시점 그대로 → 교체 0건.

### 원인 — `/T` 옵션이 self-kill을 야기

v0.9.8의 새 updater.bat:
```cmd
taskkill /F /IM "QuantPlatformLocal.exe" /T
```

`/T` = process **tree** 통째 kill. 그런데 흐름:
1. `.exe`(메인 앱)가 `perform_update()` 호출
2. `subprocess.Popen(["cmd.exe", "/c", bat_path], ...)`로 cmd.exe spawn
3. **cmd.exe는 .exe의 child** (process tree 관계)
4. cmd.exe가 updater.bat 실행 시작
5. bat 첫 줄 `taskkill /F /IM ... /T` 실행
6. taskkill이 `.exe` 죽일 때 **/T로 child인 cmd.exe도 함께 죽임**
7. **cmd.exe self-kill → bat 즉시 종료** (robocopy 도달 못 함)
8. .exe 교체 없이 모두 종료 → 사용자에겐 "꺼졌다"로 보임

### Fix — `/T` 제거

[localapp/updater.py](localapp/updater.py)
```python
# 옛 (v0.9.8-beta·v0.9.9-beta)
f'taskkill /F /IM "{app_exe.name}" /T > nul 2>&1\r\n'

# 새 (v0.9.10-beta)
f'taskkill /F /IM "{app_exe.name}" > nul 2>&1\r\n'
```

`/IM <name>`만으로 **같은 이미지 이름의 모든 인스턴스** kill (좀비 dialog 포함).
- PyInstaller `--onedir` + `console=False`는 single process — child kill 불필요.
- 좀비 dialog도 같은 .exe 이미지라 `/IM` 만으로 잡힘.
- `/T`는 over-eng + cmd.exe(bat 실행 중) self-kill 유발.

### 4원칙 자가검토

- **근본 원인**: ✓ `/T`의 self-kill 부작용을 정확히 진단·제거. 증상 봉합 아님.
- **Over-eng**: ✓ `/T` 자체가 over-eng였음을 인지·제거.
- **Overthinking**: ✓ taskkill 한 줄 수정. detached subprocess.Popen 옵션이나
  bat 자체 re-spawn 같은 복잡한 대안 회피.
- **검증**: 사용자 PC에서 v0.9.9 → v0.9.10 update 시 robocopy 실행 + .exe 교체
  + 새 .exe 시작 모두 확인.

### 영향 (regression 사슬)

| Release | 결함 | Fix |
|---|---|---|
| v0.9.7까지 | `taskkill /F /PID <one_pid>` — 좀비 dialog 못 잡음 | v0.9.8 `/IM /T` 도입 |
| v0.9.8 | `/T` self-kill — bat이 robocopy 도달 못 함 | v0.9.10 `/T` 제거 |

v0.9.7 → v0.9.8 update 시점에는 옛 (PID-only) updater가 동작해서 robocopy까지
도달은 했지만(/IM 없어서 일부 lock 남음), v0.9.8 → v0.9.9는 새 (/IM /T) updater가
self-kill로 robocopy 시작도 못 함.

v0.9.10이 v0.9.8 코드의 정확한 fix.

### 내부 변경

**[localapp/updater.py](localapp/updater.py)**
- `_write_updater_bat`: `taskkill /F /IM "{app_exe.name}" /T` → `taskkill /F /IM "{app_exe.name}"` (T 제거).
- 함수 docstring에 v0.9.10 결함 진단·fix 명시.

**[localapp/__init__.py](localapp/__init__.py)**
- 버전 0.9.9-beta → 0.9.10-beta
