#!/usr/bin/env bash
# OpenAPI / GitHub Actions workflow の YAML 構文を検証する（MVP）。
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${ROOT}"

python3 <<'PY'
from pathlib import Path
import sys

try:
    import yaml
except ImportError:
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "pyyaml"])
    import yaml

targets = list(Path("packages/contracts/openapi").glob("*.yaml"))
targets.extend(Path(".github/workflows").glob("*.yml"))

for path in sorted(targets):
    with path.open(encoding="utf-8") as fh:
        yaml.safe_load(fh)
    print(f"ok: {path}")

print(f"result: OK ({len(targets)} YAML file(s))")
PY
