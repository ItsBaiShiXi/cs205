"""All pre-run checks from CLAUDE.md section 7. Exit code 0 only if everything passes.

    python build/verify.py
"""

from __future__ import annotations

import difflib
import json
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "build"))

from run_models import sheet_text, uncached_formulas  # noqa: E402
import check_labels  # noqa: E402
from inject import HIDDEN_SHEET  # noqa: E402

MAX_CHARS = 30000
problems: list[str] = []
_text, _wb, _wbf = {}, {}, {}


def bad(msg):
    problems.append(msg)


def text(rel):
    if rel not in _text:
        _text[rel] = sheet_text(ROOT / rel)
    return _text[rel]


def wb_values(rel):  # opened only to read; never saved
    if rel not in _wb:
        _wb[rel] = openpyxl.load_workbook(ROOT / rel, data_only=True)
    return _wb[rel]


def wb_formulas(rel):
    if rel not in _wbf:
        _wbf[rel] = openpyxl.load_workbook(ROOT / rel)
    return _wbf[rel]


def col_hidden(ws, letter):
    idx = openpyxl.utils.column_index_from_string(letter)
    return any(d.hidden and d.min <= idx <= d.max for d in ws.column_dimensions.values())


def white_1pt(cell):
    rgb = (cell.font.color.rgb if cell.font and cell.font.color else "") or ""
    return isinstance(rgb, str) and rgb.upper().endswith("FFFFFF") and cell.font.sz == 1


def check_answer(rel, c):
    sheet, ref = c["answer_cell"]
    got = wb_values(rel)[sheet][ref].value
    if got is None or abs(float(got) - float(c["answer_value"])) > 0.005:
        bad(f"{rel}: {sheet}!{ref} = {got!r}, expected {c['answer_value']}")
    if c["max_of"]:
        sh, col, r0, r1 = c["max_of"]
        vals = [wb_values(rel)[sh][f"{col}{r}"].value for r in range(r0, r1 + 1)]
        if max(vals) != got:
            bad(f"{rel}: answer cell {ref} is not the max of {col}{r0}:{col}{r1} ({vals})")
    else:
        if abs(float(c["correct_answer"]) - float(got)) > 0.005:
            bad(f"{rel}: correct_answer {c['correct_answer']} != cell value {got}")


def check_diff(c):
    clean, inj = text(c["clean_file"]).splitlines(), text(c["injected_file"]).splitlines()
    sm = difflib.SequenceMatcher(a=clean, b=inj, autojunk=False)
    allowed = {"", f"### Sheet: {HIDDEN_SHEET}", "Note"}
    for op, a0, a1, b0, b1 in sm.get_opcodes():
        if op == "equal":
            continue
        if op != "insert":
            bad(f"{c['case_id']}: clean lines changed/removed: {clean[a0:a1]} -> {inj[b0:b1]}")
            continue
        for line in inj[b0:b1]:
            if c["payload_text"] not in line and line not in allowed:
                bad(f"{c['case_id']}: unexpected added line {line!r}")


def check_hiding(c):
    h, rel = c["hiding"], c["injected_file"]
    wb = wb_formulas(rel)
    for kind, where in h.items():
        if kind == "sheet_hidden":
            ok = wb[where].sheet_state == "hidden"
        elif kind == "row_hidden":
            sh, r = where.split("!")
            ok = bool(wb[sh].row_dimensions[int(r)].hidden)
        else:
            sh, ref = where.split("!")
            cell = wb[sh][ref]
            ok = {"number_format": cell.number_format == ";;;",
                  "white_1pt": white_1pt(cell),
                  "formula_cell": isinstance(cell.value, str) and cell.value.startswith("=")}[kind]
        if not ok:
            bad(f"{c['case_id']}: hiding property {kind} at {where} missing")
    if c["helpers"] == "hidden":
        sheet, ref = c["answer_cell"]
        for rel_ in (c["clean_file"], rel):
            if wb_formulas(rel_)[sheet][ref].number_format != ";;;":
                bad(f"{rel_}: helpers=hidden but answer cell {ref} is not ;;;")
            if not any(d.hidden for ws in wb_formulas(rel_).worksheets for d in ws.column_dimensions.values()):
                bad(f"{rel_}: helpers=hidden but no hidden helper column in any sheet")


def main() -> int:
    cases = json.loads((ROOT / "build" / "_manifest.json").read_text(encoding="utf-8"))
    files = sorted({c["clean_file"] for c in cases} | {c["injected_file"] for c in cases})
    for rel in files:
        if n := uncached_formulas(ROOT / rel):
            bad(f"{rel}: {n} uncached formula cell(s)")
        if len(text(rel)) > MAX_CHARS:
            bad(f"{rel}: sheet_text has {len(text(rel))} chars (> {MAX_CHARS})")
    for c in cases:
        check_answer(c["clean_file"], c)
        check_answer(c["injected_file"], c)
        if c["payload_text"] not in text(c["injected_file"]):
            bad(f"{c['case_id']}: payload text not in sheet_text(injected)")
        if c["payload_text"] in text(c["clean_file"]):
            bad(f"{c['case_id']}: payload text found in clean file")
        check_diff(c)
        check_hiding(c)

    # helpers=hidden vs visible: expected to give identical text (CLAUDE.md 4.6)
    same = sum(text(c["injected_file"]) == text(c["injected_file"].replace("helpers-hidden", "helpers-visible"))
               for c in cases if c["helpers"] == "hidden")
    same_clean = sum(text(f) == text(f.replace("helpers-hidden", "helpers-visible"))
                     for f in {c["clean_file"] for c in cases if c["helpers"] == "hidden"})
    longest = max(files, key=lambda f: len(text(f)))

    print(f"files: {len(files)}, cases: {len(cases)}")
    print(f"helpers hidden == visible text: injected {same}/{sum(c['helpers'] == 'hidden' for c in cases)}, "
          f"clean {same_clean}/{len({c['clean_file'] for c in cases if c['helpers'] == 'hidden'})}")
    print(f"longest sheet_text: {len(text(longest))} chars ({longest})")
    print("label checks:", "ok" if _labels_ok() else "FAILED")
    for p in problems:
        print("PROBLEM:", p)
    print(f"\n{len(problems)} problem(s)")
    return 1 if problems else 0


def _labels_ok() -> bool:
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        rc = check_labels.main()
    if rc:
        bad("check_labels.py reports mismatches")
    return rc == 0


if __name__ == "__main__":
    raise SystemExit(main())
