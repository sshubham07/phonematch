#!/usr/bin/env python3
"""PreToolUse hook: block edits to secrets, raw data and already-applied Alembic migrations.

Exit code 2 blocks the tool call and shows stderr to Claude.
"""

import json
import subprocess
import sys
from pathlib import Path

data = json.load(sys.stdin)
file_path = data.get("tool_input", {}).get("file_path", "")
if not file_path:
    sys.exit(0)

path = Path(file_path)
name = path.name
parts = path.parts

if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
    print("Blocked: .env files hold secrets. Edit .env.example instead.", file=sys.stderr)
    sys.exit(2)

if "data" in parts and "raw" in parts:
    print(
        "Blocked: data/raw/ is the immutable raw layer. Write derived data to the DB.",
        file=sys.stderr,
    )
    sys.exit(2)

# Existing migration files that are already committed must not be edited.
if "versions" in parts and "alembic" in "/".join(parts) and path.exists():
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)],
        capture_output=True,
        cwd=path.parent,
    )
    if tracked.returncode == 0:
        print(
            "Blocked: this Alembic migration is already committed. "
            "Create a new migration with `uv run alembic revision -m ...` instead.",
            file=sys.stderr,
        )
        sys.exit(2)

sys.exit(0)
