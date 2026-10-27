"""Selective prediction research, isolated from the application and model registry."""
import csv
import json
from collections import defaultdict, deque
from datetime import date, datetime, timedelta, timezone
from itertools import groupby
from pathlib import Path

import numpy as np
from scipy.optimize import minimize_scalar

from ml.evaluate import cluster_ci, metric_values, predict, train_challengers
from ml.models import PARAMS, replay
from ml.pipeline import POLICY, ROOT, digest, load_accepted, write_json, write_jsonl

FILTER_POLICY = json.loads((ROOT / "ml/config/selection_policy_v1.json").read_text(encoding="utf-8"))


def temperature_probabilities(probabilities, temperature):
    p = np.asarray(probabilities, dtype=float)
    if not 0.5 <= temperature <= 3 or p.ndim != 2 or p.shape[1] != 3:
        raise ValueError("invalid_calibration_input")
    logits = np.log(np.clip(p, 1e-15, 1)) / temperature
    exp = np.exp(logits - logits.max(axis=1, keepdims=True))
    return exp / exp.sum(axis=1, keepdims=True)


def fit_temperature(previous_probabilities, previous_targets):
    y = np.asarray(previous_targets)
    bounds = FILTER_POLICY["calibration"]["temperature_bounds"]
    def objective(t):
        return -np.log(temperature_probabilities(previous_probabilities, t)[np.arange(len(y)), y]).mean()
    result = minimize_scalar(objective, bounds=bounds, method="bounded", options={"xatol": 1e-8})
    if not result.success:
        raise ValueError("calibration_failed")
    return float(result.x)


def prior_context(matches):
    """Only previous dates enter the counts; target-match results are never inspected."""
    recent = defaultdict(deque)
    seasons = defaultdict(int)
    last = {}
    context = {}
    ordered = sorted(matches, key=lambda m: (m["date"], m["id"]))
    for day, items in groupby(ordered, key=lambda m: m["date"]):
        batch = list(items)
        cutoff = (date.fromisoformat(day) - timedelta(days=365)).isoformat()
        for match in batch:
            info = []
            for team in [match["home_id"], match["away_id"]]:
                key = (match["league"], team)
                while recent[key] and recent[key][0] < cutoff:
                    recent[key].popleft()
                gap = (date.fromisoformat(day) - date.fromisoformat(last[key])).days if key in last else None
                info.append({"season_matches": seasons[(match["league"], match["season"], team)], "last365_matches": len(recent[key]), "last_known_league_result_gap_days": gap})
            context[match["id"]] = {"home": info[0], "away": info[1]}
        for match in batch:
            for team in [match["home_id"], match["away_id"]]:
                key = (match["league"], team)
                recent[key].append(day)
                last[key] = day
                seasons[(match["league"], match["season"], team)] += 1
    return context


def history_reasons(row, context):
    policy = FILTER_POLICY["history"]
    reasons = []
    if len(row.get("features", [])) != 11 or not np.all(np.isfinite(row["features"])) or not all(side in context for side in ["home", "away"]):
        return ["incomplete_or_invalid_history_context"]
    if min(row["features"][7:9]) < policy["min_venue_matches_each_team"]:
        reasons.append("insufficient_home_away_history")
    for side in ["home", "away"]:
        value = context[side]
        if value["season_matches"] < policy["min_current_season_matches_each_team"]:
            reasons.append(side + "_early_season")
        if value["last365_matches"] < policy["min_league_matches_in_last_365_days_each_team"]:
            reasons.append(side + "_sparse_recent_league_history")
        gap = value["last_known_league_result_gap_days"]
        if gap is None or gap > policy["max_days_since_last_known_league_result"]:
            reasons.append(side + "_stale_league_history")
    return reasons


def stress_predictions(model, rows, temperature):
    x = np.array([r["features"] for r in rows], dtype=float)
    scenarios = []
    shift = FILTER_POLICY["stress"]["elo_difference_shift_points"]
    relative = FILTER_POLICY["stress"]["strength_relative_shift"]
    for sign in [-1, 1]:
        changed = x.copy()
        changed[:, 0] += sign * shift
        scenarios.append(temperature_probabilities(model.predict_proba(changed), temperature))
        changed = x.copy()
        changed[:, [1, 4]] *= 1 + sign * relative
        changed[:, [2, 3]] *= 1 - sign * relative
        scenarios.append(temperature_probabilities(model.predict_proba(changed), temperature))
    return np.stack(scenarios, axis=1)


