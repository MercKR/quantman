## 주요 변경 — 타임라인 전면 개편 + 종료시각 표시 + 시장별 후보 결정 분리

### 🆕 자동매매 라벨 친화화 + 시작·종료 둘 다 표시

이전 "KRX 사이클·US 사이클" → 사용자 친화적 이름으로:

| 시각 | 라벨 |
|---|---|
| 07:30 KST | **국장 매매 후보 결정** (전날 US 종가 반영) |
| 08:55 KST | **국장 자동매매 시작** (주문 발주) |
| 15:35 KST | **국장 자동매매 종료** (미체결 정리·잔고 reconcile) |
| 18:15 KST | **미장 매매 후보 결정** (오늘 KRX 종가 반영) |
| 22:25 KST (DST) / 23:25 (Std) | **미장 자동매매 시작** |
| 05:05 KST 다음날 (DST) / 06:05 (Std) | **미장 자동매매 종료** |

### 🆕 누락 원인 자동 진단 + 다음 작업 영향 분석

이전엔 "누락"이 일률적으로 "로컬앱 실행 중 아니었거나 grace 초과"로 표시 —
사용자가 진짜 원인을 알 수 없었음. 이제 **4가지 case 자동 구분 + 다음 작업
영향까지 hover로 노출**:

- **A. 앱 OFF**: heartbeat 부재 → "PC 종료·앱 종료·네트워크 단절"
- **B. cycle 미발동**: heartbeat alive였으나 push 없음 → "cron 미등록·grace 초과·KIS 점검 시간대"
- **C. cycle 실행 실패**: snapshot 존재하지만 error 마커 → KIS API 응답 등 구체 오류
- **D. push 실패**: 서버 측 구분 불가, 일단 A/B로 흡수

각 누락 옆 hover 시 예시:
```
✗ 22:25 미장 자동매매 시작  →  누락
  ↳ 로컬앱은 alive였으나 cycle이 발동되지 않았습니다 (cron 미등록·grace 초과·
    KIS 점검 시간대 가능성).
    → 오늘 미장 신규 매수 0건, 보유 US 종목 청산 평가 누락. 다음 미장 cycle은
      캘린더상 다음 거래일 open-5min.
```

**구현:**
- 서버: `HeartbeatEvent` table 추가, 매 ping마다 row 1개 기록 (latest 1건만
  유지하던 이전 방식으론 과거 임의 시점 alive 판정 불가).
- 서버: `_classify_missed`가 heartbeat history + snapshot error 마커로 A/B/C 분류.
- 로컬앱: `run_cycle`이 예외 발생 시 error snapshot을 서버에 push (이전엔 예외
  propagate해 서버가 그냥 push 없음만 봐서 case C 추적 불가).

### 🆕 시장별 매매 후보 결정 분리

이전엔 "매매 후보 결정 18:15" 하나로 표시했는데, 실제 서버 cron은 **하루에
두 번** 결정합니다:

- **07:30 KST** — yfinance/FRED publish 직후. *전날 미국 종가·S&P500·VIX·매크로
  반영* → 국장 cycle(08:55)이 이 후보 사용. "S&P 500이 X 이상이면 KRX 매수"
  같은 전략이 fresh US 종가를 정확히 사용한다.
- **18:15 KST** — KRX 종가·NAVER·technical·parquet 영구 저장 직후 (webhook
  발송 시점) → 미장 cycle(22:25)이 이 후보 사용. *오늘 KRX 종가 반영*.



v0.8.8에서 mini timeline 구현은 들어갔는데 placement 버그로 화면에 안 보였음.
또 사용자가 "웹앱에는 누락 cycle 알림 보이는데 로컬앱은 왜 없냐"고 지적 — 같이 보강.

### 🐛 mini timeline placement fix

**증상:** v0.8.8 로컬앱에서 "다음 자동매매" 카드가 안 보임.

**원인:** [gui.py:201](localapp/gui.py:201)의 `next_frame`이 `_build`에서
.pack() 안 부르고 `refresh_status`에서만 호출. Tk pack은 호출 순서대로 배치
하므로, 다른 모든 위젯(setup_bar·kf·pf·af 등)이 먼저 packed된 *후* next_frame이
packed → root 가장 아래(스크롤 영역 밖) 위치 → 사용자 눈에 안 보임.

**Fix:** `_build`에서 hero 직후 미리 .pack()으로 위치 확보 + `pack_forget()`
으로 일단 숨김. `refresh_status`의 repack은 `after=self.hero` 옵션으로 위치 강제.

### 🆕 누락 cycle 알림

**기능:** hero 아래 mini timeline 카드에 빨간색 1줄 추가 — 오늘 예정 cycle이
지났는데 cycles.jsonl에 기록 없으면:

```
⚠ 오늘 누락된 cycle: KRX
```

판정 로직: KRX 평일 08:55, US는 캘린더에서 24시간 안의 직전 세션 open-5분.
각 sched 시각 ±30min 안에 cycles.jsonl entry 없으면 누락. PC 꺼져 있었거나
grace 초과 시 즉시 사용자에게 보이게.

누락 없으면 알림 줄 자체가 숨김 — 정상 운영 시엔 깔끔.

### v0.8.8 사용자에게 자동 도달

v0.8.8의 focus event 기반 update check가 GitHub에 v0.8.9 publish 직후
감지 → amber 배너 → [지금 업데이트] 클릭으로 자동 적용 (이번엔 터미널 안 뜨고
재시작 팝업 없이 깔끔).
