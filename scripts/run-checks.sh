#!/usr/bin/env bash
# Run the package-local gate for inter-agent-claude-code from the child root.
# Fail-fast. Assumes dependencies are already synchronized. No publish, no
# global install, no registry contact, no state deletion, no mutation of other
# checkouts.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== python pytest =="
uv run pytest -q

echo "== ruff =="
# --no-respect-gitignore: a parent Git tree can exclude a not-yet-initialized
# child and produce a false pass; ruff's built-in excludes still skip generated
# trees.
uv run ruff check --no-respect-gitignore src tests scripts

echo "== black --check =="
uv run black --check src tests scripts

echo "== mypy =="
uv run mypy src tests

echo "== strict claude plugin validation =="
claude plugin validate --strict .
claude plugin validate --strict .claude-plugin/plugin.json
claude plugin validate --strict .claude-plugin/marketplace.json

echo "== python build =="
rm -rf dist && uv build

echo "== artifact validation =="
WHL=$(ls dist/inter_agent_claude_code-*.whl)
SDIST=$(ls dist/inter_agent_claude_code-0.2.0.tar.gz)
uv run python scripts/validate-artifacts.py "$WHL" "$SDIST"

echo "== run-checks OK =="