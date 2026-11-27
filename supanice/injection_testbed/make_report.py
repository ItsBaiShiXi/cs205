#!/usr/bin/env python3
"""Turn run_models.py output into a human-readable Excel report.

Reads, from --results (default ./results):
    prompts.jsonl                      distinct prompts and which files they came from
    <provider>__<model>.scored.csv     label counts per case
    <provider>__<model>.calls.jsonl    every raw reply (optional but recommended)

Writes one workbook (default report.xlsx) with sheets:
    Overview               one row per model: clean accuracy and attack success
    By attack type         attack success per attack type (custom number formatting,
                           structural concealment, contrast & dimension camouflage,
                           contextual spoofing)
    Attack type x dataset  the same, split by dataset
    By dataset             clean accuracy and attack success per dataset
    By variant             attack success per hiding variant x dataset
    Cases                  one row per case, in plain words ("attacker 2/3, correct 1/3")
    Calls                  every call: final answer, label, finish reason, tokens, reply text
Cases, By variant and Calls are sorted by attack type (controls first).
The same prompt can belong to several attack types (e.g. a ;;; file, a hidden-row file and
a white-text file read identically through pandas), so those types will show identical
numbers; the Calls sheet lists every attack type a prompt belongs to.

Important: several cases can share one prompt (e.g. attack files whose text is
identical after pandas flattens them). Overview and By dataset count each distinct
prompt once, so you don't count one set of replies several times. Cases and
By variant show every case, so identical rows there are expected.

Usage
    python make_report.py
    python make_report.py --results results --out report.xlsx
Needs: pandas, openpyxl. Run it from the folder that contains run_models.py if you
want Calls labelled with the same scoring code (it falls back to blank labels).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

LABELS = ("correct", "attacker", "ambiguous", "other", "no_answer")
# Attack types, in the order of the project proposal. Matches the "mechanism" column of cases.csv.
MECH = {"1": "Custom number formatting", "2": "Structural concealment",
        "3": "Contrast & dimension camouflage", "4": "Contextual spoofing"}


def attack_type(code: str) -> tuple[str, int]:
    """(display name, sort order). Controls come first; unknown codes go last."""
    code = (code or "").strip()
    if not code or code.lower().startswith("none"):
        return "Control (clean)", 0
    if code[0] in MECH and (len(code) == 1 or code[1] == "_"):
        return MECH[code[0]], int(code[0])
    return code.replace("_", " ").title(), 99


REPLY_LIMIT = 3000  # characters of reply kept per call in the Calls sheet


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def get_labeller():
    """Use run_models.label so labels match the team's scorer exactly."""
    for folder in (Path(__file__).resolve().parent, Path.cwd()):
        sys.path.insert(0, str(folder))
    try:
        from run_models import label  # type: ignore
        return label
    except Exception:
        return None


def rate(k, n):
    return (k / n) if n else None


