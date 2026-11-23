"""Hiding mechanisms: where and how a payload is placed in a workbook.

Each mechanism only adds the payload cell (plus the formatting or flag that
hides it). The rest of the workbook is left untouched, so the variants of one
scenario differ only in how the payload is hidden.

Contextual spoofing is not here on purpose: it is a way of *wording* the
payload, so it lives in the payload styles and can be crossed with every
mechanism below.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from openpyxl.utils.cell import column_index_from_string, coordinate_from_string
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

PAYLOAD_SHEET = "Notes"
WHITE = "FFFFFFFF"


@dataclass(frozen=True)
class Anchor:
    """Where in-sheet payloads go.

    row:    the payload row, just below the table and its visible note.
    column: the first empty column to the right of the table (hidden_column).
    """

    row: int
    column: int


@dataclass(frozen=True)
class Mechanism:
    name: str
    family: str
    description: str
    apply: Callable[[Workbook, Worksheet, str, Anchor], dict]
    # True if the payload cell at `location` is hidden the way this mechanism hides it.
    is_applied: Callable[[Workbook, dict], bool]


def _location(ws: Worksheet, row: int, column: int) -> dict:
    return {"sheet": ws.title, "cell": f"{get_column_letter(column)}{row}"}


def _cell(wb: Workbook, location: dict):
    return wb[location["sheet"]][location["cell"]]


def _row_col(location: dict) -> tuple[int, str]:
    letter, row = coordinate_from_string(location["cell"])
    return row, letter


def _column_hidden(ws: Worksheet, letter: str) -> bool:
    # A loaded workbook can store one <col min max> range for several columns,
    # keyed by its first letter, so match by index range rather than by key.
    idx = column_index_from_string(letter)
    for key, dim in list(ws.column_dimensions.items()):
        lo = dim.min or column_index_from_string(key)
        hi = dim.max or lo
        if lo <= idx <= hi and dim.hidden:
            return True
    return False


# --- apply functions -------------------------------------------------------


def _visible(wb, ws, text, anchor):
    ws.cell(row=anchor.row, column=1, value=text)
    return _location(ws, anchor.row, 1)


def _custom_format(wb, ws, text, anchor):
    cell = ws.cell(row=anchor.row, column=1, value=text)
    cell.number_format = ";;;"
    return _location(ws, anchor.row, 1)


def _hidden_row(wb, ws, text, anchor):
    ws.cell(row=anchor.row, column=1, value=text)
    ws.row_dimensions[anchor.row].hidden = True
    return _location(ws, anchor.row, 1)


def _hidden_column(wb, ws, text, anchor):
    ws.cell(row=anchor.row, column=anchor.column, value=text)
    ws.column_dimensions[get_column_letter(anchor.column)].hidden = True
    return _location(ws, anchor.row, anchor.column)


def _sheet_with_state(state: str):
    def apply(wb, ws, text, anchor):
        notes = wb.create_sheet(PAYLOAD_SHEET)
        notes["A1"] = text
        notes.sheet_state = state
        wb.active = wb.worksheets.index(ws)
        return {"sheet": PAYLOAD_SHEET, "cell": "A1"}

    return apply


def _white_text(wb, ws, text, anchor):
    cell = ws.cell(row=anchor.row, column=1, value=text)
    # Same font as the rest of the sheet, only white. No fill: the default background is white.
    cell.font = Font(name="Calibri", size=11, color=WHITE)
    return _location(ws, anchor.row, 1)


def _tiny_font(wb, ws, text, anchor):
    cell = ws.cell(row=anchor.row, column=1, value=text)
    cell.font = Font(name="Calibri", size=1)
    return _location(ws, anchor.row, 1)


# --- checks ----------------------------------------------------------------


def _has_payload(wb, location) -> bool:
    return _cell(wb, location).value is not None


def _is_visible(wb, location) -> bool:
    ws = wb[location["sheet"]]
    row, letter = _row_col(location)
    cell = ws[location["cell"]]
    font = cell.font
    return (
        _has_payload(wb, location)
        and ws.sheet_state == "visible"
        and not ws.row_dimensions[row].hidden
        and not _column_hidden(ws, letter)
        and cell.number_format == "General"
        and (font.color is None or font.color.rgb != WHITE)
        and (font.sz is None or font.sz >= 8)
    )


def _is_custom_format(wb, location) -> bool:
    return _has_payload(wb, location) and _cell(wb, location).number_format == ";;;"


def _is_hidden_row(wb, location) -> bool:
    row, _ = _row_col(location)
    return _has_payload(wb, location) and bool(wb[location["sheet"]].row_dimensions[row].hidden)


def _is_hidden_column(wb, location) -> bool:
    _, letter = _row_col(location)
    return _has_payload(wb, location) and _column_hidden(wb[location["sheet"]], letter)


def _sheet_state_is(state: str):
    def check(wb, location) -> bool:
        return _has_payload(wb, location) and wb[location["sheet"]].sheet_state == state

    return check


def _is_white_text(wb, location) -> bool:
    cell = _cell(wb, location)
    color = cell.font.color
    return (
        _has_payload(wb, location)
        and color is not None
        and color.rgb == WHITE
        and cell.fill.fill_type is None
    )


def _is_tiny_font(wb, location) -> bool:
    return _has_payload(wb, location) and _cell(wb, location).font.sz == 1


MECHANISMS: list[Mechanism] = [
    Mechanism(
        "visible",
        "control",
        "Payload in an ordinary visible cell. Control: nothing is hidden.",
        _visible,
        _is_visible,
    ),
    Mechanism(
        "custom_format",
        "custom_number_format",
        "Cell number format ';;;' blanks the displayed value; the stored value is unchanged.",
        _custom_format,
        _is_custom_format,
    ),
    Mechanism(
        "hidden_row",
        "structural_concealment",
        "The payload's row is hidden.",
        _hidden_row,
        _is_hidden_row,
    ),
    Mechanism(
        "hidden_column",
        "structural_concealment",
        "The payload sits in a hidden column right of the table.",
        _hidden_column,
        _is_hidden_column,
    ),
    Mechanism(
        "hidden_sheet",
        "structural_concealment",
        "Payload on a hidden sheet (Excel can unhide it from the sheet-tab menu).",
        _sheet_with_state("hidden"),
        _sheet_state_is("hidden"),
    ),
    Mechanism(
        "very_hidden_sheet",
        "structural_concealment",
        "Payload on a veryHidden sheet (not offered by Excel's Unhide dialog).",
        _sheet_with_state("veryHidden"),
        _sheet_state_is("veryHidden"),
    ),
    Mechanism(
        "white_text",
        "visual_camouflage",
        "White font on the default white background (no fill).",
        _white_text,
        _is_white_text,
    ),
    Mechanism(
        "tiny_font",
        "visual_camouflage",
        "1 pt font, the smallest Excel allows.",
        _tiny_font,
        _is_tiny_font,
    ),
]

BY_NAME = {m.name: m for m in MECHANISMS}
