"""Recalculate xlsx files with LibreOffice headless so formula cells get cached values.

    python build/recalc.py <out_dir> <in1.xlsx> [<in2.xlsx> ...]

Uses a private LibreOffice profile so it works even if the LibreOffice GUI is open.
Never open-and-save the output with openpyxl afterwards (that drops cached values again).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CANDIDATES = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
]


def soffice() -> str:
    found = shutil.which("soffice")
    if found:
        return found
    for c in CANDIDATES:
        if os.path.exists(c):
            return c
    raise SystemExit("LibreOffice soffice not found")


def recalc(paths, out_dir) -> list[Path]:
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = [Path(p).resolve() for p in paths]
    for p in paths:
        if p.parent == out_dir:
            raise SystemExit(f"{p}: input and output folder must differ")
    with tempfile.TemporaryDirectory() as profile:
        cmd = [soffice(), f"-env:UserInstallation={Path(profile).as_uri()}",
               "--headless", "--calc", "--convert-to", "xlsx", "--outdir", str(out_dir), *map(str, paths)]
        subprocess.run(cmd, check=True, capture_output=True, timeout=600)
    outs = [out_dir / p.name for p in paths]
    missing = [o for o in outs if not o.exists()]
    if missing:
        raise SystemExit(f"LibreOffice did not write: {missing}")
    return outs


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    for o in recalc(sys.argv[2:], sys.argv[1]):
        print(o)
