"""Run the team's run_models.py with API keys loaded from ../.env (KEY=value lines).

    python build/run_env.py --cases cases.csv --provider deepseek --model deepseek-flash --by ...

Takes the same arguments as run_models.py. Variables already set in the environment win.
Never prints the keys.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def load_env(path: Path) -> list[str]:
    loaded = []
    if not path.is_file():
        return loaded
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        value = value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    return loaded


if __name__ == "__main__":
    names = load_env(ROOT / ".env")
    print(f"loaded from .env: {', '.join(names) or 'nothing'}", flush=True)
    import run_models
    run_models.main()
