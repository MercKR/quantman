"""피드 레지스트리 — 수급/cron 단위 피드의 정책·분류 **단일 출처**.

각 피드는 DataSpec 키(spec.py REGISTRY)에 대응한다. manifest 빌더(server.data_manifest)는
이 레지스트리에서 ① 가격 심볼→피드 분류와 ② 피드별 정책(source·adjustment·calendar)을 읽는다 —
정책이 코드 곳곳이 아닌 여기 한 곳에 산다. 신규 피드는 여기 등록만 하면 manifest가 자동 반영된다.

설계: core/quant_core/data/feeds/ — 모놀리식 data_fetcher.fetch_all에 덧대지 않고 피드별로 조직.
의존: dataclass뿐(pandas/yfinance 비의존).
"""

from __future__ import annotations

from .base import FeedPolicy

# 가격 피드 정책 — (source, 실측 adjustment, calendar). data_fetcher 수급 동작과 일치.
# ohlcv.kr: FDR는 분할조정(split_adjusted) — 삼성 2018 50:1 분할 구간 연속성으로 실측 검증(Stage 4).
#   배당재투자(total_return)는 아님(무료 미제공). DataSpec 요구도 split_adjusted라 D-adj 해소.
PRICE_FEED_POLICY: dict[str, FeedPolicy] = {
    "ohlcv.kr":      FeedPolicy(source="FinanceDataReader(KRX)", adjustment="split_adjusted", calendar="KRX"),
    "ohlcv.us":      FeedPolicy(source="yfinance(auto_adjust)", adjustment="total_return", calendar="US"),
    "ohlcv.crypto":  FeedPolicy(source="Binance", adjustment="raw", calendar="CRYPTO"),
    "ohlcv.futures": FeedPolicy(source="yfinance/FinanceDataReader", adjustment="total_return", calendar="US"),
}


def classify_price_feed(sym: str, *, macro: set, fdr_assets: set, yf_assets: set) -> str | None:
    """가격 심볼 → 피드 키. 매크로 브로드캐스트는 가격 피드가 아니므로 None.

    분류 우선순위(순서 의존): 매크로 제외 → 비트코인 → 선물/지수 ETF → KR 6자리 → 그 외 해외주.
    """
    if sym in macro:
        return None                              # 매크로 브로드캐스트 — 가격 피드 아님
    if sym == "비트코인":
        return "ohlcv.crypto"
    if sym in yf_assets or sym in fdr_assets:
        return "ohlcv.futures"
    if sym.isdigit() and len(sym) == 6:
        return "ohlcv.kr"
    return "ohlcv.us"                            # 그 외 — 개별 해외주


__all__ = ["FeedPolicy", "PRICE_FEED_POLICY", "classify_price_feed"]
