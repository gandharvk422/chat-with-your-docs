"""
Compare an experiment's results with the baseline, question by question.

Put this file in:  backend/evals/compare.py
Run from backend/: python .\\evals\\compare.py <experiment_name>

Example:  python .\\evals\\compare.py k10_n6
          (reads evals/results_baseline.json and evals/results_k10_n6.json)
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
REFUSAL = "have enough information"  # same phrase run_evals.py uses


def load(name):
    path = HERE / f"results_{name}.json"
    if not path.exists():
        sys.exit(f"File not found: {path}")
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {r["id"]: r for r in rows}


def status(r):
    """answered / refused / error"""
    if r["answer"].startswith("ERROR"):
        return "error"
    return "refused" if REFUSAL in r["answer"].lower() else "answered"


def is_correct(r):
    """Did the bot do the right thing? None if the call failed."""
    s = status(r)
    if s == "error":
        return None
    should_refuse = r["type"] == "unanswerable"
    return (s == "refused") == should_refuse


def avg_chars(rows):
    rows = list(rows)
    if not rows:
        return 0
    return sum(sum(len(c) for c in r["contexts"]) for r in rows) / len(rows)


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python .\\evals\\compare.py <experiment_name>")

    base = load("baseline")
    exp = load(sys.argv[1])
    better = worse = 0

    print(f"{'id':5}{'type':14}{'baseline':10}{'experiment':12}verdict")
    for qid, r in exp.items():
        if qid not in base:
            print(f"{qid:5}(not in baseline, skipped)")
            continue
        b = base[qid]
        cb, ce = is_correct(b), is_correct(r)
        if cb is None or ce is None:
            verdict = "ERROR - ignore"
        elif cb == ce:
            verdict = ""
        elif ce:
            verdict = "BETTER"
            better += 1
        else:
            verdict = "WORSE"
            worse += 1
        print(f"{qid:5}{r['type']:14}{status(b):10}{status(r):12}{verdict}")

    print(f"\nbetter: {better}   worse: {worse}")
    shared = [q for q in exp if q in base]
    print(
        f"avg context chars  baseline: {avg_chars(base[q] for q in shared):.0f}"
        f"   experiment: {avg_chars(exp[q] for q in shared):.0f}"
    )


if __name__ == "__main__":
    main()