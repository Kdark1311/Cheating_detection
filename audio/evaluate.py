"""Compare events.csv with hand labels (CSV columns: start,end,label).

Usage: uv run python evaluate.py outputs/session/events.csv data/labels.csv
Labels: `silence` and `candidate` must not raise anything; any other label
(other, alternating, overlap, ...) must be caught by a flag or review event.
"""
import csv
import sys

SHORT_S = 2.0
SAFE_LABELS = {"silence", "candidate"}


def read(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["start"], row["end"] = float(row["start"]), float(row["end"])
    return rows


def shared(a, b):
    return max(0.0, min(a["end"], b["end"]) - max(a["start"], b["start"]))


def score(events, labels):
    raised = [e for e in events if e["decision"] != "ignore"]
    safe = [x for x in labels if x["label"] in SAFE_LABELS]
    risky = [x for x in labels if x["label"] not in SAFE_LABELS]
    short = [x for x in risky if x["end"] - x["start"] < SHORT_S]

    def caught(items, decisions):
        hits = sum(any(shared(x, e) > 0 for e in raised if e["decision"] in decisions) for x in items)
        return f"{hits}/{len(items)}"

    safe_s = sum(x["end"] - x["start"] for x in safe)
    false_s = sum(shared(x, e) for x in safe for e in raised)
    return {
        "correctly_skipped": 1 - false_s / safe_s if safe_s else None,
        "caught_flag": caught(risky, {"flag"}),
        "caught_flag_or_review": caught(risky, {"flag", "review"}),
        "caught_short": caught(short, {"flag", "review"}),
        "review_events": sum(e["decision"] == "review" for e in events),
        "review_s": sum(e["end"] - e["start"] for e in events if e["decision"] == "review"),
    }


if __name__ == "__main__":
    for name, value in score(read(sys.argv[1]), read(sys.argv[2])).items():
        print(f"{name}: {value}")
