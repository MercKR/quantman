## 주요 변경 — KIS 시간 기반 점검 가드 제거 (실측 fallback에 위임)

### 🐞 사용자 발견 사건 (2026-05-28 KST 03:03)

v0.9.7 → v0.9.8 update 후 catch-up cycle이 trigger됐으나 매수 0건. 로그:
```
03:03:03 [P1-B] KIS 점검 시간대 — cycle skip (Thu 03:03)
```

원인 — `trader._in_kis_maintenance_window`가 평일 03:00~06:00을 KIS 점검 시간대로
*추정*해 차단. KIS 호출 시도 자체 없음.

### 실측 결과 — 가드가 over-conservative

[probe_kis_maintenance.py](tools/probe_kis_maintenance.py)로 03:28부터 5분 간격
3 endpoint (HHDFS76200200·FHKST01010100·VTTC8434R) 호출:

| 시각 | 해외 시세 | 국내 시세 | 잔고 | latency |
|---|---|---|---|---|
| 03:28:42 | OK | OK | OK | 47~125ms |
| 03:29:21 | OK | OK | OK | 83~110ms |
| 03:34:21 | OK | OK | OK | 47~125ms |

가드 윈도우(03:00~06:00) 안인데 모두 정상 응답. **가드 = "시간 기반 추정"이지
"KIS 실측 차단" 아님** — KIS가 진짜 점검 중이었다는 증거 0.

### Fix — 시간 가드 완전 제거, KIS health check fallback에 위임

[localapp/trader.py](localapp/trader.py)
- `_in_kis_maintenance_window` 함수 제거.
- `_cycle_body`에서 가드 호출·`skip_maintenance` decision 분기 제거.

KIS 진짜 점검 중이면 line 1083~의 잔고 health check가 자동 차단:
```python
try:
    snap_pre = self.broker.account_snapshot()
except Exception as e:
    log.error("[P1-B] KIS 잔고 조회 실패 — cycle 중단: %s", e)
    decisions.append(order_log.decision("skip_kis_health", ...))
    return {...}
```

### 4원칙 자가검토

- **근본 원인**: ✓ 추정(시간) → 실측(KIS 응답) fallback. PR-1 (보수적 가드는
  근본 회피)을 본질로 해소.
- **Over-eng 금지**: ✓ 함수 정의·호출·분기·decision 모두 dead code로 제거.
  `_in_kis_maintenance_window` 호출처 0이므로 함수도 제거.
- **Overthinking 금지**: ✓ "가드 풀어도 KIS 응답 실패 시 자동 보호"라는 단순한
  결론. 복잡한 시간 분기 로직 (wd 5/6/0/1~4 × hour 비교) 5줄 모두 삭제.
- **검증**: 실측 가능 — 평일 03:00~06:00 cycle 시도 시
  (a) KIS 정상 → 매수 진행 / (b) KIS 진짜 점검 → skip_kis_health decision.

### 영향 (catch-up 사건)

- 다음 미장(5/29 22:30) catch-up: 가드 차단 없어 시가 fix(v0.9.7 HHDFS76200200)도
  통합 검증 가능.
- 미장 마감(KST 05:00) 직전 catch-up 매수 기회 회복.
- `tools/probe_kis_maintenance.py`로 실측 데이터 계속 누적 — 향후 진짜 점검
  시간대 발견 시 GOTCHAS.md 기록.

### 내부 변경

**[localapp/trader.py](localapp/trader.py)**
- `_in_kis_maintenance_window` 함수 제거 (line 990-1009).
- `_cycle_body`의 가드 분기 제거 (line 1064-1076) — 주석으로 "왜 제거했는지" 명시.

**[localapp/__init__.py](localapp/__init__.py)**
- 버전 0.9.8-beta → 0.9.9-beta
