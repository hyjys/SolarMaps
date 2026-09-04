"""빌드 산출물(쾨펜 이진 격자, Pyodide용 zip)을 일괄 생성한다."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

STEPS = ["build_koppen.py", "build_pyodide_bundle.py"]


def main() -> None:
    for step in STEPS:
        print(f"--- {step} ---")
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / step)], cwd=ROOT)
        if result.returncode != 0:
            sys.exit(result.returncode)


if __name__ == "__main__":
    main()
