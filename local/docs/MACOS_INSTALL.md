# macOS 설치 가이드 (Apple Silicon)

> **대상**: M1·M2·M3·M4 Mac (Apple Silicon). Intel Mac은 지원하지 않습니다.
> **macOS 요구사항**: Sonoma 14.0 이상.

## ⚠️ 미서명 앱 — 첫 실행만 다른 절차

이 앱은 **코드 서명되어 있지 않습니다** (Apple Developer Program 미가입).
첫 실행 시 macOS Gatekeeper가 "확인되지 않은 개발자" 경고를 띄웁니다.

**그냥 더블클릭하면 안 열립니다.** 아래 둘 중 하나로 첫 실행하면, 다음부터는
일반 더블클릭으로 정상 실행됩니다.

---

## 방법 1 — Finder (권장)

1. [최신 release](https://github.com/MercKR/quantman-releases/releases/latest)에서
   `QuantPlatformLocal-vX.Y.Z-macos-arm64.zip` 다운로드.
2. zip 더블클릭 → `QuantPlatformLocal-vX.Y.Z.app` 생성.
3. 생긴 `.app`을 **`/Applications` 폴더로 드래그**해 옮김.
4. **Finder에서** `/Applications/QuantPlatformLocal-vX.Y.Z.app`에 **마우스 우클릭** → **[열기]**.
5. 경고 dialog의 **[열기]** 버튼 클릭. (그냥 더블클릭하면 [취소]만 가능 — 우클릭이 핵심.)
6. 다음부터는 더블클릭·Dock·Spotlight 어떤 방식으로든 실행 가능.

## 방법 2 — Terminal 한 줄

zip 압축 해제 후 `/Applications`로 옮긴 다음 터미널에서:

```bash
xattr -dr com.apple.quarantine /Applications/QuantPlatformLocal-vX.Y.Z.app
```

이후 더블클릭으로 그냥 열립니다. (위 명령은 quarantine 속성을 제거 — Gatekeeper가
"인터넷에서 받은 앱"으로 인식하지 않게 합니다.)

---

## 🔑 KIS Keychain 권한 — "항상 허용" 필수

앱 첫 실행 후 KIS 자격증명을 wizard에서 저장·로드할 때 macOS Keychain prompt가
표시됩니다:

> "QuantPlatformLocal에서 키체인 항목 'kis_credentials'에 접근하려고 합니다"

**반드시 [항상 허용]을 클릭하세요.**

[허용] (한 번만)을 누르면 다음 자동매매 cycle에서 또 prompt가 뜨는데, **새벽
8:55 KOR 자동 진입 cycle은 사용자가 자고 있는 동안 동작**하므로 prompt에 응답
못 해 매매 실패로 이어집니다.

만약 실수로 [허용]만 눌렀다면 키체인 접근.app(Keychain Access)에서:
1. 검색창에 `quant-platform-local` 입력
2. 항목 더블클릭 → [접근 제어] 탭 → [이 항목을 사용할 때 인증되지 않은 모든 응용 프로그램 허용] 체크 (또는 QuantPlatformLocal을 [항상 허용 목록]에 추가).

---

## 자동 업데이트

앱이 부팅·focus 시 GitHub release를 polling해 새 버전 안내 배너를 띄웁니다.
[지금 업데이트] 클릭 시:
1. 새 .app zip 자동 다운로드.
2. 앱 종료.
3. 백그라운드 shell script가 기존 .app을 새 .app으로 교체.
4. `xattr -dr com.apple.quarantine` 자동 실행 (Gatekeeper 재경고 방지).
5. 새 .app 자동 실행.

**업데이트 후에도 정상 실행되지 않으면** 위 "방법 2" 명령을 한 번 더 실행하세요.

---

## 알려진 제약

- **메뉴바 트레이 아이콘**: pystray의 macOS backend 제약으로 dark menubar에서 약간
  흐릿하게 보일 수 있습니다. 클릭은 정상 동작.
- **창 닫기 동작**: Windows와 동일 — 빨간 버튼으로 닫아도 백그라운드에서 스케줄러가
  계속 동작. 완전 종료는 메뉴바 트레이 → [종료] 또는 Dock 우클릭 → [종료].

## 문제 보고

[GitHub Issues](https://github.com/MercKR/quantman-releases/issues)에 macOS
환경 정보 (모델·OS 버전·앱 버전)와 함께 알려주세요.
