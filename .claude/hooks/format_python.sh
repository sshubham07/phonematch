#!/usr/bin/env bash
# PostToolUse hook: auto-format and lint-fix any Python file Claude edits.
# Lint errors that can't be auto-fixed are sent back to Claude (exit 2) so it fixes them.

file_path=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))')

[[ "$file_path" == *.py ]] || exit 0
[[ -f "$file_path" ]] || exit 0

if command -v uv >/dev/null 2>&1 && [[ -f "$CLAUDE_PROJECT_DIR/pyproject.toml" ]]; then
  RUFF="uv run --quiet ruff"
elif command -v ruff >/dev/null 2>&1; then
  RUFF="ruff"
else
  exit 0  # ruff not installed yet (before milestone M0) - skip silently
fi

$RUFF format --quiet "$file_path"
if ! output=$($RUFF check --fix --quiet "$file_path" 2>&1); then
  echo "ruff found issues in $file_path that need a manual fix:" >&2
  echo "$output" >&2
  exit 2
fi
exit 0