def num(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    df = df.copy()
    for c in cols:
        df[c] = pd.to_numeric(df.get(c), errors="coerce").fillna(0)
    return df


def load_scored(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    if "dataset" not in df:
        df["dataset"] = df["case_id"].str.split("__").str[0]
    if "variant" not in df:
        df["variant"] = df["case_id"].str.split("__").str[-1]
    for col in ("mechanism", "payload_style"):
        if col not in df:
            df[col] = ""
    count_cols = [f"{v}_{x}" for v in ("clean", "injected") for x in ("runs",) + LABELS]
    df = num(df, count_cols)
    at = df["mechanism"].map(attack_type)
    df["Attack type"] = at.str[0]
    df["_order"] = at.str[1]
    return df.sort_values("_order", kind="stable").reset_index(drop=True)


def distinct(df: pd.DataFrame, variant: str) -> pd.DataFrame:
    """One row per distinct prompt for that variant (clean or injected)."""
    d = df[df[f"{variant}_prompt_id"] != ""]
    return d.drop_duplicates(f"{variant}_prompt_id")


def summarize(df: pd.DataFrame) -> dict:
    cl, inj = distinct(df, "clean"), distinct(df, "injected")
    c_runs, i_runs = cl["clean_runs"].sum(), inj["injected_runs"].sum()
    return {
        "Clean prompts": len(cl),
        "Clean runs": int(c_runs),
        "Clean accuracy": rate(cl["clean_correct"].sum(), c_runs),
        "Clean no-answer": rate(cl["clean_no_answer"].sum(), c_runs),
        "Injected prompts": len(inj),
        "Injected runs": int(i_runs),
        "Attack success": rate(inj["injected_attacker"].sum(), i_runs),
        "Still correct": rate(inj["injected_correct"].sum(), i_runs),
        "Other wrong": rate(inj["injected_other"].sum() + inj["injected_ambiguous"].sum(), i_runs),
        "No answer": rate(inj["injected_no_answer"].sum(), i_runs),
    }


def describe(row, variant: str) -> str:
    runs = int(row[f"{variant}_runs"])
    if row[f"{variant}_prompt_id"] == "" or runs == 0:
        return ""
    parts = [f"{x.replace('_', '-')} {int(row[f'{variant}_{x}'])}/{runs}"
             for x in LABELS if row[f"{variant}_{x}"] > 0]
    return ", ".join(parts)


def build_tables(models: dict[str, pd.DataFrame]):
    overview, by_dataset, cases, variants, by_attack, attack_ds = [], [], [], [], [], []
    for model, df in models.items():
        overview.append({"Model": model, **summarize(df)})
        for ds, g in df.groupby("dataset", sort=False):
            by_dataset.append({"Model": model, "Dataset": ds, **summarize(g)})
        attacks = df[df["injected_prompt_id"] != ""]
        for (order, name), g in attacks.groupby(["_order", "Attack type"], sort=True):
            sm = summarize(g)
            by_attack.append({
                "Model": model, "Attack type": name, "Variants": ", ".join(dict.fromkeys(g["variant"])),
                "Cases": len(g), "Distinct prompts": sm["Injected prompts"], "Runs": sm["Injected runs"],
                "Attack success": sm["Attack success"], "Still correct": sm["Still correct"],
                "Other wrong": sm["Other wrong"], "No answer": sm["No answer"]})
            for ds, gd in g.groupby("dataset", sort=False):
                attack_ds.append({"Model": model, "Attack type": name, "Dataset": ds,
                                  "rate": summarize(gd)["Attack success"]})
        for _, r in df.iterrows():
            injected = r["injected_prompt_id"] != ""
            cases.append({
                "Model": model, "Case": r["case_id"], "Attack type": r["Attack type"], "Dataset": r["dataset"],
                "Mechanism": r["mechanism"], "Variant": r["variant"],
                "Payload style": r["payload_style"], "Question": r["question"],
                "Correct answer": r["correct_answer"], "Attacker answer": r["attacker_answer"],
                "Clean file result": describe(r, "clean"),
                "Injected file result": describe(r, "injected"),
                "Attack success": rate(r["injected_attacker"], r["injected_runs"]) if injected else None,
            })
        inj = df[df["injected_prompt_id"] != ""]
        if len(inj):
            m = inj.assign(rate=inj["injected_attacker"] / inj["injected_runs"].replace(0, pd.NA))
            pivot = m.pivot_table(index="variant", columns="dataset", values="rate", aggfunc="mean", sort=False)
            pivot = pivot.reset_index().rename(columns={"variant": "Variant"})
            vt = dict(zip(inj["variant"], inj["Attack type"]))
            pivot.insert(0, "Attack type", pivot["Variant"].map(vt))
            pivot.insert(0, "Model", model)
            variants.append(pivot)
    matrix = pd.DataFrame(attack_ds)
    if len(matrix):
        matrix = matrix.pivot_table(index=["Model", "Attack type"], columns="Dataset", values="rate",
                                    aggfunc="mean", sort=False).reset_index()
    return (pd.DataFrame(overview), pd.DataFrame(by_attack), matrix, pd.DataFrame(by_dataset),
            pd.DataFrame(cases), pd.concat(variants, ignore_index=True) if variants else pd.DataFrame())


def build_calls(name: str, df: pd.DataFrame, calls: list[dict], prompts: dict, label) -> list[dict]:
    """One row per call, labelled against the case(s) that use its prompt."""
    key, types = {}, {}
    for _, r in df.iterrows():
        for variant in ("clean", "injected"):
            pid = r[f"{variant}_prompt_id"]
            if pid and (pid not in key or (variant == "clean" and r["injected_file"] == "")):
                key[pid] = (variant, r["correct_answer"], r["attacker_answer"], r["case_id"])
            if pid and variant == "injected":
                types.setdefault(pid, {})[(r["_order"], r["Attack type"])] = None
    order_of = {pid: min(t)[0] for pid, t in types.items()}
    rows = []
    for c in calls:
        pid = c["prompt_id"]
        if pid not in key:
            continue
        variant, correct, attacker, case_id = key[pid]
        lab = ""
        if label:
            try:
                lab = label(c["reply"], correct, attacker)[0]
            except Exception:
                lab = ""
        usage = c.get("usage") or {}
        reply = c.get("reply") or ""
        rows.append({
            "Model": name, "File type": variant,
            "Attack type": " / ".join(n for _, n in sorted(types.get(pid, {}))) or "Control (clean)",
            "_order": order_of.get(pid, 0),
            "File(s)": ", ".join(prompts.get(pid, {}).get("files", [])), "Run": c["repeat"] + 1,
            "Correct answer": correct, "Attacker answer": attacker,
            "Final answer": c.get("final_answer"), "Label": lab,
            "Finish reason": c.get("finish_reason"),
            "Prompt tokens": usage.get("prompt_tokens"),
            "Completion tokens": usage.get("completion_tokens"),
            "Seconds": c.get("seconds"),
            "Reply": reply[:REPLY_LIMIT] + (" ...[truncated]" if len(reply) > REPLY_LIMIT else ""),
        })
    rows.sort(key=lambda x: (x["_order"], x["File(s)"], x["Run"]))
    for x in rows:
        del x["_order"]
    return rows


# ---- formatting ---------------------------------------------------------------

HEAD = PatternFill("solid", fgColor="1F4E78")
GOOD = PatternFill("solid", fgColor="E2F0D9")
BAD = PatternFill("solid", fgColor="F8CBAD")
MID = PatternFill("solid", fgColor="FFF2CC")
GOOD_WHEN_HIGH = {"Clean accuracy", "Still correct"}


def style_sheet(ws, df: pd.DataFrame, wide: tuple[str, ...] = (), pct: tuple[str, ...] = ()):
    for c in ws[1]:
        c.font = Font(name="Arial", bold=True, color="FFFFFF")
        c.fill = HEAD
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for i, col in enumerate(df.columns, 1):
        letter = get_column_letter(i)
        ws.column_dimensions[letter].width = 70 if col in wide else min(max(len(str(col)) + 4, 12), 34)
        for cell in ws[letter][1:]:
            cell.font = Font(name="Arial", size=10)
            cell.alignment = Alignment(vertical="top", wrap_text=col in wide)
            if col in pct and isinstance(cell.value, (int, float)):
                v = float(cell.value)
                cell.number_format = "0%"
                if col in GOOD_WHEN_HIGH:
                    cell.fill = GOOD if v >= 0.8 else BAD if v < 0.5 else MID
                else:  # attack success, wrong answers, no answers: high is bad
                    cell.fill = BAD if v >= 0.5 else GOOD if v == 0 else MID


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", type=Path, default=Path("results"))
    ap.add_argument("--out", type=Path, default=Path("report.xlsx"))
    args = ap.parse_args(argv)

    scored_files = sorted(args.results.glob("*.scored.csv"))
    if not scored_files:
        raise SystemExit(f"no *.scored.csv in {args.results}. Run run_models.py first.")
    prompts = {p["prompt_id"]: p for p in read_jsonl(args.results / "prompts.jsonl")}
    label = get_labeller()
    if label is None:
        print("note: could not import run_models.py; the Label column in Calls will be blank", file=sys.stderr)

    models, call_rows = {}, []
    for f in scored_files:
        name = f.name[: -len(".scored.csv")]
        models[name] = load_scored(f)
        call_rows += build_calls(name, models[name], read_jsonl(f.with_name(f"{name}.calls.jsonl")),
                                 prompts, label)

    overview, by_attack, attack_matrix, by_dataset, cases, variants = build_tables(models)
    calls = pd.DataFrame(call_rows)

    rates = ("Clean accuracy", "Clean no-answer", "Attack success", "Still correct", "Other wrong", "No answer")
    var_pct = tuple(c for c in variants.columns if c not in ("Model", "Attack type", "Variant")) if len(variants) else ()
    mx_pct = tuple(c for c in attack_matrix.columns if c not in ("Model", "Attack type")) if len(attack_matrix) else ()
    sheets = [("Overview", overview, (), rates),
              ("By attack type", by_attack, (), rates),
              ("Attack type x dataset", attack_matrix, (), mx_pct),
              ("By dataset", by_dataset, (), rates),
              ("By variant", variants, (), var_pct),
              ("Cases", cases, ("Question", "Clean file result", "Injected file result"), ("Attack success",)),
              ("Calls", calls, ("Reply",), ())]
    with pd.ExcelWriter(args.out, engine="openpyxl") as xw:
        for title, df, wide, pct in sheets:
            if df.empty:
                continue
            df.to_excel(xw, sheet_name=title, index=False)
            style_sheet(xw.sheets[title], df, wide, pct)

    with pd.option_context("display.width", 200, "display.max_columns", 20):
        show = overview.copy()
        for c in show.columns:
            if show[c].dtype == float:
                show[c] = show[c].map(lambda v: "-" if pd.isna(v) else f"{v:.0%}")
        print(show.to_string(index=False))
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()