"""로컬앱 설정."""

import os
from pathlib import Path

# 사용자 PC의 로컬앱 데이터 디렉터리 (원장·로그)
APP_DIR = Path(os.getenv("QP_LOCAL_DIR", Path.home() / ".quant-platform"))
APP_DIR.mkdir(parents=True, exist_ok=True)

# 연동할 플랫폼 서버 (배포 기본값 — 개발 시 QP_PLATFORM_URL 환경변수로 덮어쓰기)
PLATFORM_URL = os.getenv("QP_PLATFORM_URL",
                         "https://quantman-production.up.railway.app")

# keyring 서비스명 (OS 자격증명 저장소 키)
KEYRING_SERVICE = "quant-platform-local"

LEDGER_PATH = APP_DIR / "ledger.json"
EQUITY_PATH = APP_DIR / "equity.json"
TRADES_PATH = APP_DIR / "trades.jsonl"
PENDING_PATH = APP_DIR / "pending_snapshot.json"

# Phase 9 추가
ORDERS_PATH = APP_DIR / "orders.jsonl"           # 주문 이벤트 로그 (제출/체결/취소/거부)
CYCLES_PATH = APP_DIR / "cycles.jsonl"           # 사이클별 의사결정 로그
KILLSWITCH_PATH = APP_DIR / "killswitch.json"    # kill switch 상태
PENDING_ORDERS_PATH = APP_DIR / "pending_orders.json"  # 미체결 추적
SLIPPAGE_PATH = APP_DIR / "slippage.json"        # 누적 슬리피지 통계
