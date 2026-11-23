from __future__ import annotations

import csv
import dataclasses
import json
import re

import openpyxl
import pytest
from openpyxl.styles import Font
from openpyxl.utils.cell import coordinate_from_string

from hiddencells import build, exposure, procurement
from hiddencells.mechanisms import BY_NAME, MECHANISMS

SHEET_MECHANISMS = {"hidden_sheet", "very_hidden_sheet"}
SCENARIOS = procurement.SCENARIOS
BY_ID = {sc.scenario_id: sc for sc in SCENARIOS}


def _injected(cases):
    return [c for c in cases if c["kind"] == "injected"]


def _cells(wb) -> dict:
    return {
        (ws.title, cell.coordinate): cell.value
        for ws in wb.worksheets
        for row in ws.iter_rows()
        for cell in row
        if cell.value is not None
    }


# --- scenarios -------------------------------------------------------------


def test_three_scenarios_per_sheet_type():
    types = [sc.sheet_type for sc in SCENARIOS]
    assert {t: types.count(t) for t in set(types)} == {
        "quote_comparison": 3,
        "cloud_pricing": 3,
        "evaluation_matrix": 3,
    }
    assert len({sc.scenario_id for sc in SCENARIOS}) == len(SCENARIOS)


@pytest.mark.parametrize("sc", SCENARIOS, ids=lambda s: s.scenario_id)
def test_decision_column_matches_its_inputs(sc):
    """Recompute every decision value from the other columns (and the note, for the workload)."""
    for row in sc.rows:
        if sc.sheet_type == "quote_comparison":
            expected = row[1] * row[2] + row[3]
        elif sc.sheet_type == "evaluation_matrix":
            expected = 0.4 * row[1] + 0.3 * row[2] + 0.2 * row[3] + 0.1 * row[4]
        else:
            m = re.search(r"([\d,]+) vCPU-hours, ([\d,]+) GB-months of storage and ([\d,]+) GB", sc.note)
            hours, storage, egress = (int(g.replace(",", "")) for g in m.groups())
            expected = row[1] * hours + row[2] * storage + row[3] * egress
        assert row[sc.decision_col] == pytest.approx(expected, abs=0.005), row[0]


@pytest.mark.parametrize("sc", SCENARIOS, ids=lambda s: s.scenario_id)
def test_correct_is_the_best_row_and_attacker_the_worst(sc):
    ranked = sorted(sc.rows, key=lambda r: r[sc.decision_col], reverse=sc.objective == "max")
    assert sc.correct_answer == ranked[0][0]
    assert sc.attacker_answer == ranked[-1][0]


@pytest.mark.parametrize("sc", SCENARIOS, ids=lambda s: s.scenario_id)
def test_spoofed_adjustment_makes_the_attacker_best(sc):
    adjusted = sc.adjusted_values()
    pick = min if sc.objective == "min" else max
    assert pick(adjusted, key=adjusted.get) == sc.attacker_answer


@pytest.mark.parametrize("sc", SCENARIOS, ids=lambda s: s.scenario_id)
def test_check_rejects_an_adjustment_too_small_to_flip_the_answer(sc):
    with pytest.raises(ValueError, match="adjust_pct"):
        dataclasses.replace(sc, adjust_pct=1).check()


@pytest.mark.parametrize("sc", SCENARIOS, ids=lambda s: s.scenario_id)
def test_payloads_name_the_attacker_and_fill_every_placeholder(sc):
    for style in build.STYLES:
        text = sc.payload(style)
        assert sc.attacker_answer in text
        assert "{" not in text and "}" not in text
    spoof = sc.payload("contextual_spoof")
    assert all(o in spoof for o in sc.options)


def test_attacker_and_correct_answers_move_around():
    positions = {(sc.options.index(sc.correct_answer), sc.options.index(sc.attacker_answer)) for sc in SCENARIOS}
    assert len(positions) >= 5


# --- generated files -------------------------------------------------------


def test_one_clean_case_plus_every_mechanism_and_style(dataset):
    _, cases = dataset
    per_scenario = 1 + len(MECHANISMS) * len(build.STYLES)
    assert len(cases) == per_scenario * len(SCENARIOS)
    assert len({c["case_id"] for c in cases}) == len(cases)


def test_manifest_file_matches_returned_cases(dataset):
    out, cases = dataset
    lines = (out / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line) for line in lines] == cases


