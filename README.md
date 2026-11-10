# ai-hedge-fund-runner

Runs [virattt/ai-hedge-fund](https://github.com/virattt/ai-hedge-fund)
(the `aihf` package — an AI-powered hedge fund proof of concept, for
educational purposes only; it does not place real trades) on GitHub
Actions, where the commands to execute live in a repository **Actions
variable** — not in code.

**This repo is SMOKE-ONLY as provisioned.** The default `COMMANDS`
only verifies that the upstream package installs, its main module
imports, and its CLI help runs. It does **not** attempt a real
analysis run — the API keys for that are provisioned separately.

## The pattern (one repo per tool)

1. **Edit the commands**: repo *Settings → Secrets and variables →
   Actions → Variables* → set the `COMMANDS` variable to whatever
   shell commands this run should execute (multi-line works). The
   same can be done through the GitHub API
   (`PUT /repos/{owner}/{repo}/actions/variables/COMMANDS`).
2. **Trigger manually**: *Actions* tab → “Run analysis” → *Run
   workflow* (or `POST /repos/{owner}/{repo}/actions/workflows/run.yml/dispatches`).
   The workflow has **no other triggers** — it runs only when
   dispatched (`workflow_dispatch` only).
3. **Collect results**: the workflow uploads everything under
   `results/` as the `results` build artifact (`if: always()`, so
   partial results survive a failing step). Download it from the run
   page or via the API.

The workflow itself is generic: checkout → Python 3.11 →
`bash scripts/install.sh` → run `${{ vars.COMMANDS }}` → upload
`results/`. To run a different analysis, change the variable — not
the workflow.

## Install

`scripts/install.sh` clones the upstream repo and installs it per
its README. Upstream is a **Poetry** project (Python ^3.11;
documented dev route: `poetry install`, then `poetry run aihf`;
documented user route: `pipx install aihf` / `pip install aihf`).
The runner pip-installs the cloned `pyproject.toml` (built via
poetry-core) into the runner's system Python 3.11, so the plain
`python` invoked by `COMMANDS` can import `hedge_fund` and the
`aihf` entry point is on PATH.

## Smoke test

`scripts/smoke.py`:

- verifies the main module imports (`hedge_fund`, `hedge_fund.run`;
  legacy `src.main` tried as a fallback if present), and
- runs the CLI help via subprocess using the project's documented
  entry point (`python -m hedge_fund.run --help`, equivalently the
  `aihf` console script), saving the first ~50 lines.

It writes `results/smoke.json` (`{"ok": ..., "cli_help_ok": ...}`)
and `results/smoke.md` quoting the help output.

Current `COMMANDS` value:

```sh
mkdir -p results
set -o pipefail; python scripts/smoke.py 2>&1 | tee results/run.log
```

(The `set -o pipefail;` prefix matters: without it, piping through
`tee` would mask a failing smoke script as a successful run.)

## ⚠️ KEY REQUIREMENTS for real runs

A real analysis run needs **both** of the following — neither is
provisioned in this smoke-only setup, and no real run should be
attempted until they are:

1. **An LLM API key** — one model provider is enough. Per the
   project's `.env.example`, supported providers include OpenAI,
   Anthropic, Groq, DeepSeek, Google, xAI, Kimi/Moonshot and
   TypeSafe (Jev) — e.g. `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`.
2. **A Financial Datasets API key** — from
   [financialdatasets.ai](https://financialdatasets.ai)
   (`FINANCIAL_DATASETS_API_KEY`), which supplies the market data
   (prices, fundamentals, earnings) the agents analyse. (Upstream
   also documents an x402 / Base-wallet pay-per-call alternative
   instead of a key.)

Set them as repository **Secrets** (never in `COMMANDS` or in code)
before changing `COMMANDS` to a real run, e.g. upstream's documented
`aihf backtest <mandate> --universe AAPL,MSFT,NVDA ...` form.

## Multi-market by design

Nothing in the workflow or the runner pattern is tied to one
exchange. Scripts take the ticker symbol and analysis parameters as
inputs (CLI args and/or the `COMMANDS` variable), so the same repo
can analyse a US stock today and another market tomorrow — only the
inputs change.
