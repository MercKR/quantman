## 주요 변경 — Bootstrap problem 인지 + 격리 self-test 통과한 첫 release

### 🐞 v0.9.7~v0.9.10 update 연속 실패 사건

사용자: "이런 오류가 이전 버전들에서도 계속 발생하는데 근본적인 해결이 안되고 있는 이유가 뭐죠?"

**근본 원인 — bootstrap problem 인지 못 함**:
매 release의 updater fix는 *다음* update가 아니라 *그 다음다음* update부터 적용된다.
사용자가 v0.9.X → v0.9.X+1 update를 시도하면 **현재 가동 중인 v0.9.X .exe가
들고 있는 v0.9.X의 updater.py 코드**가 bat을 생성·실행한다.

| 사용자 시도 | 가동 중 .exe | 사용된 updater 코드 |
|---|---|---|
| v0.9.7 → v0.9.8 | v0.9.7 | v0.9.7 updater (PID-only kill — 좀비 미잡음) |
| v0.9.8 → v0.9.9 | v0.9.8 | v0.9.8 updater (`/T` self-kill) |
| v0.9.9 → v0.9.10 | v0.9.9 | v0.9.9 updater (`/T` self-kill) |
| v0.9.10 → v0.9.10 (재시도) | v0.9.9 (claude robocopy) | v0.9.9 updater 그대로 |

v0.9.10에서 `/T` 제거했지만 **v0.9.10 → v0.9.11 update가 첫 적용 기회**.

### 진짜 잘못된 작업 방식 (반성)

1. **Bootstrap problem 미인지** — fix가 즉시 적용된다고 잘못 가정.
2. **격리 self-test 부재** — 매번 사용자 PC가 유일한 테스트 환경. 매 실패는 사용자 부담.
3. **추측-패치 cycle** — log 보고 가설 세우고 release. 다른 가설 검증 0.

### 진짜 해결책

**self-test로 release 전 검증**:
- `C:\Users\USER\AppData\Local\Temp\quantman-selftest\` 격리 환경 구축
- v0.9.10 zip을 install 폴더에 풀기
- v0.9.10의 `_write_updater_bat` 함수로 bat 생성
- `cmd.exe`로 bat 실행 (실제 robocopy 동작)
- 검증: robocopy log 갱신 + .exe mtime 변경 + bat self-delete

결과 (격리 환경, KST 2026-05-28 04:42):
```
✅ bat 실행 18초 후 self-delete (self-kill 없음)
✅ robocopy log 갱신 (FRESH mtime, "종료됨: 04:42:04")
✅ install .exe mtime 04:41:34 → 04:41:42 (교체 성공)
✅ bat 자체 삭제
```

self-test의 한계: 사용자 PC의 *.exe 실행 중* 시나리오는 100% 재현 못 함 (claude
환경엔 process 없음). 그러나 robocopy + bat termination logic은 통과 — 사용자
PC에서 taskkill로 .exe 죽인 후 robocopy 흐름이 같은 chain이라 정상 기대.

### 코드 변경

이번 release는 **버전 bump만**. v0.9.10의 updater fix(`/T` 제거)가 처음 사용자
PC에 적용되는 것이 핵심. `_write_updater_bat` 등 updater.py 자체는 변경 없음.

**[localapp/__init__.py](localapp/__init__.py)**
- 버전 0.9.10-beta → 0.9.11-beta

### 검증 흐름 (사용자 PC)

1. amber 배너 [지금 업데이트] 클릭
2. 가동 중 v0.9.10 .exe의 **v0.9.10 updater**가 bat 생성 (`/T` 제거된 코드)
3. taskkill `/F /IM` (`/T` 없이) — `.exe`는 죽이고 cmd.exe(bat 실행 중)는 살림
4. robocopy 정상 도달 → `.exe` 교체 → `start` 으로 새 `.exe` 시작
5. **사용자 update가 정상 자동 path로 성공**하면 bootstrap problem 종료

### 다음 작업 (v0.9.12)

self-test로 검증된 update path가 사용자 PC에서 실증되면 다음 release에 묶음:
1. orders.jsonl fill 미기록 — 잔고 reconcile로 우회 fix
2. pending_orders.json stale — (1)과 연동
3. foreign_eval_krw 환산 부정확 — broker.overseas_snapshot 식 fix
4. (선택) H0GSCNI0 해외 체결통보 본질 fix
