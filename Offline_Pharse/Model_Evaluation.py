"""Legacy evaluation entry point.

The production evaluation pipeline now lives in the top-level ``evaluation/``
folder. This wrapper is kept so old references to Offline_Pharse still work
without relying on Colab or local Windows paths.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    command = [sys.executable, str(ROOT / "evaluation" / "run_all.py")]
    raise SystemExit(subprocess.call(command, cwd=ROOT))


if __name__ == "__main__":
    main()