def select_one(probabilities, model_probabilities, history_failures, stress, layer, threshold):
    """Inputs deliberately contain no target label, score, or post-match event."""
    probabilities = np.asarray(probabilities, dtype=float)
    if probabilities.shape != (3,) or not np.all(np.isfinite(probabilities)) or np.any(probabilities < 0) or abs(probabilities.sum() - 1) > 1e-6:
        return {"selected": False, "choice": None, "reasons": ["invalid_probabilities"]}
    if layer not in FILTER_POLICY["candidate_search"]["layers"] or not 0 <= threshold <= 1:
        raise ValueError("unknown_filter_configuration")
    chosen = int(np.argmax(probabilities))
    reasons = []
    if float(probabilities[chosen]) < threshold:
        reasons.append("probability_below_threshold")
    if layer in {"history", "consensus", "robust"}:
        reasons.extend(history_failures)
    if layer in {"consensus", "robust"}:
        for name in FILTER_POLICY["candidate_search"]["consensus_models"]:
            model_p = np.asarray(model_probabilities.get(name, []), dtype=float)
            if model_p.shape != (3,) or not np.all(np.isfinite(model_p)) or np.any(model_p < 0) or abs(model_p.sum() - 1) > 1e-6:
                reasons.append(name + "_missing_or_invalid")
            elif int(np.argmax(model_p)) != chosen:
                reasons.append(name + "_disagrees")
    if layer == "robust":
        stress = np.asarray(stress, dtype=float)
        if stress.shape != (4, 3) or not np.all(np.isfinite(stress)) or np.any(stress < 0) or not np.allclose(stress.sum(axis=1), 1):
            return {"selected": False, "choice": chosen, "reasons": reasons + ["invalid_stress_scenarios"]}
        if any(int(np.argmax(p)) != chosen for p in stress):
            reasons.append("stress_changes_top_outcome")
        if min(float(p[chosen]) for p in stress) < FILTER_POLICY["stress"]["minimum_selected_class_probability"]:
            reasons.append("stress_support_too_low")
    return {"selected": not reasons, "choice": chosen, "reasons": reasons}


def select_mask(rows, predictions, calibrated, stress, contexts, layer, threshold):
    decisions = []
    for i, row in enumerate(rows):
        decisions.append(select_one(calibrated[i], {name: p[i] for name, p in predictions.items()}, history_reasons(row, contexts[row["id"]]), stress[i], layer, threshold))
    return np.array([d["selected"] for d in decisions]), decisions


def wilson_interval(correct, n):
    if not n:
        return None
    z = 1.959963984540054
    p = correct / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return [float(centre - half), float(centre + half)]


def selected_summary(rows, probabilities, mask):
    selected = [r for r, yes in zip(rows, mask) if yes]
    if not selected:
        return {"n": 0, "total": len(rows), "coverage": 0, "accuracy": None, "wilson95": None, "date_cluster95": None}
    p = probabilities[mask]
    y = [r["target"] for r in selected]
    metrics, values = metric_values(y, p)
    ci = cluster_ci(values, [r["date"] for r in selected])
    return {"n": len(selected), "total": len(rows), "coverage": len(selected) / len(rows), "correct": int((p.argmax(axis=1) == y).sum()), "accuracy": metrics["accuracy"], "mean_probability": float(p.max(axis=1).mean()), "absolute_calibration_gap": abs(float(p.max(axis=1).mean()) - metrics["accuracy"]), "log_loss": metrics["log_loss"], "brier": metrics["brier"], "ece": metrics["ece"], "wilson95": wilson_interval(int((p.argmax(axis=1) == y).sum()), len(selected)), "date_cluster95": ci[2], "per_league": {league: {"n": sum(r["league"] == league for r in selected), "correct": sum(r["league"] == league and int(p[i].argmax()) == r["target"] for i, r in enumerate(selected))} for league in POLICY["leagues"]}}


def qualification(summary, folds):
    policy = FILTER_POLICY["qualification"]
    reasons = []
    checks = {
        "too_few_validation_samples": summary["n"] >= policy["min_validation_selected"],
        "coverage_too_low": summary["coverage"] >= policy["min_validation_coverage"],
        "accuracy_below_target": (summary["accuracy"] or 0) >= policy["min_validation_accuracy"],
        "wilson_lower_bound_too_low": summary["wilson95"] is not None and summary["wilson95"][0] >= policy["min_wilson95_lower"],
        "date_cluster_lower_bound_too_low": summary["date_cluster95"] is not None and summary["date_cluster95"][0] >= policy["min_date_cluster95_lower"],
        "calibration_gap_too_large": summary.get("absolute_calibration_gap", 1) <= policy["max_abs_confidence_hit_rate_gap"],
        "league_support_too_small": all(v["n"] >= policy["min_each_league_selected"] for v in summary.get("per_league", {}).values()) and bool(summary.get("per_league")),
        "fold_support_too_small": all(f["n"] >= policy["min_each_fold_selected"] for f in folds),
        "unstable_fold_accuracy": all((f["accuracy"] or 0) >= policy["min_each_fold_accuracy"] for f in folds),
    }
    reasons.extend(name for name, passed in checks.items() if not passed)
    return reasons


