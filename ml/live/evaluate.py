"""Grade immutable forecasts against observed result revisions, never backdate."""
import json
import math
from collections import Counter
from datetime import datetime, timezone

from ml.live.ledger import DIRECTORY, latest_observations, read_kind, write_once
from ml.live.normalize import moment, sha, stamp
from ml.pipeline import ROOT, write_json


def grade(prediction, observation, asof):
    if observation and moment(observation["first_seen_at"]) > moment(asof):
        observation = None
    value = {"prediction_id": prediction["snapshot_id"], "fixture_id": prediction["fixture_id"], "stage": prediction.get("stage", "initial"), "grade": "pending", "outcome": None, "log_loss": None, "brier": None, "outcome_version": observation["observation_id"] if observation else "unavailable"}
    if observation:
        if observation["occurrence_id"] != prediction["occurrence_id"] or observation["status"] in {"postponed", "cancelled", "awarded", "walkover", "abandoned"}:
            value["grade"] = "void"
        elif observation["status"] in {"finished", "finished_extra_time", "finished_penalties"} and observation["score_90"] is not None and not observation["quarantine_reasons"] and moment(observation["kickoff_utc"]) < moment(observation["first_seen_at"]):
            if moment(prediction["generated_at"]) >= moment(observation["kickoff_utc"]):
                raise ValueError("cannot_grade_backdated_or_late_prediction")
            h, a = observation["score_90"]
            y = 0 if h > a else 1 if h == a else 2
            p = prediction["probabilities"]
            if len(p) != 3 or any(not math.isfinite(v) or not 0 <= v <= 1 for v in p) or abs(sum(p)-1) > 1e-6:
                raise ValueError("invalid_prediction_probabilities")
            choice = max(range(3), key=lambda i: p[i])
            value.update({"grade": "win" if choice == y else "loss", "outcome": y, "log_loss": -math.log(max(1e-15, p[y])), "brier": sum((v-int(i == y))**2 for i, v in enumerate(p))})
    value["id"] = sha(value)
    return value


def evaluate(directory=DIRECTORY, asof=None):
    now = stamp(asof or datetime.now(timezone.utc).isoformat())
    observations = {r["fixture_id"]: r for r in latest_observations(read_kind(directory, "observations"), now)}
    predictions = [p for p in read_kind(directory, "predictions") if moment(p["generated_at"]) <= moment(now)]
    grades = [grade(p, observations.get(p["fixture_id"]), now) for p in predictions]
    for result in grades:
        write_once(directory, "evaluations", result)
    primary = {}
    for p in sorted(predictions, key=lambda p: p["generated_at"]):
        if p.get("stage", "initial") == "initial":
            primary.setdefault((p["fixture_id"], p["occurrence_id"]), p["snapshot_id"])
    selected = [g for g in grades if g["prediction_id"] in primary.values() and g["grade"] in {"win", "loss"}]
    from ml.selective import wilson_interval
    by_id = {p["snapshot_id"]: p for p in predictions}
    chosen = [g for g in selected if by_id[g["prediction_id"]].get("research_eligible") is True]
    def metrics(values):
        n = len(values)
        correct = sum(g["grade"] == "win" for g in values)
        result = {"n": n, "correct": correct, "accuracy": correct/n if n else None, "log_loss": sum(g["log_loss"] for g in values)/n if n else None, "brier": sum(g["brier"] for g in values)/n if n else None, "wilson95": wilson_interval(correct, n) if n else None, "ece": None, "calibration_bins": []}
        if n:
            from ml.evaluate import metric_values
            probabilities = [by_id[g["prediction_id"]]["probabilities"] for g in values]
            measured = metric_values([g["outcome"] for g in values], probabilities)[0]
            result.update({k: measured[k] for k in ["ece", "calibration_bins", "reliability"]})
        return result
    external = []
    for value in read_kind(directory, "enrichments"):
        if value["route"] != "/predictions" or not value.get("probabilities") or moment(value["available_at"]) > moment(now):
            continue
        known = next((o for o in latest_observations(read_kind(directory, "observations"), value["available_at"]) if o["fixture_id"] == value["fixture_id"]), None)
        if known is None or moment(value["available_at"]) >= moment(known["kickoff_utc"]):
            continue
        forecast = {"snapshot_id": "external-"+value["id"], "fixture_id": value["fixture_id"], "occurrence_id": known["occurrence_id"], "generated_at": value["available_at"], "probabilities": value["probabilities"]}
        by_id[forecast["snapshot_id"]] = forecast
        external.append(grade(forecast, observations.get(value["fixture_id"]), now))
    summary = {"evaluated_at": now, "counts_all_snapshots": dict(Counter(g["grade"] for g in grades)), "primary_stage": "initial, first per fixture occurrence", "settled_primary_n": len(selected), "accuracy": sum(g["grade"] == "win" for g in selected)/len(selected) if selected else None, "log_loss": sum(g["log_loss"] for g in selected)/len(selected) if selected else None, "brier": sum(g["brier"] for g in selected)/len(selected) if selected else None, "prospective_certified": False, "model_promoted": False, "note": "Pending/void are excluded from accuracy. Corrections create new outcome versions and preserve original forecasts."}
    summary["all_primary"] = metrics(selected)
    summary["selected_primary"] = metrics(chosen)
    summary["selected_primary"]["coverage_of_settled_primary"] = len(chosen)/len(selected) if selected else None
    summary["external_provider_forecasts"] = {"records": len(external), "pending": sum(g["grade"] == "pending" for g in external), "settled": metrics([g for g in external if g["grade"] in {"win", "loss"}])}
    summary["per_league_selected"] = {code: metrics([g for g in chosen if by_id[g["prediction_id"]].get("league") == code]) for code in sorted({p.get("league", "unknown") for p in predictions})}
    write_json(ROOT/"reports/live-research/prospective-evaluation.json", summary)
    print(json.dumps(summary))
    return summary


if __name__ == "__main__":
    evaluate()
