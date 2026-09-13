#!/usr/bin/env python3
"""Read-only local-import scanner for the TESTR ERD Studio Pro restructure.

Prints, for every .py at the repository root (excluding server.py itself), the
exact lines that import another LOCAL module — so the migration script and the
human both act from the same verified ground truth. It never writes anything.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LOCAL_MODULE_NAMES = {
    "database", "oracle_sync", "subsystems",
    "ai_assistant", "ai_classify",
    "db_connectors",
    "sql_import", "sql_export",
    "datadict_import", "datadict_export",
}

IMPORT_RE = re.compile(r"^\s*(?:import\s+([A-Za-z_][A-Za-z0-9_.]*)|from\s+([A-Za-z_][A-Za-z0-9_.]*)\s+import\b)(.*)$")


def scan() -> None:
    self_name = Path(__file__).name
    for py in sorted(ROOT.glob("*.py")):
        if py.name == self_name:
            continue
        hits: list[str] = []
        for lineno, raw in enumerate(py.read_text(encoding="utf-8").splitlines(), start=1):
            m = IMPORT_RE.match(raw)
            if not m:
                continue
            mod = m.group(1) or m.group(2) or ""
            root_mod = mod.split(".")[0]
            if root_mod in LOCAL_MODULE_NAMES:
                hits.append(f"    L{lineno:<5} {raw.strip()}")
        if hits:
            print(f"=== {py.name} ===")
            print("\n".join(hits))


if __name__ == "__main__":
    scan()
