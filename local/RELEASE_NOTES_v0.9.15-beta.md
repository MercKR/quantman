## 주요 변경 — HTS ID GUI 입력 + server ETag 회귀 (별도 commit으로 배포 완료)

v0.9.14까지 HTS ID는 secrets_store에 저장 필드가 있었지만 **GUI에 입력 UI가
없어** 사실상 활성화 불가. 실시간 체결통보(KIS WebSocket H0STCNI0/H0GSCNI0)
구독이 항상 skip되고 REST 폴링 fallback으로만 동작 — 체결 인지 ~수십초 지연.

### 🆕 HTS ID 입력 필드 (gui.py wizard Step 3)

**변경**: [localapp/gui.py](localapp/gui.py)
- `_make_wizard_entry`로 "HTS ID (선택 — 실시간 체결통보용)" Entry 추가
- 입력 변경 reset 루프에 포함
- `_wizard_save`가 `secrets_store.save_kis(..., hts_id=hts_id)` 전달
- `refresh_status`에서 자격증명 헤더에 "HTS ID 미설정" 표시 (등록 안 했을 때)
- 기존 자격증명 재편집 시 hts_id 자동 채움 (`_wizard_jump_to_input`)

**왜 필요한가**:
- App key / Secret / 계좌번호는 **REST API 인증**용
- HTS ID는 **WebSocket 체결통보 구독**의 `tr_key` 필드 — KIS 사양상 필수
- 미설정 시 `intraday_loop.py:415-430`가 WS skip → REST 폴링 thread만 가동 →
  체결 인지 지연 (KIS REST가 fill 반영하는 시점까지 polling 주기 대기)
- 자금 안전엔 영향 0 (orders·intent·pending 모두 polling으로 갱신됨)

**입력 방법**:
1. GUI ① KIS 자격증명 영역 → ⚙ 변경 클릭
2. Step 3에서 HTS ID 입력 (선택)
3. 연결 테스트 → 저장

**HTS ID란**: KIS HTS 또는 영웅문 데스크탑에 로그인할 때 쓰는 **사용자 ID**
(이메일이 아닌 그 사용자명). KIS 마이페이지 → 사용자 정보에서 확인 가능.

### 🐞 별도 — Server dataset bundle ETag 304 fix (이미 배포)

오늘(5/28) 미장 22:25 cycle에서 dataset bundle이 147s 풀 다운로드 → 발주 4분
22초 지연 → 시초가 의도가 벗어남. 원인은 server가 If-None-Match를 큰따옴표
포함으로 비교(`'"<md5>"'`)하지만 client는 strip 후 송신 → 매번 mismatch.

Server commit [7712438](https://github.com/MercKR/quantman/commit/7712438)에서
양쪽 형식 모두 수용하도록 본질 fix. Railway 자동 deploy 완료.

이 release(v0.9.15)와 무관하게 모든 client가 즉시 혜택 — dataset 변경 안 됐을
때 304 + 즉시 skip으로 cycle 시작 2~3분 단축.

### 4원칙 자가검토

- **근본 원인 ✓** — HTS ID 미입력은 KIS 사양상 WS 구독 불가의 본질. 입력 UI
  제공이 본질 fix. Server ETag도 quote 불일치의 본질 (양쪽 호환).
- **Over-eng 금지 ✓** — Entry 1개 추가, save_kis 인자 1개 전달. status 표시
  1줄. 추가 추상화·옵션 0.
- **Overthinking 금지 ✓** — HTS ID 검증 별도 endpoint 없음 (KIS는 ID 유효성
  체크 API 없음). 입력 = 저장 단순 흐름.
- **검증** — 다음 미장 22:25 cycle (5/29) 또는 KRX 08:55 (6/1)에서 dataset
  304 + WS 체결통보 정상 수신 실측. 자금 안전엔 영향 0이라 즉시 release 가능.

### 내부 변경

**[localapp/gui.py](localapp/gui.py)**
- wizard Step 3: `self.e_hts = self._make_wizard_entry(f, "HTS ID (선택)")`
- 입력 reset 루프에 `self.e_hts` 추가
- `_wizard_save`에 `hts_id=self.e_hts.get().strip()` + `save_kis(..., hts_id=...)`
- `refresh_status`에서 자격증명 헤더에 "HTS ID 미설정" suffix
- 자격증명 재편집 시 `self.e_hts.insert(0, kis.get("hts_id", ""))`
- wizard 안내 문구에 HTS ID 설명 추가

**[localapp/\_\_init\_\_.py](localapp/__init__.py)**
- 버전 0.9.14-beta → 0.9.15-beta