def live_rejection_reasons(evidence, now=None):
    """Fail closed on missing evidence. Research source acceptance is insufficient for live publication."""
    now = now or datetime.now(timezone.utc)
    reasons = []
    for field in ["kickoff_verified", "team_mapping_verified", "provider_coverage_verified", "feature_cutoff_verified", "model_approved"]:
        if evidence.get(field) is not True:
            reasons.append(field + "_missing_or_false")
    if evidence.get("is_mock") is not False:
        reasons.append("mock_or_unknown_source")
    if evidence.get("fixture_status") != "scheduled":
        reasons.append("fixture_not_scheduled")
    for field, max_hours in [("fixture_feed_fetched_at", 6), ("results_feed_fetched_at", 24)]:
        try:
            stamp = datetime.fromisoformat(evidence[field].replace("Z", "+00:00"))
            age = (now - stamp).total_seconds()
            if age < -60 or age > max_hours * 3600:
                reasons.append(field + "_stale_or_future")
        except (KeyError, ValueError, TypeError):
            reasons.append(field + "_unverified")
    try:
        kickoff = datetime.fromisoformat(evidence["kickoff_utc"].replace("Z", "+00:00"))
        cutoff = datetime.fromisoformat(evidence["information_cutoff_utc"].replace("Z", "+00:00"))
        if kickoff <= now or cutoff >= kickoff or cutoff > now:
            reasons.append("live_cutoff_violation")
    except (KeyError, ValueError, TypeError):
        reasons.append("live_timestamps_unverified")
    return reasons


