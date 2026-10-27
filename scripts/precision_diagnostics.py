"""Report every selected mistake and selection capacity; do not change the policy."""
import json
from collections import Counter

from ml.pipeline import ROOT, write_json


def build_diagnostics():
    pointer = json.loads((ROOT/"reports/precision-v3/latest.json").read_text(encoding="utf-8"))
    directory = (ROOT/pointer["report"]).parent
    rows = [json.loads(line) for line in (directory/"retrospective_test-predictions.jsonl").read_text(encoding="utf-8").splitlines()]
    selected = []
    for row in rows:
        if row["selected"]:
            prediction = max(range(3), key=lambda index: row["probabilities"][index])
            selected.append({**row, "choice": prediction, "probability": row["probabilities"][prediction], "correct": prediction == row["target"]})
    failures = [r for r in selected if not r["correct"]]
    dates = Counter(r["date"] for r in selected)
    return {"selected_decisions": selected, "mistakes": failures, "mistake_outcomes": dict(Counter(["home","draw","away"][r["target"]] for r in failures)), "predicted_outcomes": dict(Counter(["home","draw","away"][r["choice"]] for r in selected)), "capacity": {"selected_matches": len(selected), "calendar_dates_with_any_pick": len(dates), "calendar_dates_with_at_least3": sum(n >= 3 for n in dates.values()), "calendar_dates_with_at_least5": sum(n >= 5 for n in dates.values()), "maximum_on_calendar_date": max(dates.values(), default=0), "matches_per_365days": len(selected)/365, "warning": "Calendar-date grouping is a capacity diagnostic, not verified 06:00 Bangkok report backtesting; source kickoff times remain unverified."}, "interpretation": "All failed picks retained. Causes such as injuries/red cards are unknown and are not invented. The rule/model remains unchanged after test."}


def main():
    pointer = json.loads((ROOT/"reports/precision-v3/latest.json").read_text(encoding="utf-8"))
    destination = (ROOT/pointer["report"]).parent/"error-and-capacity-analysis.json"
    result = build_diagnostics()
    write_json(destination, result)
    print(json.dumps({"mistakes": len(result["mistakes"]), "outcomes": result["mistake_outcomes"], "capacity": result["capacity"]}))


if __name__ == "__main__":
    main()
