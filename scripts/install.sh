#!/usr/bin/env bash
# Install virattt/ai-hedge-fund (the "aihf" package) for the smoke test.
#
# Upstream is a Poetry project (pyproject.toml + poetry.lock, Python ^3.11).
# Its documented routes are:
#   - end users:   pipx install aihf   (or: pip install aihf)
#   - development: git clone ... && poetry install && poetry run aihf
#
# This runner clones the upstream repo and pip-installs the cloned
# pyproject (built via poetry-core) into the runner's system Python 3.11.
# That is the task-allowed pip equivalent of `poetry install`, and it
# puts `hedge_fund` and the `aihf` entry point on the plain `python`
# that the COMMANDS variable invokes (a Poetry venv would not be
# visible to that step).
set -euo pipefail

if [ ! -d upstream/.git ]; then
  rm -rf upstream
  git clone --depth 1 https://github.com/virattt/ai-hedge-fund.git upstream
fi

python -m pip install --upgrade pip
python -m pip install ./upstream

# Fail the install step loudly if the package did not land.
python -c "import hedge_fund, hedge_fund.run; print('hedge_fund import OK:', hedge_fund.__file__)"
command -v aihf
