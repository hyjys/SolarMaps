"""solarmaps/ 패키지를 public/py/solarmaps.zip으로 압축한다.

Pyodide는 이 zip을 fetch()로 받아 micropip 없이 sys.path에 마운트할 수 있는
순수 파이썬 zip 임포트(zipimport)를 지원한다. 표준 라이브러리만 쓰는 패키지라
별도 휠 빌드 없이 소스 그대로 압축하면 된다.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = ROOT / "solarmaps"
OUT_PATH = ROOT / "public" / "py" / "solarmaps.zip"


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for py_file in sorted(PACKAGE_DIR.rglob("*.py")):
            if "__pycache__" in py_file.parts:
                continue
            arcname = py_file.relative_to(ROOT)  # solarmaps/xxx.py 형태로 보존
            zf.write(py_file, arcname)

    size_kb = OUT_PATH.stat().st_size / 1024
    print(f"{OUT_PATH.relative_to(ROOT)}: {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
