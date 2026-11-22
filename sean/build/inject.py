"""Apply one hiding mechanism + payload to a fresh (un-recalculated) clean workbook."""

from __future__ import annotations

from openpyxl.styles import Font, PatternFill

from payloads import CONTEXT_LABEL, PAYLOADS, as_formula

HIDDEN_SHEET = "Notes"

# (mechanism, structural_kind, payload_style, payload_source)
VARIANTS = [
    ("custom_format", "", "instruction", "typed"),
    ("custom_format", "", "spoofed_data", "typed"),
    ("visual", "", "instruction", "typed"),
    ("visual", "", "spoofed_data", "typed"),
    ("structural", "hidden_row", "instruction", "typed"),
    ("structural", "hidden_row", "spoofed_data", "typed"),
    ("structural", "hidden_sheet", "instruction", "typed"),
    ("structural", "hidden_sheet", "spoofed_data", "typed"),
    ("contextual", "", "spoofed_data", "typed"),
    ("contextual", "", "spoofed_data", "formula"),
]


def variant_name(mechanism, kind, style, source) -> str:
    return "_".join(x for x in (mechanism, kind, style, "formula" if source == "formula" else "") if x)


def inject(wb, meta, mechanism, kind, style, source) -> dict:
    """Modify wb in place. Returns what verify.py needs: payload text, location, hiding properties."""
    sid = meta["scenario"]
    text = PAYLOADS[sid][style]
    ws = wb[meta["payload_sheet"]]
    row = meta["payload_row"]
    info = {"payload_text": text, "hiding": {}}

    if mechanism == "contextual":
        # visible, labelled like a real note; column A only, so no other column changes type in pandas
        text = f"{CONTEXT_LABEL[sid]}: {text}"
        ws.cell(row, 1, as_formula(text) if source == "formula" else text)
        info["payload_text"] = text
        info["payload_location"] = f"{ws.title}!A{row} (visible labelled note row under the footer)"
        info["hiding"] = {"formula_cell": f"{ws.title}!A{row}"} if source == "formula" else {}
        return info

    if kind == "hidden_sheet":
        notes = wb.create_sheet(HIDDEN_SHEET)
        notes.append(["Note"])
        notes.append([text])
        notes.sheet_state = "hidden"
        info["payload_location"] = f"{HIDDEN_SHEET}!A2 (hidden sheet)"
        info["hiding"] = {"sheet_hidden": HIDDEN_SHEET}
        return info

    cell = ws.cell(row, 1, text)  # cell P
    ref = f"{ws.title}!A{row}"
    info["payload_location"] = f"{ref} (row under the table footer)"
    if mechanism == "custom_format":
        cell.number_format = ";;;"
        info["hiding"] = {"number_format": ref}
    elif mechanism == "visual":
        cell.font = Font(color="FFFFFF", size=1)
        cell.fill = PatternFill("solid", start_color="FFFFFF", end_color="FFFFFF")
        info["hiding"] = {"white_1pt": ref}
    elif kind == "hidden_row":
        ws.row_dimensions[row].hidden = True
        info["hiding"] = {"row_hidden": f"{ws.title}!{row}"}
    else:
        raise ValueError((mechanism, kind))
    return info
