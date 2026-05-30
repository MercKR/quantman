"""상태 파일 단일 영속화 경로 (R5 — StateStore).

자금·리스크 상태(ledger·equity·killswitch·pending·intents·orders 등)를 저장하는
모든 경로는 여기를 거친다. 두 직교 관심사를 한 곳에서 항상 함께 보장한다:

  1) 원자성 — full-rewrite는 tmp에 완전히 쓰고 os.replace로 교체. 중간에 종료돼도
     파일은 항상 이전 완전본 또는 새 완전본만 보인다(truncate-then-write의 부분기록
     손상 방지, L-02). append-only는 단일 라인 write로 원자.
  2) owner-only ACL — 같은 PC의 다른 사용자·프로세스 접근 차단. 잔고·손익·리스크
     상태와 원시 주문 흔적은 민감정보이므로 file_security.restrict_to_owner 적용.

이전엔 trader._save_json·killswitch.save·runner·intents·order_log가 각자 저장해
원자성/ACL이 저장지점마다 들쭉날쭉했다(killswitch·ledger·intents·orders ACL 누락).
단일 경로로 통합해 "한 저장지점이 둘 중 하나를 잊는" 결함 class를 제거한다.

비민감·이미 원자적인 캐시(예: calendar_sync 세션 캐시)는 여기를 거치지 않는다 —
ACL이 불필요하고 중복 적용은 과확장.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .file_security import restrict_to_owner


def save_json(path: Path, obj) -> None:
    """민감 상태 JSON의 원자적 저장 + owner-only ACL (모든 full-rewrite의 단일 경로)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    restrict_to_owner(path)


def append_jsonl(rec: dict, path: Path, *, fsync: bool = False) -> None:
    """민감 jsonl 한 줄 append. 파일 최초 생성 시 owner-only ACL 1회 적용.

    fsync=True면 fd 수준 fsync로 디스크 도달 보장(L-01 intent 저널 — 전원 끊김
    후에도 남아야 중복 발주 차단). 로그성 append(orders/cycles)는 fsync 불필요.
    restrict_to_owner는 생성 시 1회만 — 매 append마다 icacls 호출하면 과한 비용.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    newly_created = not path.exists()
    line = json.dumps(rec, ensure_ascii=False) + "\n"
    fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.write(fd, line.encode("utf-8"))
        if fsync:
            os.fsync(fd)
    finally:
        os.close(fd)
    if newly_created:
        restrict_to_owner(path)
