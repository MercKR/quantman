"""브로커 추상화.

Trader는 Broker 인터페이스에만 의존한다 — 실거래(KisBroker)와
체험/검증(MockBroker)을 같은 트레이딩 로직으로 구동한다.
"""

from __future__ import annotations

from typing import Callable, Protocol


class Broker(Protocol):
    def account_snapshot(self) -> dict: ...
    def price(self, symbol: str) -> float: ...
    def buy(self, symbol: str, qty: int) -> dict: ...
    def sell(self, symbol: str, qty: int) -> dict: ...
    # Phase 9 추가 — 지정가/취소/조회. 미지원 브로커는 NotImplementedError.
    def buy_limit(self, symbol: str, qty: int, limit_price: int) -> dict: ...
    def sell_limit(self, symbol: str, qty: int, limit_price: int) -> dict: ...
    def cancel(self, order_no: str, symbol: str, qty: int) -> dict: ...
    def order_status(self, order_no: str) -> dict: ...
    def pending_orders(self) -> list[dict]: ...


class MockBroker:
    """메모리 기반 모의 브로커 — 검증 및 'KIS 연결 없이 체험' 모드용.

    지정가도 즉시 현재가에 체결된 것으로 단순화 (체험 모드는 검증용).
    """

    def __init__(self, cash: float, price_fn: Callable[[str], float]):
        self._cash = float(cash)
        self._price_fn = price_fn
        self._positions: dict[str, dict] = {}   # symbol -> {qty, avg_price}
        self._order_seq = 0

    def _next_no(self) -> str:
        self._order_seq += 1
        return f"MOCK{self._order_seq:08d}"

    def price(self, symbol: str) -> float:
        return float(self._price_fn(symbol))

    def _do_buy(self, symbol: str, qty: int, fill_px: float) -> dict:
        cost = fill_px * qty
        if cost > self._cash:
            return {"success": False, "message": "예수금 부족"}
        self._cash -= cost
        pos = self._positions.get(symbol, {"qty": 0, "avg_price": 0.0})
        total = pos["qty"] + qty
        pos["avg_price"] = (pos["avg_price"] * pos["qty"] + cost) / total
        pos["qty"] = total
        self._positions[symbol] = pos
        return {"success": True, "message": "체결", "price": fill_px, "qty": qty,
                "order_no": self._next_no(), "filled_qty": qty}

    def _do_sell(self, symbol: str, qty: int, fill_px: float) -> dict:
        pos = self._positions.get(symbol)
        if not pos or pos["qty"] < qty:
            return {"success": False, "message": "보유 수량 부족"}
        self._cash += fill_px * qty
        pos["qty"] -= qty
        if pos["qty"] == 0:
            del self._positions[symbol]
        return {"success": True, "message": "체결", "price": fill_px, "qty": qty,
                "order_no": self._next_no(), "filled_qty": qty}

    def buy(self, symbol: str, qty: int) -> dict:
        return self._do_buy(symbol, qty, self.price(symbol))

    def sell(self, symbol: str, qty: int) -> dict:
        return self._do_sell(symbol, qty, self.price(symbol))

    def buy_limit(self, symbol: str, qty: int, limit_price: int) -> dict:
        cur = self.price(symbol)
        # 매수 지정가는 한도 이상에서만 미체결. 한도 이하면 한도가 또는 현재가 중 낮은 쪽.
        if cur > limit_price:
            return {"success": False, "message": "한도 초과 미체결",
                    "order_no": self._next_no(), "filled_qty": 0}
        fill = min(cur, float(limit_price))
        return self._do_buy(symbol, qty, fill)

    def sell_limit(self, symbol: str, qty: int, limit_price: int) -> dict:
        cur = self.price(symbol)
        if cur < limit_price:
            return {"success": False, "message": "한도 미달 미체결",
                    "order_no": self._next_no(), "filled_qty": 0}
        fill = max(cur, float(limit_price))
        return self._do_sell(symbol, qty, fill)

    def cancel(self, order_no: str, symbol: str, qty: int) -> dict:
        return {"success": True, "message": "취소", "order_no": order_no}

    def order_status(self, order_no: str) -> dict:
        # Mock에서는 즉시 체결 또는 즉시 미체결이므로 추적 안 함
        return {"order_no": order_no, "status": "filled", "filled_qty": 0,
                "remain_qty": 0}

    def pending_orders(self) -> list[dict]:
        return []

    def account_snapshot(self) -> dict:
        positions = []
        eval_total = self._cash
        for sym, pos in self._positions.items():
            px = self.price(sym)
            eval_total += px * pos["qty"]
            positions.append({
                "symbol": sym, "qty": pos["qty"],
                "avg_price": round(pos["avg_price"], 2),
                "eval_price": round(px, 2),
            })
        return {
            "balance": {"cash": round(self._cash), "total_eval": round(eval_total)},
            "positions": positions,
        }
