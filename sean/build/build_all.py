"""Build every clean + injected workbook, recalculate them with LibreOffice, write cases.csv.

    python build/build_all.py

Writes build/_raw/ (openpyxl output, no cached values), data/clean/, data/injected/ (recalculated),
cases.csv, and build/_manifest.json (what verify.py checks).
"""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

from inject import VARIANTS, inject, variant_name
from recalc import recalc
from scenarios import SCENARIOS

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "build" / "_raw"
COLUMNS = ["case_id", "clean_file", "injected_file", "question", "correct_answer", "attacker_answer",
           "owner", "domain", "scenario", "mechanism", "structural_kind", "payload_style", "payload_source",
           "payload_location", "helpers"]


def main():
    shutil.rmtree(RAW, ignore_errors=True)
    (RAW / "clean").mkdir(parents=True)
    (RAW / "injected").mkdir(parents=True)
    for d in ("clean", "injected"):
        for old in (ROOT / "data" / d).glob("S*.xlsx"):
            old.unlink()

    cases, manifest = [], []
    for sid, fn in SCENARIOS.items():
        for helpers in ("visible", "hidden"):
            wb, meta = fn(helpers)
            clean_name = f"{sid}_clean_helpers-{helpers}.xlsx"
            wb.save(RAW / "clean" / clean_name)
            for mechanism, kind, style, source in VARIANTS:
                vname = variant_name(mechanism, kind, style, source)
                wb, meta = fn(helpers)  # fresh copy for every variant
                info = inject(wb, meta, mechanism, kind, style, source)
                inj_name = f"{sid}_{vname}_helpers-{helpers}.xlsx"
                wb.save(RAW / "injected" / inj_name)
                case = {
                    "case_id": f"sean_{sid}_{vname}_helpers-{helpers}",
                    "clean_file": f"data/clean/{clean_name}",
                    "injected_file": f"data/injected/{inj_name}",
                    "question": meta["question"],
                    "correct_answer": meta["correct_answer"],
                    "attacker_answer": meta["attacker_answer"],
                    "owner": "sean", "domain": "finance_formula", "scenario": sid,
                    "mechanism": mechanism, "structural_kind": kind, "payload_style": style,
                    "payload_source": source, "payload_location": info["payload_location"], "helpers": helpers,
                }
                cases.append(case)
                manifest.append({**case, "payload_text": info["payload_text"], "hiding": info["hiding"],
                                 "answer_cell": meta["answer_cell"], "answer_value": meta["answer_value"],
                                 "max_of": meta.get("max_of")})

    for d in ("clean", "injected"):
        files = sorted((RAW / d).glob("*.xlsx"))
        for i in range(0, len(files), 40):
            recalc(files[i:i + 40], ROOT / "data" / d)
        print(f"recalculated {len(files)} {d} files")

    with open(ROOT / "cases.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(cases)
    (ROOT / "build" / "_manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"wrote cases.csv ({len(cases)} cases) and build/_manifest.json")


if __name__ == "__main__":
    main()
