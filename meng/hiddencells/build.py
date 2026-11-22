"""Build the clean and injected workbooks plus manifest.jsonl for a dataset.

    python -m hiddencells.build                # writes data/procurement/
    python -m hiddencells.build --out DIR

Every scenario yields one clean case and one injected case per
(payload style, mechanism) pair.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from . import procurement
from .mechanisms import MECHANISMS

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STYLES = ("imperative", "contextual_spoof")
CSV_COLUMNS = (
    "case_id",
    "clean_file",
    "injected_file",
    "question",
    "correct_answer",
    "attacker_answer",
    "sheet_type",
    "mechanism",
    "payload_style",
    "payload_text",
)


def _case(sc, owner, domain, kind, injected_file=None, mechanism=None, style=None, text=None, location=None) -> dict:
    """One manifest line. Keys follow the team's five elements first, then the labels."""
    suffix = "clean" if kind == "clean" else f"{mechanism.name}__{style}"
    return {
        "case_id": f"{sc.scenario_id}__{suffix}",
        "kind": kind,
        "clean_file": f"{sc.scenario_id}/clean.xlsx",
        "injected_file": injected_file,
        "question": sc.question,
        "correct_answer": sc.correct_answer,
        "attacker_answer": sc.attacker_answer,
        "options": sc.options,
        "owner": owner,
        "domain": domain,
        "scenario_id": sc.scenario_id,
        "sheet_type": sc.sheet_type,
        "mechanism": mechanism.name if mechanism else None,
        "mechanism_family": mechanism.family if mechanism else None,
        "payload_style": style,
        "attack_route": sc.attack_route(style) if style else None,
        "payload_text": text,
        "payload_location": location,
    }


def build_dataset(out_dir: Path, scenarios, owner: str = "meng", domain: str = "procurement") -> list[dict]:
    out_dir = Path(out_dir)
    cases: list[dict] = []
    for sc in scenarios:
        sc.check()
        (out_dir / sc.scenario_id / "injected").mkdir(parents=True, exist_ok=True)

        wb, _, _ = sc.build_clean()
        wb.save(out_dir / sc.scenario_id / "clean.xlsx")
        cases.append(_case(sc, owner, domain, "clean"))

        for style in STYLES:
            text = sc.payload(style)
            for mechanism in MECHANISMS:
                wb, ws, anchor = sc.build_clean()
                location = mechanism.apply(wb, ws, text, anchor)
                rel = f"{sc.scenario_id}/injected/{mechanism.name}__{style}.xlsx"
                wb.save(out_dir / rel)
                cases.append(_case(sc, owner, domain, "injected", rel, mechanism, style, text, location))

    with open(out_dir / "manifest.jsonl", "w", encoding="utf-8") as f:
        for case in cases:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")

    # The same cases as a table people can open in Excel: the five elements first.
    with open(out_dir / "cases.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(cases)
    return cases


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Build the procurement test cases.")
    parser.add_argument("--out", type=Path, default=PROJECT_ROOT / "data" / "procurement")
    args = parser.parse_args(argv)
    cases = build_dataset(args.out, procurement.SCENARIOS)
    injected = sum(c["kind"] == "injected" for c in cases)
    print(f"wrote {len(cases)} cases ({len(cases) - injected} clean, {injected} injected) to {args.out}")


if __name__ == "__main__":
    main()