def run(output=ROOT / "reports/selection-v1"):
    output = Path(output)
    if (output / "new-test.json").exists():
        raise FileExistsError("Research test already evaluated in this directory; do not silently overwrite or retune.")
    output.mkdir(parents=True, exist_ok=True)
    accepted = load_accepted()
    if digest(accepted) != FILTER_POLICY["dataset_version"] or POLICY["source_commit"] != FILTER_POLICY["source_commit"]:
        raise ValueError("source_or_dataset_mismatch")
    rows, _ = replay(accepted)
    rows = [r for r in rows if r["history_matches"] >= PARAMS["min_history_matches"]]
    contexts = prior_context(accepted)
    write_json(output / "frozen-policy.json", FILTER_POLICY)
    cache = {}

    def period(start, end):
        if start in cache:
            return cache[start]
        train = [r for r in rows if r["date"] < start]
        testing = [r for r in rows if start <= r["date"] < end]
        models = train_challengers(train)
        preds = predict(testing, models)
        cache[start] = {"rows": testing, "models": models, "predictions": preds, "training_last_date": max(r["date"] for r in train), "training_n": len(train)}
        return cache[start]

    validation = []
    for start, end in FILTER_POLICY["validation_periods"]:
        year = int(start[:4])
        prior = period(f"{year - 1}-07-01", start)
        current = period(start, end)
        temperature = fit_temperature(prior["predictions"]["logistic"], [r["target"] for r in prior["rows"]])
        calibrated = temperature_probabilities(current["predictions"]["logistic"], temperature)
        stress = stress_predictions(current["models"]["logistic"], current["rows"], temperature)
        validation.append({"start": start, "end": end, **current, "temperature": temperature, "calibrated": calibrated, "stress": stress, "calibration_start": f"{year - 1}-07-01"})
    candidates = []
    pooled_rows = [r for f in validation for r in f["rows"]]
    pooled_calibrated = np.concatenate([f["calibrated"] for f in validation])
    for layer in FILTER_POLICY["candidate_search"]["layers"]:
        for threshold in FILTER_POLICY["candidate_search"]["thresholds"]:
            masks, fold_metrics = [], []
            for fold in validation:
                mask, _ = select_mask(fold["rows"], fold["predictions"], fold["calibrated"], fold["stress"], contexts, layer, threshold)
                masks.append(mask)
                fold_metrics.append(selected_summary(fold["rows"], fold["calibrated"], mask))
            summary = selected_summary(pooled_rows, pooled_calibrated, np.concatenate(masks))
            failed = qualification(summary, fold_metrics)
            candidates.append({"id": f"{layer}-p{int(threshold * 100)}", "layer": layer, "threshold": threshold, "summary": summary, "folds": fold_metrics, "qualification_failures": failed, "qualified": not failed})
    qualified = sorted([c for c in candidates if c["qualified"]], key=lambda c: (-c["summary"]["coverage"], -c["summary"]["date_cluster95"][0], c["id"]))
    chosen = qualified[0] if qualified else None
    import hashlib
    selection = {"policy_sha256": digest(FILTER_POLICY), "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "chosen_rule": {k: chosen[k] for k in ["id", "layer", "threshold"]} if chosen else None, "status": "validation_qualified_pending_new_test" if chosen else "insufficient_validation_evidence", "candidates": candidates, "validation_temperatures": [{"period": [f["start"], f["end"]], "temperature": f["temperature"], "calibration_period_start": f["calibration_start"]} for f in validation], "auto_promoted": False}
    write_json(output / "selection-before-test.json", selection)
    selection_hash = digest(selection)
    # New-test predictions are computed only after the selection file has been written.
    start, end = FILTER_POLICY["new_test_period"]
    prior = period("2024-07-01", "2025-07-01")
    temperature = fit_temperature(prior["predictions"]["logistic"], [r["target"] for r in prior["rows"]])
    current = period(start, end)
    calibrated = temperature_probabilities(current["predictions"]["logistic"], temperature)
    stress = stress_predictions(current["models"]["logistic"], current["rows"], temperature)
    p = current["predictions"]["logistic"]
    controls = {
        "all_raw": selected_summary(current["rows"], p, np.ones(len(p), dtype=bool)),
        "p75_raw": selected_summary(current["rows"], p, p.max(axis=1) >= 0.75),
        "p75_calibrated": selected_summary(current["rows"], calibrated, calibrated.max(axis=1) >= 0.75),
    }
    new_result = None
    decisions = []
    if chosen:
        mask, decisions = select_mask(current["rows"], current["predictions"], calibrated, stress, contexts, chosen["layer"], chosen["threshold"])
        new_result = selected_summary(current["rows"], calibrated, mask)
        limits = FILTER_POLICY["confirmation"]
        new_result["confirmation_passed"] = bool(new_result["n"] >= limits["min_test_selected"] and all(v["n"] >= limits["min_test_each_league_selected"] for v in new_result.get("per_league", {}).values()) and (new_result["accuracy"] or 0) >= limits["min_test_accuracy"] and new_result["wilson95"] is not None and new_result["wilson95"][0] >= limits["min_wilson95_lower"] and new_result["date_cluster95"][0] >= limits["min_date_cluster95_lower"])
    assert digest(json.loads((output / "selection-before-test.json").read_text(encoding="utf-8"))) == selection_hash
    test_report = {"period": [start, end], "policy_sha256": digest(FILTER_POLICY), "selection_sha256": selection_hash, "selection_unchanged": True, "model_training_last_date": current["training_last_date"], "calibration_period": ["2024-07-01", "2025-07-01"], "temperature": temperature, "chosen_rule": selection["chosen_rule"], "selected_result": new_result, "fixed_controls": controls, "n_all": len(p), "research_only": True, "live_publication": "blocked: source dates/timezones/provider mappings and fresh live data unverified; no active approved model", "limitations": ["Twelve candidates examined on validation: validation confidence bounds are not multiplicity-adjusted", "Models share inputs; agreement is correlated", "No injuries, lineups, xG, cup-calendar fatigue or verified current provider data", "Stress bounds are sensitivity scenarios, not probability confidence intervals", "Accepted-source dates may contain undetected errors; this is retrospective replay", "No model registry or application changes; no live API requests"]}
    write_json(output / "new-test.json", test_report)
    write_jsonl(output / "new-test-predictions.jsonl", [{"id": r["id"], "date": r["date"], "league": r["league"], "target": r["target"], "information_cutoff_date": r["information_cutoff_date"], "probabilities_raw": p[i].tolist(), "probabilities_calibrated": calibrated[i].tolist(), "model_probabilities": {n: v[i].tolist() for n, v in current["predictions"].items()}, "history": contexts[r["id"]], "history_rejections": history_reasons(r, contexts[r["id"]]), "decision": decisions[i] if decisions else {"selected": False, "reasons": ["no_validation_qualified_rule"]}} for i, r in enumerate(current["rows"])])
    with (output / "validation-candidates.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["rule", "selected", "coverage", "accuracy", "mean_probability", "wilson_lower", "date_cluster_lower", "qualified", "rejection_reasons"])
        for c in candidates:
            s = c["summary"]
            writer.writerow([c["id"], s["n"], s["coverage"], s["accuracy"], s.get("mean_probability"), s["wilson95"][0] if s["wilson95"] else None, s["date_cluster95"][0] if s["date_cluster95"] else None, c["qualified"], ";".join(c["qualification_failures"])])
    print(json.dumps({"chosen_rule": selection["chosen_rule"], "validation_status": selection["status"], "new_test": new_result, "controls": {name: {k: m[k] for k in ["n", "coverage", "accuracy"]} for name, m in controls.items()}}, indent=2))
    return selection, test_report


if __name__ == "__main__":
    run()
