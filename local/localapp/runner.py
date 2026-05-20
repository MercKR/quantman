"""모의투자 사이클 오케스트레이션 — 전략 풀 → 평가·매매 → 스냅샷 푸시.

견고성: 플랫폼 연결이 끊겨도 매매는 로컬에서 완료한다.
  - 전략 풀 실패 → 신규 진입 없이 기존 보유분 청산만 평가
  - 스냅샷 푸시 실패 → 보류 큐에 저장, 다음 사이클에 재전송
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path

import quant_core as qc

from .broker import Broker, MockBroker
from .config import APP_DIR, PENDING_PATH
from .logging_setup import setup_logging
from .sync_client import pull_strategies, push_snapshot, push_tradable_symbols
from .trader import Trader

log = logging.getLogger("localapp.runner")

# KIS 종목마스터를 마지막으로 push한 날짜를 기록. 같은 날 중복 push 방지.
_MASTER_STAMP = APP_DIR / ".kis_master_pushed.txt"


def _price_fn(dataset: dict):
    def fn(symbol: str) -> float:
        df = dataset.get(symbol)
        if df is None or df.empty or "Close" not in df.columns:
            return 0.0
        return float(df["Close"].iloc[-1])
    return fn


def make_broker(use_mock: bool, mock_cash: float = 10_000_000.0,
                dataset: dict | None = None) -> Broker:
    if use_mock:
        return MockBroker(mock_cash, _price_fn(dataset or {}))
    from .kis_broker import KisBroker          # KIS 자격증명 필요 시에만 import
    return KisBroker()


def _flush_pending() -> None:
    """이전 사이클에서 전송 실패한 스냅샷이 있으면 재전송한다."""
    if not PENDING_PATH.exists():
        return
    try:
        payload = json.loads(PENDING_PATH.read_text(encoding="utf-8"))
        push_snapshot(payload)
        PENDING_PATH.unlink()
        log.info("보류된 스냅샷 재전송 완료")
    except Exception as e:
        log.warning("보류 스냅샷 재전송 실패 (다음 사이클 재시도): %s", e)


def _sync_kis_master_if_due() -> None:
    """KIS 종목마스터를 받아 플랫폼에 push. 같은 날 두 번 이상은 스킵."""
    today = date.today().isoformat()
    if _MASTER_STAMP.exists():
        try:
            if _MASTER_STAMP.read_text(encoding="utf-8").strip() == today:
                return
        except Exception:
            pass
    try:
        from .kis_master import fetch_all_tradable
        rows = fetch_all_tradable()
        if not rows:
            log.warning("KIS 종목마스터: 받은 행이 없어 push 스킵")
            return
        res = push_tradable_symbols(rows)
        _MASTER_STAMP.write_text(today, encoding="utf-8")
        log.info("KIS 종목마스터 push 완료 — %s개 (서버 ok=%s)",
                 res.get("n", len(rows)), res.get("ok"))
    except Exception as e:
        log.warning("KIS 종목마스터 sync 실패 (오늘 안에 재시도 가능): %s", e)


def run_cycle(use_mock: bool = False) -> dict:
    """1회 모의투자 사이클을 실행하고 동기화 스냅샷을 반환한다."""
    setup_logging()
    _flush_pending()
    _sync_kis_master_if_due()

    try:
        strategies = pull_strategies()
        log.info("배정된 전략 %d개", len(strategies))
    except Exception as e:
        log.warning("전략 풀 실패 — 신규 진입 없이 보유분 청산만 평가: %s", e)
        strategies = []

    from .datafetch import refresh_market_data
    refresh_market_data()
    dataset = qc.load_dataset(with_indicators=True)
    broker = make_broker(use_mock, dataset=dataset)
    trader = Trader(broker)
    payload = trader.cycle(strategies, dataset)

    try:
        push_snapshot(payload)
        log.info("동기화 완료 — 평가금액 %s원", f"{payload['balance']['total_eval']:,}")
    except Exception as e:
        PENDING_PATH.write_text(json.dumps(payload, ensure_ascii=False),
                                encoding="utf-8")
        log.warning("동기화 실패 — 보류 큐 저장 (다음 사이클 재전송): %s", e)

    return payload
