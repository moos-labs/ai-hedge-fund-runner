#!/usr/bin/env python3
"""Smoke test for virattt/ai-hedge-fund (package ``aihf``).

SMOKE ONLY — no real analysis run, no API keys are used or needed.

Verifies:
  1. The main module imports (``hedge_fund`` and ``hedge_fund.run``;
     the legacy ``src.main`` layout is also tried if present).
  2. The CLI help runs via the project's documented entry point
     (``aihf``, i.e. ``hedge_fund.run:main`` — equivalently
     ``python -m hedge_fund.run --help``), invoked via subprocess.
     The legacy ``python -m src.main --help`` is tried as a fallback
     when an upstream checkout still carries that layout.

Writes:
  - ``results/smoke.json`` with ``{"ok": ..., "cli_help_ok": ...}``
    (plus diagnostic extras)
  - ``results/smoke.md`` quoting the first ~50 lines of the CLI help

Exit code is 0 only when both checks pass.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
UPSTREAM = ROOT / "upstream"


def _candidate_env() -> dict:
    env = dict(os.environ)
    # If the upstream checkout exists, make its package importable even
    # if the pip install step only partially landed — the import check
    # should test the code, and the recorded error says which path failed.
    if UPSTREAM.is_dir():
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(UPSTREAM) + (os.pathsep + existing if existing else "")
    return env


def check_import() -> tuple[bool, str]:
    """Try to import the main module(s). Returns (ok, detail)."""
    if UPSTREAM.is_dir():
        sys.path.insert(0, str(UPSTREAM))
    errors = []
    for mod in ("hedge_fund", "hedge_fund.run"):
        try:
            __import__(mod)
            return True, f"imported {mod} OK"
        except Exception as exc:  # noqa: BLE001 - smoke test records any failure
            errors.append(f"{mod}: {type(exc).__name__}: {exc}")
    # Legacy layout (pre-v2 upstream had src/main.py)
    if (UPSTREAM / "src" / "main.py").exists() or (ROOT / "src" / "main.py").exists():
        try:
            __import__("src.main")
            return True, "imported src.main OK (legacy layout)"
        except Exception as exc:  # noqa: BLE001
            errors.append(f"src.main: {type(exc).__name__}: {exc}")
    return False, "; ".join(errors)


def check_cli_help(env: dict) -> tuple[bool, str, list[str], int | None]:
    """Run the CLI --help via subprocess. Returns (ok, command, lines, rc)."""
    cwd = str(UPSTREAM) if UPSTREAM.is_dir() else str(ROOT)
    candidates: list[list[str]] = [
        [sys.executable, "-m", "hedge_fund.run", "--help"],
        ["aihf", "--help"],
    ]
    if (UPSTREAM / "src" / "main.py").exists():
        candidates.append([sys.executable, "-m", "src.main", "--help"])

    last_cmd, last_lines, last_rc = "", [], None
    for cmd in candidates:
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120, cwd=cwd, env=env
            )
        except Exception as exc:  # noqa: BLE001 - e.g. aihf not on PATH
            last_cmd, last_lines, last_rc = " ".join(cmd), [f"{type(exc).__name__}: {exc}"], None
            continue
        out = (proc.stdout or "") + (proc.stderr or "")
        lines = out.splitlines()
        last_cmd, last_lines, last_rc = " ".join(cmd), lines, proc.returncode
        if proc.returncode == 0 and "usage" in out.lower():
            return True, last_cmd, lines, proc.returncode
    return False, last_cmd, last_lines, last_rc


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    env = _candidate_env()

    import_ok, import_detail = check_import()
    print(f"import_ok={import_ok} ({import_detail})")

    cli_help_ok, cli_cmd, help_lines, cli_rc = check_cli_help(env)
    print(f"cli_help_ok={cli_help_ok} (cmd={cli_cmd!r}, rc={cli_rc})")
    for line in help_lines[:50]:
        print(line)

    ok = bool(import_ok and cli_help_ok)

    payload = {
        "ok": ok,
        "cli_help_ok": bool(cli_help_ok),
        "import_ok": bool(import_ok),
        "import_detail": import_detail,
        "cli_command": cli_cmd,
        "cli_returncode": cli_rc,
        "tool": "virattt/ai-hedge-fund",
        "note": "Smoke only: import + CLI --help. No analysis run, no API keys used.",
    }
    (RESULTS / "smoke.json").write_text(json.dumps(payload, indent=2) + "\n")

    md_lines = [
        "# ai-hedge-fund — smoke test",
        "",
        f"- ok: `{ok}`",
        f"- import_ok: `{import_ok}` — {import_detail}",
        f"- cli_help_ok: `{cli_help_ok}`",
        f"- cli_command: `{cli_cmd}` (return code: {cli_rc})",
        "",
        "## CLI help (first ~50 lines)",
        "",
        "```text",
        *help_lines[:50],
        "```",
        "",
    ]
    (RESULTS / "smoke.md").write_text("\n".join(md_lines))

    print(f"SMOKE RESULT: ok={ok} cli_help_ok={cli_help_ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
