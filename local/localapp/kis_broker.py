"""KIS(한국투자증권) REST 브로커 — 모의투자(VTS) 연동.

자격증명은 keyring에서만 읽는다. Access Token은 APP_DIR에 캐싱(24h).
실전(virtual=False) TR_ID도 분기하지만 첫 릴리스는 모의투자만 사용한다.

Phase 9 확장:
- 지정가 주문 (ORD_DVSN="00") + 시장가 (ORD_DVSN="01")
- 주문 취소·정정 (order-rvsecncl)
- 일별 주문체결 조회 (inquire-daily-ccld) — 미체결/체결 상태 추적
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

import requests

from .config import APP_DIR
from .secrets_store import load_kis

log = logging.getLogger("localapp.kis_broker")

_VTS = "https://openapivts.koreainvestment.com:29443"
_REAL = "https://openapi.koreainvestment.com:9443"
_TOKEN_CACHE = APP_DIR / ".kis_token.json"


def _kis_check(r: requests.Response) -> dict:
    """KIS 응답 검증 — 오류 시 KIS가 보낸 메시지(msg_cd/msg1)를 그대로 노출."""
    try:
        body = r.json()
    except Exception:
        raise RuntimeError(f"KIS API HTTP {r.status_code}: {r.text[:300]}")
    if r.status_code != 200:
        raise RuntimeError(f"KIS API HTTP {r.status_code} "
                           f"[{body.get('msg_cd', '')}] {body.get('msg1', body)}")
    return body


class KisBroker:
    """KIS 모의투자 브로커. Broker 인터페이스 구현.

    주문·잔고는 모의투자(VTS) 도메인, 시세 조회는 실전 도메인을 사용한다.
    KIS 모의투자 서버는 시세 API를 제대로 지원하지 않기 때문이다.
    """

    def __init__(self):
        creds = load_kis()
        if not creds:
            raise RuntimeError("KIS 자격증명이 없습니다. 먼저 setup으로 등록하세요.")
        self.key = creds["app_key"]
        self.secret = creds["app_secret"]
        self.virtual = creds.get("virtual", True)
        self.base = _VTS if self.virtual else _REAL
        self.quote_base = _REAL          # 시세는 항상 실전 도메인
        no = creds["account_no"].split("-")
        self.cano, self.acnt_cd = no[0], (no[1] if len(no) > 1 else "01")

    # ── 토큰 ──────────────────────────────────────────────────────────────────

    def _token(self) -> str:
        if _TOKEN_CACHE.exists():
            c = json.loads(_TOKEN_CACHE.read_text(encoding="utf-8"))
            if datetime.fromisoformat(c["expires_at"]) > datetime.now() + timedelta(minutes=30):
                return c["access_token"]
        r = requests.post(f"{self.base}/oauth2/tokenP",
                           json={"grant_type": "client_credentials",
                                 "appkey": self.key, "appsecret": self.secret},
                           timeout=10)
        r.raise_for_status()
        d = r.json()
        _TOKEN_CACHE.write_text(json.dumps({
            "access_token": d["access_token"],
            "expires_at": (datetime.now()
                           + timedelta(seconds=int(d.get("expires_in", 86400)))).isoformat(),
        }), encoding="utf-8")
        return d["access_token"]

    def _headers(self, tr_id: str) -> dict:
        return {
            "content-type": "application/json",
            "authorization": f"Bearer {self._token()}",
            "appkey": self.key, "appsecret": self.secret,
            "tr_id": tr_id, "custtype": "P",
        }

    # ── 조회 ──────────────────────────────────────────────────────────────────

    def _balance_raw(self) -> dict:
        tr = "VTTC8434R" if self.virtual else "TTTC8434R"
        r = requests.get(f"{self.base}/uapi/domestic-stock/v1/trading/inquire-balance",
                         headers=self._headers(tr), timeout=10, params={
            "CANO": self.cano, "ACNT_PRDT_CD": self.acnt_cd,
            "AFHR_FLPR_YN": "N", "OFL_YN": "", "INQR_DVSN": "02",
            "UNPR_DVSN": "01", "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N", "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "", "CTX_AREA_NK100": "",
        })
        return _kis_check(r)

    def account_snapshot(self) -> dict:
        body = self._balance_raw()
        out = body.get("output2", [{}])[0]
        positions = [{
            "symbol": it["pdno"], "name": it["prdt_name"],
            "qty": int(it["hldg_qty"]),
            "avg_price": float(it["pchs_avg_pric"]),
            "eval_price": float(it["prpr"]),
        } for it in body.get("output1", []) if int(it.get("hldg_qty", 0)) > 0]
        return {
            "balance": {"cash": int(out.get("dnca_tot_amt", 0)),
                        "total_eval": int(out.get("tot_evlu_amt", 0))},
            "positions": positions,
        }

    def price(self, symbol: str) -> float:
        # 시세 조회는 실전 도메인 사용 (모의투자 도메인은 시세 API 미지원)
        r = requests.get(
            f"{self.quote_base}/uapi/domestic-stock/v1/quotations/inquire-price",
            headers=self._headers("FHKST01010100"), timeout=10,
            params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": symbol})
        body = _kis_check(r)
        return float(body.get("output", {}).get("stck_prpr", 0))

    # ── 주문 ──────────────────────────────────────────────────────────────────

    def _submit(self, symbol: str, qty: int, side: str,
                ord_dvsn: str, unit_price: int) -> dict:
        """ord_dvsn: 00=지정가, 01=시장가. unit_price는 지정가일 때만 의미.

        반환: {success, message, order_no, filled_qty(=0, 미체결 시작), msg_cd}
        """
        if side == "buy":
            tr = "VTTC0802U" if self.virtual else "TTTC0802U"
        else:
            tr = "VTTC0801U" if self.virtual else "TTTC0801U"
        body = {
            "CANO": self.cano, "ACNT_PRDT_CD": self.acnt_cd,
            "PDNO": symbol, "ORD_DVSN": ord_dvsn,
            "ORD_QTY": str(qty),
            "ORD_UNPR": str(unit_price) if ord_dvsn == "00" else "0",
        }
        r = requests.post(f"{self.base}/uapi/domestic-stock/v1/trading/order-cash",
                          headers=self._headers(tr), timeout=10, json=body)
        d = _kis_check(r)
        return {
            "success": d.get("rt_cd") == "0",
            "message": d.get("msg1", ""),
            "msg_cd": d.get("msg_cd", ""),
            "order_no": d.get("output", {}).get("ODNO", ""),
            "ord_branch": d.get("output", {}).get("KRX_FWDG_ORD_ORGNO", ""),
            "filled_qty": 0,
        }

    def buy(self, symbol: str, qty: int) -> dict:
        return self._submit(symbol, qty, "buy", "01", 0)

    def sell(self, symbol: str, qty: int) -> dict:
        return self._submit(symbol, qty, "sell", "01", 0)

    def buy_limit(self, symbol: str, qty: int, limit_price: int) -> dict:
        return self._submit(symbol, qty, "buy", "00", int(limit_price))

    def sell_limit(self, symbol: str, qty: int, limit_price: int) -> dict:
        return self._submit(symbol, qty, "sell", "00", int(limit_price))

    # ── 주문 취소 / 조회 ──────────────────────────────────────────────────────

    def cancel(self, order_no: str, symbol: str, qty: int,
               ord_branch: str = "") -> dict:
        """미체결 주문 전량 취소."""
        tr = "VTTC0803U" if self.virtual else "TTTC0803U"
        r = requests.post(
            f"{self.base}/uapi/domestic-stock/v1/trading/order-rvsecncl",
            headers=self._headers(tr), timeout=10, json={
                "CANO": self.cano, "ACNT_PRDT_CD": self.acnt_cd,
                "KRX_FWDG_ORD_ORGNO": ord_branch or "",
                "ORGN_ODNO": order_no, "ORD_DVSN": "00",
                "RVSE_CNCL_DVSN_CD": "02",       # 02 = 취소
                "ORD_QTY": str(qty), "ORD_UNPR": "0",
                "QTY_ALL_ORD_YN": "Y",
            })
        d = _kis_check(r)
        return {"success": d.get("rt_cd") == "0",
                "message": d.get("msg1", ""),
                "msg_cd": d.get("msg_cd", "")}

    def _daily_ccld(self) -> dict:
        """당일 주문체결 조회 — 미체결·체결·취소 모두 포함."""
        tr = "VTTC8001R" if self.virtual else "TTTC8001R"
        today = datetime.now().strftime("%Y%m%d")
        r = requests.get(
            f"{self.base}/uapi/domestic-stock/v1/trading/inquire-daily-ccld",
            headers=self._headers(tr), timeout=10, params={
                "CANO": self.cano, "ACNT_PRDT_CD": self.acnt_cd,
                "INQR_STRT_DT": today, "INQR_END_DT": today,
                "SLL_BUY_DVSN_CD": "00", "INQR_DVSN": "00",
                "PDNO": "", "CCLD_DVSN": "00",
                "ORD_GNO_BRNO": "", "ODNO": "",
                "INQR_DVSN_3": "00", "INQR_DVSN_1": "",
                "CTX_AREA_FK100": "", "CTX_AREA_NK100": "",
            })
        return _kis_check(r)

    def order_status(self, order_no: str) -> dict:
        """특정 주문번호의 현재 상태."""
        try:
            body = self._daily_ccld()
        except Exception as e:
            log.warning("주문 조회 실패: %s", e)
            return {"order_no": order_no, "status": "unknown",
                    "filled_qty": 0, "remain_qty": 0, "fill_price": 0.0}
        for row in body.get("output1", []) or []:
            if row.get("odno") == order_no:
                ord_qty = int(row.get("ord_qty", 0) or 0)
                ccld_qty = int(row.get("tot_ccld_qty", 0) or 0)
                avg_px = float(row.get("avg_prvs", 0) or 0)
                cncl = row.get("cncl_yn", "") == "Y"
                if cncl:
                    status = "cancelled"
                elif ccld_qty >= ord_qty and ord_qty > 0:
                    status = "filled"
                elif ccld_qty > 0:
                    status = "partial"
                else:
                    status = "submitted"
                return {"order_no": order_no, "status": status,
                        "filled_qty": ccld_qty,
                        "remain_qty": max(0, ord_qty - ccld_qty),
                        "fill_price": avg_px,
                        "ord_branch": row.get("ord_gno_brno", "")}
        return {"order_no": order_no, "status": "unknown",
                "filled_qty": 0, "remain_qty": 0, "fill_price": 0.0}

    def pending_orders(self) -> list[dict]:
        """현재 미체결 잔량이 있는 주문 목록."""
        try:
            body = self._daily_ccld()
        except Exception as e:
            log.warning("미체결 조회 실패: %s", e)
            return []
        out = []
        for row in body.get("output1", []) or []:
            ord_qty = int(row.get("ord_qty", 0) or 0)
            ccld_qty = int(row.get("tot_ccld_qty", 0) or 0)
            if row.get("cncl_yn", "") == "Y":
                continue
            remain = ord_qty - ccld_qty
            if remain <= 0:
                continue
            out.append({
                "order_no": row.get("odno", ""),
                "symbol": row.get("pdno", ""),
                "name": row.get("prdt_name", ""),
                "side": "buy" if row.get("sll_buy_dvsn_cd") == "02" else "sell",
                "qty": ord_qty, "filled_qty": ccld_qty, "remain_qty": remain,
                "limit_price": float(row.get("ord_unpr", 0) or 0),
                "ord_branch": row.get("ord_gno_brno", ""),
                "submitted_at": row.get("ord_tmd", ""),
            })
        return out
