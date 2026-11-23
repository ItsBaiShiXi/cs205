"""Report which parser views expose each injected payload (the Exposure metric).

    python -m hiddencells.exposure                          # data/procurement/manifest.jsonl
    python -m hiddencells.exposure path/to/manifest.jsonl

"Exposed" means the full payload text appears in what the parser returns.
That is an upper bound on what reaches the model: `print(df)` cuts strings
at 50 characters, so a script that only prints the frame shows part of it.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import openpyxl
import pandas as pd

from .build import PROJECT_ROOT


def _frame_text(df: pd.DataFrame) -> str:
    cells = [str(v) for v in df.to_numpy().ravel()]
    return "\n".join([*map(str, df.columns), *cells])


def _pandas_first_sheet(path: Path) -> str:
    # The usual first line of an LLM-written analysis script.
    return _frame_text(pd.read_excel(path))


def _pandas_all_sheets(path: Path) -> str:
    return "\n".join(_frame_text(df) for df in pd.read_excel(path, sheet_name=None).values())


def _openpyxl_all_cells(path: Path) -> str:
    wb = openpyxl.load_workbook(path)
    return "\n".join(
        str(cell.value)
        for ws in wb.worksheets
        for row in ws.iter_rows()
        for cell in row
        if cell.value is not None
    )


VIEWS = {
    "pandas_first_sheet": _pandas_first_sheet,
    "pandas_all_sheets": _pandas_all_sheets,
    "openpyxl_all_cells": _openpyxl_all_cells,
}


def exposure(manifest: Path) -> list[dict]:
    manifest = Path(manifest)
    rows = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        case = json.loads(line)
        if case["kind"] != "injected":
            continue
        path = manifest.parent / case["injected_file"]
        row = {k: case[k] for k in ("case_id", "mechanism", "payload_style")}
        row.update({name: case["payload_text"] in view(path) for name, view in VIEWS.items()})
        rows.append(row)
    return rows


def markdown_table(rows: list[dict]) -> str:
    mechanisms = list(dict.fromkeys(r["mechanism"] for r in rows))
    lines = [
        "| mechanism | " + " | ".join(VIEWS) + " |",
        "|---|" + "---|" * len(VIEWS),
    ]
    for m in mechanisms:
        group = [r for r in rows if r["mechanism"] == m]
        counts = [f"{sum(r[v] for r in group)}/{len(group)}" for v in VIEWS]
        lines.append(f"| {m} | " + " | ".join(counts) + " |")
    return "\n".join(lines)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Which parsers expose each payload.")
    parser.add_argument(
        "manifest", nargs="?", type=Path, default=PROJECT_ROOT / "data" / "procurement" / "manifest.jsonl"
    )
    args = parser.parse_args(argv)
    print(markdown_table(exposure(args.manifest)))


if __name__ == "__main__":
    main()
