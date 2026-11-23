"""Score manual/manual_log.csv with the team's label() (same rules as run_models.py).

    python build/manual_score.py

Reads the final_answer column (paste just the answer, or the whole 'Final answer: ...' line),
writes manual/manual_scored.csv and prints counts per platform.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from run_models import label  # noqa: E402

M = ROOT / "manual"


def main():
    trials = {t["trial"]: t for t in csv.DictReader(open(M / "trials.csv", encoding="utf-8-sig"))}
    rows = [r for r in csv.DictReader(open(M / "manual_log.csv", encoding="utf-8-sig")) if r["final_answer"].strip()]
    counts = Counter()
    for r in rows:
        t = trials[r["trial"]]
        ans = r["final_answer"].strip()
        reply = ans if ans.lower().startswith("final answer") else f"Final answer: {ans}"
        r["label"], _ = label(reply, t["correct_answer"], t["attacker_answer"])
        r.update({k: t[k] for k in ("mode", "scenario", "variant", "what", "correct_answer", "attacker_answer")})
        counts[(r["platform"], r["mode"], t["variant"], r["label"])] += 1
    if not rows:
        print("no filled-in rows yet")
        return
    with open(M / "manual_scored.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for key in sorted(counts):
        print(" / ".join(key), counts[key])


if __name__ == "__main__":
    main()
