"""Trading Workbench 시뮬레이터 — 오프라인 결정론적 자동매매 검증 환경.

이 패키지는 **배포 번들(localapp)에 포함되지 않는다**. production 코드(localapp)는
sim을 import하지 않는다(tests/test_sim_prod_boundary.py가 강제). sim은 주입 seam
(Trader(broker) + intraday_loop._on_exec_event)에만 끼며 production 로직을
재구현하지 않는다.
"""
