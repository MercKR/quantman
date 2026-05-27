## 주요 변경 — macOS Apple Silicon 지원 (베타)

### 🆕 macOS 빌드 신규 (Apple Silicon)

v0.9.0-beta부터 macOS Apple Silicon (M1·M2·M3·M4)에서도 동작.
**최소 요구사항**: macOS Sonoma 14.0+.

설치 가이드: [docs/MACOS_INSTALL.md](https://github.com/MercKR/quantman/blob/main/platform/local/docs/MACOS_INSTALL.md)

**중요 — 미서명 빌드 안내** (Apple Developer Program 미가입):
1. zip 다운로드 후 압축 해제 → `.app`을 `/Applications`로 이동
2. Finder에서 `.app` **우클릭 → [열기]** (첫 실행만, 더블클릭은 차단됨)
3. KIS wizard에서 자격증명 입력 후 Keychain prompt가 뜨면 **반드시 [항상 허용]** 클릭
   ([허용]만 누르면 새벽 자동매매 cycle에서 다시 prompt → 실패)

터미널 대안: `xattr -dr com.apple.quarantine /Applications/QuantPlatformLocal-v0.9.0-beta.app`

### 🆕 자동 업데이트 — platform-aware asset 선택

기존 updater는 release의 첫 zip asset을 그대로 다운로드.
v0.9.0-beta부터 release zip 이름에 platform suffix:
- Windows: `QuantPlatformLocal-vX.Y.Z-windows.zip`
- macOS arm64: `QuantPlatformLocal-vX.Y.Z-macos-arm64.zip`

updater가 `sys.platform`으로 자기 플랫폼 asset만 선택.
v0.8.x → v0.9.0-beta 업데이트는 Windows 사용자에게 정상 동작 (suffix 매칭 +
하위 호환 fallback 둘 다 구현).

### 🆕 GitHub Actions CI 빌드 파이프라인

수동 PyInstaller 빌드 → GitHub Actions workflow로 자동화.
- `windows-latest` runner: Windows zip
- `macos-14` runner (Apple Silicon): `.app` zip (ditto 압축으로 resource fork 보존)
- 트리거: tag push (`v*.*.*`, `v*-beta`) 자동 + workflow_dispatch 수동
- Release publish: 같은 workflow의 `publish` job이 `MercKR/quantman-releases`에
  cross-repo upload (RELEASES_PAT secret 필요)

### 내부 변경

**[QuantPlatformLocal.spec](QuantPlatformLocal.spec)**:
- `IS_MAC = sys.platform == "darwin"` 분기
- macOS hiddenimports: `pystray._darwin`, `keyring.backends.macOS`
- EXE에 `target_arch="arm64"` (Apple Silicon)
- `BUNDLE` 블록 추가 — `.app` bundle 생성, Info.plist with bundle_identifier·
  CFBundleShortVersionString·NSHighResolutionCapable·LSMinimumSystemVersion 14.0

**[localapp/updater.py](localapp/updater.py)**:
- `_select_platform_asset` 신규 — platform suffix 매칭, mac에서 suffix 없는
  zip은 거부 (Windows binary 잘못 받기 방지)
- `_app_root_and_exe` macOS 분기 — `.app` bundle root 반환 (exe.parent ×3)
- `_write_updater_sh` 신규 — bash script: 3초 대기 → rsync → `xattr -dr
  com.apple.quarantine` (Gatekeeper 재경고 방지) → open
- `perform_update`에서 mac/win 분기, mac은 `start_new_session=True`로 detached

### Windows 사용자 영향

**영향 zero**. spec·updater 변경은 모두 `sys.platform == "darwin"` 가드 안에서만
동작. v0.8.11 → v0.9.0-beta 자동 업데이트 흐름 동일.

### v0.8.11 사용자 자동 업데이트

v0.8.11의 focus event update check가 v0.9.0-beta publish 직후 감지 → amber 배너 →
[지금 업데이트] 클릭으로 자동 적용. 업데이트 후 hero `v0.9.0-beta` 확인.
