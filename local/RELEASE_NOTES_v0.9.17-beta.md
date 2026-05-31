## 현황 "거래된 금액" 집계 노출 (서버 분석 일반화 동반)

서버·웹에 백테스트 분석 일반화(신호값 분포·횡단 IC·기간분할·전략 조합)와 "내 전략"
현황 보강이 배포됨(quantman `ac13d13`). 로컬앱은 그 현황에 필요한 **거래된 금액(총
체결대금) 집계**만 스냅샷 요약에 추가한다. 원시 체결·주문·계좌번호는 로컬 PC 전용
유지 — 서버엔 전략별 집계 숫자 하나만 push(보안 경계 불변).

### ✨ 거래된 금액(총 체결대금) 집계

- [localapp/analytics.py](localapp/analytics.py) — `strategy_pnl_summary`의 by_strategy
  행에 `traded_amount` 추가. 매수·매도 체결의 `체결가 × 수량` 합(전략별 누적).
- 효과: 웹 **내 전략 → 현황**에 "거래된 금액"이 표시됨
  (서버 `StrategyStatsOut.traded_amount`로 전달).

### 4원칙 자가검토

- **근본 ✓** — "로컬앱에서 확인" 안내 대신 집계를 정식 노출. 서버가 가진 게 요약뿐이라는
  한계를 *raw 체결 전송 없이* 해소(집계만 안전정보로 push).
- **Over-eng 금지 ✓** — 기존 by_strategy 집계 루프에 합산 1줄 + 출력 1키. 새 계층 없음.
- **Overthinking 금지 ✓** — 모든 체결의 notional 단순 합.
- **검증 ✓** — analytics 컴파일·로직 검토. live 스냅샷 표시는 갱신 후 재확인 권장.

### 내부 변경

**[localapp/analytics.py]** by_strategy 행에 `traded_amount` 집계.
**[localapp/\_\_init\_\_.py]** 0.9.16-beta → 0.9.17-beta.

※ 서버측 현황 데이터흐름 버그(by_strategy 키매칭 `strategy_name`↔`strategy`, 승률 ×100
스케일)도 같은 배포(`ac13d13`)에서 수정됨 — 현황 P&L·승률·거래금액이 이번부터 정상
표시될 전망(live 스냅샷으로 최종 재확인 권장).
