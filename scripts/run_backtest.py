#!/usr/bin/env python3
"""AI Hedge Fund real run for the Borsagator fleet.

Route (verified from upstream source, hedge_fund/llm/client.py):
the "OpenAI" provider builds ChatOpenAI with base_url=os.getenv(
"OPENAI_API_BASE"), so Cohere's OpenAI-compatible endpoint can serve it.
The only catch: the model id must resolve to provider "OpenAI" in the
package's llm/api_models.json registry, so this script appends a
command-r-08-2024 -> OpenAI entry to the INSTALLED copy before running
(the same spirit as the TradingAgents schema patch).

Data comes from Financial Datasets (FINANCIAL_DATASETS_API_KEY org
secret). Runs `aihf backtest` headlessly over a recent ~100-day window
and writes results/backtest_stdout.json + results/aihf_result.json.
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

MANDATE = """schema_version: 2
name: borsagator-fund
strategies:
  - name: value-pod
    blend: {mode: long_only}
    weight: 1.0
    models:
      - name: graham
        weight: 2.0
      - name: buffett
      - name: munger
risk:
  max_position_pct: 0.25
  max_gross_exposure: 1.0
  halve_drawdown_pct: 0.10
  max_drawdown_pct: 0.20
costs:
  spread_bps: 5
  commission_per_share: 0.005
  impact_coefficient: 1.0
  min_trade_pct: 0.005
capital: 100000
rebalance: weekly
benchmark: SPY
"""

MODEL = "command-r-08-2024"
COHERE_BASE = "https://api.cohere.ai/compatibility/v1"


def patch_registry() -> str:
    import hedge_fund
    path = Path(hedge_fund.__file__).parent / "llm" / "api_models.json"
    entries = json.loads(path.read_text())
    if not any(e.get("model_name") == MODEL for e in entries):
        entries.append({"display_name": "Cohere Command R (OpenAI wire)",
                        "model_name": MODEL, "provider": "OpenAI"})
        path.write_text(json.dumps(entries, indent=2))
    return str(path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", default="AAPL")
    ap.add_argument("--days", type=int, default=100)
    args = ap.parse_args()
    ticker = args.ticker.upper()
    results = Path("results")
    results.mkdir(exist_ok=True)

    cohere = os.environ.get("COHERE_API_KEY")
    fd_key = os.environ.get("FINANCIAL_DATASETS_API_KEY")
    missing = [n for n, v in (("COHERE_API_KEY", cohere),
                              ("FINANCIAL_DATASETS_API_KEY", fd_key)) if not v]
    if missing:
        out = {"tool": "ai-hedge-fund", "ticker": ticker, "status": "error",
               "error": "missing env: " + ", ".join(missing)}
        (results / "aihf_result.json").write_text(json.dumps(out, indent=2))
        print(json.dumps(out))
        return 1

    patched = patch_registry()
    print(f"registry patched: {patched}")

    mandate_path = results / "mandate.yaml"
    mandate_path.write_text(MANDATE)
    end = date.today()
    start = end - timedelta(days=args.days)
    out_path = results / "backtest.json"

    env = dict(os.environ)
    env["OPENAI_API_KEY"] = cohere
    env["OPENAI_API_BASE"] = COHERE_BASE
    env["HEDGE_FUND_LLM_MODEL"] = MODEL

    import shutil
    exe = shutil.which("aihf")
    if not exe:
        print("aihf console script not found on PATH", file=sys.stderr)
        return 1
    cmd = [exe, "backtest", str(mandate_path), "--universe", ticker,
           "--start", start.isoformat(), "--end", end.isoformat(),
           "--model", MODEL, "--out", str(out_path)]
    print("running:", " ".join(cmd))
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True,
                          timeout=3300)
    (results / "run.log").write_text(
        (proc.stdout or "")[-20000:] + "\n--- STDERR ---\n"
        + (proc.stderr or "")[-8000:])
    out = {"tool": "ai-hedge-fund", "ticker": ticker, "model": MODEL,
           "window": f"{start}..{end}", "exit_code": proc.returncode,
           "backtest_file": out_path.exists()}
    # The CLI also prints the full result JSON on stdout; keep a copy.
    if proc.stdout and proc.stdout.strip().startswith("{"):
        (results / "backtest_stdout.json").write_text(proc.stdout)
    (results / "aihf_result.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out))
    return 0 if proc.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