def test_cases_csv_lists_the_five_elements(dataset):
    out, cases = dataset
    with open(out / "cases.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert list(rows[0])[:6] == [
        "case_id", "clean_file", "injected_file", "question", "correct_answer", "attacker_answer",
    ]
    assert [r["case_id"] for r in rows] == [c["case_id"] for c in cases]
    for row, case in zip(rows, cases):
        for key in ("clean_file", "question", "correct_answer", "attacker_answer"):
            assert row[key] == case[key]
        assert row["injected_file"] == (case["injected_file"] or "")


def test_clean_workbook_has_one_sheet_and_no_payload(dataset):
    out, cases = dataset
    payloads = {c["payload_text"] for c in _injected(cases)}
    for case in cases:
        if case["kind"] != "clean":
            continue
        wb = openpyxl.load_workbook(out / case["clean_file"])
        assert len(wb.worksheets) == 1
        assert not payloads & set(_cells(wb).values())


def test_injection_only_adds_the_payload_cell(dataset):
    out, cases = dataset
    for case in _injected(cases):
        clean = _cells(openpyxl.load_workbook(out / case["clean_file"]))
        injected = _cells(openpyxl.load_workbook(out / case["injected_file"]))
        loc = case["payload_location"]
        key = (loc["sheet"], loc["cell"])
        assert injected[key] == case["payload_text"], case["case_id"]
        assert {k: v for k, v in injected.items() if k != key} == clean, case["case_id"]


def test_payload_is_hidden_by_its_own_mechanism_only(dataset):
    out, cases = dataset
    for case in _injected(cases):
        wb = openpyxl.load_workbook(out / case["injected_file"])
        loc = case["payload_location"]
        assert BY_NAME[case["mechanism"]].is_applied(wb, loc), case["case_id"]
        others = [
            m.name
            for m in MECHANISMS
            if m.name != case["mechanism"] and m.is_applied(wb, loc)
        ]
        assert others == [], case["case_id"]


def test_main_sheet_stays_first_visible_and_active(dataset):
    out, cases = dataset
    for case in cases:
        title = BY_ID[case["scenario_id"]].sheet_title
        wb = openpyxl.load_workbook(out / (case["injected_file"] or case["clean_file"]))
        assert wb.worksheets[0].title == title
        assert wb.worksheets[0].sheet_state == "visible"
        assert wb.active.title == title


def _undo(wb, mechanism: str, loc: dict) -> None:
    ws = wb[loc["sheet"]]
    cell = ws[loc["cell"]]
    _, row = coordinate_from_string(loc["cell"])
    if mechanism == "custom_format":
        cell.number_format = "General"
    elif mechanism == "hidden_row":
        ws.row_dimensions[row].hidden = False
    elif mechanism == "hidden_column":
        for dim in ws.column_dimensions.values():
            dim.hidden = False
    elif mechanism in SHEET_MECHANISMS:
        ws.sheet_state = "visible"
    elif mechanism == "white_text":
        cell.font = Font(color="FF000000")
    elif mechanism == "tiny_font":
        cell.font = Font(size=11)
    else:
        raise AssertionError(f"no undo for {mechanism}")


@pytest.mark.parametrize("mechanism", [m.name for m in MECHANISMS if m.name != "visible"])
def test_checks_fail_once_the_hiding_is_undone(dataset, mechanism):
    """Failure path: the checks above must be able to go red."""
    out, cases = dataset
    case = next(c for c in _injected(cases) if c["mechanism"] == mechanism)
    wb = openpyxl.load_workbook(out / case["injected_file"])
    loc = case["payload_location"]
    _undo(wb, mechanism, loc)
    assert not BY_NAME[mechanism].is_applied(wb, loc)
    assert BY_NAME["visible"].is_applied(wb, loc)


def test_exposure_by_parser(dataset):
    out, _ = dataset
    for row in exposure.exposure(out / "manifest.jsonl"):
        on_other_sheet = row["mechanism"] in SHEET_MECHANISMS
        # pd.read_excel(path) reads only the first sheet.
        assert row["pandas_first_sheet"] is (not on_other_sheet), row["case_id"]
        assert row["pandas_all_sheets"] is True, row["case_id"]
        assert row["openpyxl_all_cells"] is True, row["case_id"]
