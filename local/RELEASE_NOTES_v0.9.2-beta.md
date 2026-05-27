## 주요 변경 — Hotfix: '자동매매 시작' 버튼 무동작 fix

### 🐞 v0.9.0~v0.9.1 회귀 — `ModuleNotFoundError: No module named 'websocket'`

증상: GUI에서 **'자동매매 시작' 버튼을 눌러도 아무 반응 없음**. 로그에도
에러 흔적 없음. 사용자는 클릭이 무시되는 것처럼 보임.

원인 (4원칙 PR-1·PR-4 위반):
- `intraday_loop.py` → `kis_order_websocket.py` → `import websocket` 경로가
  v0.9.0에서 GUI mode `register_jobs` 흐름에도 활성화됐다.
- 그런데 `requirements.txt`에 `websocket-client`가 **명시되지 않음** —
  dev 머신엔 transitive로 설치돼 있어 그동안 안 드러남.
- CI(GitHub Actions windows-latest)에선 누락 → PyInstaller가 번들에 포함 못함
  → 사용자 exe 실행 시 import 실패.
- PyInstaller `--noconsole` 빌드는 stderr를 어디에도 안 흘려보내 traceback이
  사용자·로그 양쪽에서 invisible → silent fail.

### Fix

**[platform/local/requirements.txt](platform/local/requirements.txt)**:
- `websocket-client>=1.6` 명시 (KIS 체결통보 WebSocket)
- `cryptography>=42.0` 명시 (KIS WebSocket AES 복호화 — 같은 잠재 risk)
- `zstandard>=0.22` 명시 (dataset 압축해제 — `localapp.datafetch`가 이미 사용
  중인데 누락돼 `WARNING dataset sync 실패 — No module named 'zstandard'`
  로그를 매번 찍고 있었음)

**[platform/local/QuantPlatformLocal.spec](platform/local/QuantPlatformLocal.spec)**:
- `collect_all` 대상에 `websocket` 추가 (belt-and-suspenders).

### 영향

- v0.9.0·v0.9.1 사용자: 자동매매 시작 버튼 자체가 동작 안 했으므로 **즉시 업데이트
  강력 권장**. 업데이트 후 버튼이 정상 동작.
- v0.8.x 사용자: GUI mode가 cron 일부만 register하던 시절이라 우연히 영향 없었음.
  v0.9.x 흐름 활성화 시 영향 있을 수 있으니 업데이트 권장.

### 검증

- dev 머신에서 `register_jobs` + `sched.start()`까지 import 체인 정상 동작 확인.
- stderr 캡쳐 모드로 v0.9.1-beta 재현: `ModuleNotFoundError: No module named 'websocket'`
  발생 확인 → requirements 추가 후 사라짐.

### 별건

`zstandard` 누락은 dataset bundle 갱신을 무력화하던 잠재 회귀. v0.9.2-beta에서
함께 fix되어 로컬앱이 서버 dataset 갱신을 다시 정상 수신.
