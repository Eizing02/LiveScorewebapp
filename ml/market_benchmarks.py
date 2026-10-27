"""Extra exploratory diagnostics: compare goal markets with prior league rates."""
import json
from collections import defaultdict, deque
from itertools import groupby

from ml.expanded import CONFIG, OUTPUT
from ml.goal_markets import goal_markets
from ml.pipeline import ROOT, write_json
from ml.recent_evaluate import binary_metrics


def targets(h, a):
    return {**{f"{side}_{line}": int(h+a > line) if side == "over" else int(h+a < line) for line in [1.5, 2.5, 3.5] for side in ["over", "under"]}, "btts_yes": int(h > 0 and a > 0), "btts_no": int(h == 0 or a == 0)}


def main():
    rows = [json.loads(line) for line in (OUTPUT / "accepted.jsonl").read_text(encoding="utf-8").splitlines()]
    windows = defaultdict(lambda: deque(maxlen=380))
    counts = defaultdict(int)
    prior = goal_markets(1.5, 1.2)
    predictions = []
    start, end = CONFIG["retrospective_test"]
    for day, batch in groupby(rows, key=lambda r: r["date"]):
        matches = list(batch)
        for row in matches:
            history = windows[row["league"]]
            if start <= day < end and counts[row["league"]] >= 40:
                p = {name: (sum(result[name] for result in history)+30*prior[name])/(len(history)+30) for name in prior}
                predictions.append({"league": row["league"], "date": day, "p": p, "y": targets(*row["goals"])})
        # Nothing on this date can use another same-date result.
        for row in matches:
            windows[row["league"]].append(targets(*row["goals"]))
            counts[row["league"]] += 1
    metrics = {}
    for name in prior:
        metrics[name] = {}
        for league in ["all", *CONFIG["leagues"]]:
            subset = [r for r in predictions if league == "all" or r["league"] == league]
            if subset:
                metrics[name][league] = binary_metrics([r["y"][name] for r in subset], [r["p"][name] for r in subset], [r["date"] for r in subset])
    report = {"status": "additional_exploratory_diagnostic_not_model_selection", "period": [start, end], "n": len(predictions), "method": "Previous 380 league outcomes plus 30 prior pseudo-games; strict whole-date updates, no test-label fitted probabilities", "metrics": metrics, "purpose": "High binary accuracy can come from the base event frequency; compare log loss and Brier with this simple prior before claiming improvement."}
    write_json(ROOT / "reports/recent-v2/market-baseline-diagnostics.json", report)
    print(json.dumps({name: {key: group["all"][key] for key in ["log_loss", "brier", "accuracy"]} for name, group in metrics.items()}))


if __name__ == "__main__":
    main()
