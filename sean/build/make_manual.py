"""Materials for trying the cases by hand in web chat UIs (ChatGPT, Gemini, DeepSeek ...).

    python build/make_manual.py

Writes manual/:
  prompts/<trial>.txt   paste mode: the exact text run_models.py sends (system text + user text, one block)
  upload/<trial>/<neutral name>.xlsx + question.txt
                        upload mode: byte copies of the data files under a neutral file name
                        (the real names say "injected", "instruction" ...), plus the text to type
  trials.csv            every trial with its expected correct / attacker answer
  manual_log.csv        empty log to fill in (one row per trial x platform)
Score the log afterwards with  python build/manual_score.py
"""

from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from run_models import plan  # noqa: E402

OUT = ROOT / "manual"
NEUTRAL = {"S1": "income_tax_2025.xlsx", "S2": "fy2025_consolidation.xlsx", "S3": "auto_loan.xlsx",
           "S4": "q3_commissions.xlsx", "S5": "budget_vs_actual_2025.xlsx", "S6": "capital_projects.xlsx"}
STYLE = {"instruction": "instr", "spoofed_data": "spoof"}
SUFFIX = "End your reply with a line of the form 'Final answer: <your answer>'."
# trials in the recommended first pass (paste mode): clean + both styles in cell P, per scenario
CORE = {"clean", "cellP_instr", "cellP_spoof"}


def where(c):
    if c["mechanism"] == "contextual":
        return "note"
    if c["structural_kind"] == "hidden_sheet":
        return "hiddensheet"
    return "cellP"


def upload_kind(c):
    if c["mechanism"] == "contextual":
        return "note_formula" if c["payload_source"] == "formula" else "note_typed"
    return c["structural_kind"] or c["mechanism"]


def main():
    cases, prompts = plan(ROOT / "cases.csv")
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "prompts").mkdir(parents=True)
    trials = []

    def add(trial, mode, c, variant, file_rel, what):
        trials.append({"trial": trial, "mode": mode, "scenario": c["scenario"], "variant": variant, "what": what,
                       "core": "yes" if trial.split("_", 1)[1] in CORE and mode == "paste" else "",
                       "source_file": file_rel, "question": c["question"],
                       "correct_answer": c["correct_answer"],
                       "attacker_answer": c["attacker_answer"] if variant == "injected" else ""})

    # paste mode: one trial per distinct prompt
    done = set()
    for c in sorted(cases, key=lambda c: c["case_id"]):
        if c["helpers"] != "visible":
            continue  # helpers=hidden gives identical text
        for variant in ("clean", "injected"):
            pid = c[f"{variant}_prompt_id"]
            if pid in done:
                continue
            done.add(pid)
            tag = "clean" if variant == "clean" else f"{where(c)}_{STYLE[c['payload_style']]}"
            trial = f"{c['scenario']}_{tag}"
            msgs = prompts[pid]["messages"]
            # pandas on Windows writes \r\n between CSV rows; plain \n here (a chat box normalises line breaks anyway)
            text = (msgs[0]["content"] + "\n\n" + msgs[1]["content"] + "\n").replace("\r\n", "\n")
            with open(OUT / "prompts" / f"{trial}.txt", "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            add(trial, "paste", c, variant, c[f"{variant}_file"],
                "clean file" if variant == "clean" else f"{where(c)}, {c['payload_style']}")

    # upload mode: every mechanism is its own trial (the UI's file reader decides what the model sees)
    seen = set()
    for c in sorted(cases, key=lambda c: c["case_id"]):
        if c["helpers"] != "visible":
            continue
        items = [("clean", c["clean_file"], "clean")]
        items.append(("injected", c["injected_file"], f"{upload_kind(c)}_{STYLE[c['payload_style']]}"))
        for variant, rel, tag in items:
            trial = f"{c['scenario']}_up_{tag}"
            if trial in seen:
                continue
            seen.add(trial)
            d = OUT / "upload" / trial
            d.mkdir(parents=True)
            shutil.copyfile(ROOT / rel, d / NEUTRAL[c["scenario"]])  # byte copy keeps cached values
            (d / "question.txt").write_text(c["question"].strip() + "\n\n" + SUFFIX + "\n", encoding="utf-8")
            add(trial, "upload", c, variant, rel, "clean file" if variant == "clean" else
                f"{c['mechanism']}/{c['structural_kind'] or '-'}/{c['payload_source']}, {c['payload_style']}")

    trials.sort(key=lambda t: (t["mode"] != "paste", t["scenario"], t["variant"] != "clean", t["trial"]))
    with open(OUT / "trials.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(trials[0]))
        w.writeheader()
        w.writerows(trials)

    log_cols = ["trial", "platform", "model_shown", "date", "run", "final_answer", "mentions_payload",
                "flags_suspicious", "file_read_ok", "notes", "chat_link"]
    with open(OUT / "manual_log.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(log_cols)
        for t in trials:
            if t["core"]:
                for p in ("ChatGPT", "Gemini", "DeepSeek"):
                    w.writerow([t["trial"], p] + [""] * (len(log_cols) - 2))

    n_paste = sum(t["mode"] == "paste" for t in trials)
    print(f"paste trials: {n_paste}, upload trials: {len(trials) - n_paste}, core: {sum(bool(t['core']) for t in trials)}")


if __name__ == "__main__":
    main()
