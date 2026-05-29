"""sim/prod 경계 — localapp(프로덕션)은 sim/tests를 절대 import하지 않는다.
배포 번들(localapp)에 테스트/시뮬 코드가 새어들면 안 된다(spec §5)."""
import ast
from pathlib import Path

_LOCALAPP = Path(__file__).resolve().parent.parent / "localapp"


def test_localapp_never_imports_sim_or_tests():
    offenders = []
    for py in _LOCALAPP.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                mods = [node.module or ""]
            for m in mods:
                if m.split(".")[0] in ("sim", "tests"):
                    offenders.append(f"{py.name}: import {m}")
    assert not offenders, f"프로덕션이 sim/tests import: {offenders}"
