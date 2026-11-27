from __future__ import annotations

import csv
import shutil
from collections import Counter
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

from hiddencells import harmonize as hz
from hiddencells.build import PROJECT_ROOT
from hiddencells.mechanisms import MECHANISMS

DATA = PROJECT_ROOT / "data"
BUILT = [d for d in ("finance", "statistics") if (DATA / d / "cases.csv").exists()]


def _cases(domain):
    return list(csv.DictReader(open(DATA / domain / "cases.csv", encoding="utf-8")))


@pytest.mark.parametrize("domain", BUILT)
def test_every_scenario_gets_all_sixteen_variants(domain):
    rows = [r for r in _cases(domain) if r["injected_file"]]
    per_scenario = Counter(r["scenario"] for r in rows)
    assert len(per_scenario) == 6 and set(per_scenario.values()) == {16}
    assert Counter((r["mechanism"], r["payload_style"]) for r in rows) == {
        (m.name, s): 6 for m in MECHANISMS for s in hz.STYLES}


@pytest.mark.parametrize("domain", BUILT)
def test_written_files_pass_the_checks(domain):
    assert hz.verify(DATA / domain) == []


@pytest.mark.skipif("finance" not in BUILT, reason="finance set not built")
def test_finance_keeps_helpers_hidden_clean_files_for_the_false_removal_test():
    rows = _cases("finance")
    hidden = [r for r in rows if r["helpers"] == "hidden"]
    assert len(hidden) == 6 and not any(r["injected_file"] for r in hidden)


@pytest.mark.skipif("finance" not in BUILT or not (hz.TEAM_REPO / "sean").exists(),
                    reason="finance set or team repo clone missing")
def test_finance_keeps_seans_numbers_but_no_formulas():
    for path in sorted((DATA / "finance" / "clean").glob("*.xlsx")):
        assert hz.same_values(path, hz.TEAM_REPO / "sean" / "data" / "clean" / path.name), path.name
    assert sum(hz._formula_cells(p) for p in (DATA / "finance").rglob("*.xlsx")) == 0


def test_flatten_replaces_formulas_with_their_cached_values(tmp_path):
    from hiddencells.run_models import uncached_formulas
    seans = sorted((hz.TEAM_REPO / "sean" / "data" / "clean").glob("S1_clean_helpers-visible.xlsx"))
    if not seans:
        pytest.skip("team repo clone missing")
    copy = tmp_path / "s1.xlsx"
    shutil.copy(seans[0], copy)
    assert hz._formula_cells(copy) > 0 and uncached_formulas(copy) == 0
    hz.flatten(copy)
    assert hz._formula_cells(copy) == 0 and hz.same_values(copy, seans[0])


@pytest.mark.skipif("statistics" not in BUILT or not (hz.TEAM_REPO / "supanice").exists(),
                    reason="statistics set or team repo clone missing")
def test_statistics_rebuild_matches_ethans_five_datasets():
    original = hz.TEAM_REPO / "supanice" / "injection_testbed" / "clean"
    for path in sorted(original.glob("*.xlsx")):
        assert hz.same_values(DATA / "statistics" / "clean" / path.name, path), path.name


def test_set_sheet_state_changes_only_the_state(tmp_path):
    wb = Workbook()
    wb.active["A1"] = 42
    notes = wb.create_sheet("Notes")
    notes["A1"] = "payload"
    notes.sheet_state = "hidden"
    path = tmp_path / "book.xlsx"
    wb.save(path)
    hz._set_sheet_state(path, "Notes", "veryHidden")
    back = load_workbook(path)
    assert back["Notes"].sheet_state == "veryHidden"
    assert back["Notes"]["A1"].value == "payload" and back.worksheets[0]["A1"].value == 42
    with pytest.raises(RuntimeError):
        hz._set_sheet_state(path, "Missing", "veryHidden")
