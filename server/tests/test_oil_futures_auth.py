"""원유선물 라우터 인증 게이트 회귀 — /oil-futures/*는 로그인(JWT) 전용.

라우터 전역 dependencies=[Depends(get_current_user)]. 토큰 없으면 401.
최소 앱으로 검증 — app.main lifespan/DB 불요(인증이 데이터 접근 전에 차단).
"""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

# server 디렉터리를 path에 추가 — `import app.*`
_SERVER_DIR = Path(__file__).resolve().parent.parent
if str(_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(_SERVER_DIR))

from app.routers import oil_futures


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(oil_futures.router)
    return TestClient(app)


def test_oil_get_endpoints_require_auth():
    client = _client()
    for path in ["/oil-futures/data-info", "/oil-futures/latest-price",
                 "/oil-futures/prices", "/oil-futures/grid", "/oil-futures/signals",
                 "/oil-futures/seasonality", "/oil-futures/macro-context"]:
        assert client.get(path).status_code == 401, f"{path} should require auth"


def test_oil_post_endpoints_require_auth():
    client = _client()
    # 토큰 없으면 본문 검증 전에 401 (빈 본문이라도 인증이 먼저 차단)
    for path in ["/oil-futures/backtest", "/oil-futures/walkforward"]:
        assert client.post(path, json={}).status_code == 401, f"{path} should require auth"
