"""웹에서 발행한 명령을 SSE로 수신해 실행한다.

연결이 끊기면 지수 백오프로 재연결. SSE가 안 되면 폴링 fallback.
스레드로 백그라운드 동작 — SettingsApp이 페어링된 상태에서 시작.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Callable, Optional

import requests

from .config import PLATFORM_URL
from .secrets_store import load_device_token

log = logging.getLogger("localapp.commands")

_STREAM_URL = f"{PLATFORM_URL}/sync/commands/stream"
_POLL_URL = f"{PLATFORM_URL}/sync/commands/poll"
_ACK_URL_FMT = f"{PLATFORM_URL}/sync/commands/{{id}}/ack"


class CommandClient:
    """SSE 우선, 실패 시 폴링으로 fallback. on_command(cmd)로 핸들러 호출."""

    def __init__(self, on_command: Callable[[dict], dict]):
        self.on_command = on_command
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True,
                                         name="cmd-client")
        self._thread.start()
        log.info("명령 수신 클라이언트 시작")

    def stop(self) -> None:
        self._stop.set()

    # ── 내부 ──────────────────────────────────────────────────────────────────

    def _headers(self) -> dict | None:
        tok = load_device_token()
        if not tok:
            return None
        return {"Authorization": f"Bearer {tok}"}

    def _ack(self, cmd_id: int, status: str, result: dict | None = None) -> None:
        try:
            r = requests.post(
                _ACK_URL_FMT.format(id=cmd_id),
                headers=self._headers(),
                json={"status": status, "result": result or {}},
                timeout=10)
            r.raise_for_status()
        except Exception as e:
            log.warning("명령 ack 실패 [%d]: %s", cmd_id, e)

    def _dispatch(self, cmd: dict) -> None:
        cid = int(cmd.get("id"))
        try:
            result = self.on_command(cmd) or {}
            self._ack(cid, "done", result)
        except Exception as e:  # noqa: BLE001
            log.exception("명령 실행 실패")
            self._ack(cid, "failed", {"error": str(e)})

    def _run(self) -> None:
        backoff = 2
        while not self._stop.is_set():
            headers = self._headers()
            if not headers:
                # 페어링 전 — 5초 후 재시도
                time.sleep(5)
                continue
            try:
                with requests.get(_STREAM_URL, headers=headers, stream=True,
                                  timeout=(10, None)) as r:
                    if r.status_code != 200:
                        log.warning("SSE 연결 거부 HTTP %d — 폴링 fallback",
                                     r.status_code)
                        self._poll_once(headers)
                        time.sleep(backoff)
                        backoff = min(backoff * 2, 60)
                        continue
                    backoff = 2     # 성공 시 리셋
                    log.info("SSE 연결 수립")
                    self._read_stream(r)
            except requests.exceptions.RequestException as e:
                log.info("SSE 연결 끊김 (%s) — %d초 후 재시도", e, backoff)
                # 끊김 동안 누락된 명령은 폴링으로 회수
                try:
                    self._poll_once(self._headers() or {})
                except Exception:
                    pass
                self._stop.wait(backoff)
                backoff = min(backoff * 2, 60)

    def _read_stream(self, r: requests.Response) -> None:
        """SSE 라인 파서. 명령 1건마다 dispatch."""
        buf: list[str] = []
        for line_raw in r.iter_lines(decode_unicode=True):
            if self._stop.is_set():
                return
            if line_raw is None:
                continue
            line = line_raw.strip()
            if line == "":
                # 이벤트 경계
                self._flush_event(buf)
                buf = []
            elif line.startswith(":"):
                continue  # comment / heartbeat
            else:
                buf.append(line)

    def _flush_event(self, lines: list[str]) -> None:
        data_lines = [l[5:].lstrip() for l in lines if l.startswith("data:")]
        if not data_lines:
            return
        try:
            cmd = json.loads("\n".join(data_lines))
        except json.JSONDecodeError:
            log.warning("SSE payload 파싱 실패")
            return
        self._dispatch(cmd)

    def _poll_once(self, headers: dict) -> None:
        try:
            r = requests.get(_POLL_URL, headers=headers, timeout=10)
            if r.status_code == 200:
                for cmd in r.json():
                    self._dispatch(cmd)
        except Exception as e:
            log.debug("폴링 fallback 실패: %s", e)
