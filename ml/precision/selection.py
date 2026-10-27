"""Label-free eligibility and predeclared selective-accuracy qualification."""
from collections import Counter

import numpy as np

from ml.evaluate import cluster_ci, metric_values
from ml.precision.calibration import validate_probabilities
from ml.precision.features import CONFIG
from ml.selective import wilson_interval


def history_reasons(row, layer):
    p = CONFIG["selective"]
    c = row["context"]
    reasons = []
    if not row.get("cutoff_date") or row["cutoff_date"] >= row["date"]:
        reasons.append("invalid_feature_cutoff")
    if row["history_matches"] < 40 or min(c["venue"]) < p["minimum_venue_matches_each"]:
        reasons.append("insufficient_venue_history")
    if min(c["last365"]) < p["minimum_last365_each"]:
        reasons.append("insufficient_recent_history")
    if max(c["gaps"]) > p["maximum_known_league_gap_days"]:
        reasons.append("old_known_league_history")
    if layer == "strict_history" and min(c["season_matches"]) < p["strict_minimum_season_matches_each"]:
        reasons.append("early_season")
    return reasons


def select(rows, probabilities, threshold, layer, supported_leagues=None):
    probabilities = validate_probabilities(probabilities)
    if len(rows) != len(probabilities):
        raise ValueError("selection_shape")
    return np.array([float(p.max()) >= threshold and not history_reasons(row, layer) and (supported_leagues is None or row["league"] in supported_leagues) for row, p in zip(rows, probabilities)], dtype=bool)


def summarize(rows, probabilities, mask):
    p = validate_probabilities(probabilities)
    subset = [r for r, selected in zip(rows, mask) if selected]
    if not subset:
        return {"n": 0, "total": len(rows), "coverage": 0, "accuracy": None, "wilson95": None, "date_cluster95": None, "per_league": {}}
    q = p[mask]
    y = np.array([r["target"] for r in subset])
    metrics, values = metric_values(y, q)
    correct = int((q.argmax(axis=1) == y).sum())
    ci = cluster_ci(values, [r["date"] for r in subset])
    leagues = {}
    for league in sorted({r["league"] for r in rows}):
        indices = [i for i, row in enumerate(subset) if row["league"] == league]
        wins = sum(int(q[i].argmax()) == int(y[i]) for i in indices)
        leagues[league] = {"n": len(indices), "correct": wins, "accuracy": wins/len(indices) if indices else None, "wilson95": wilson_interval(wins, len(indices)) if indices else None}
    return {"n": len(subset), "total": len(rows), "coverage": len(subset)/len(rows), "correct": correct, "accuracy": metrics["accuracy"], "log_loss": metrics["log_loss"], "brier": metrics["brier"], "ece": metrics["ece"], "mean_probability": float(q.max(axis=1).mean()), "absolute_calibration_gap": abs(float(q.max(axis=1).mean())-metrics["accuracy"]), "wilson95": wilson_interval(correct, len(subset)), "date_cluster95": ci[2], "per_league": leagues}


def choose_policy(rows, probabilities, fold_ids):
    candidates = []
    cfg = CONFIG["selective"]
    for layer in cfg["layers"]:
        for threshold in cfg["thresholds"]:
            initial = select(rows, probabilities, threshold, layer)
            counts = Counter(r["league"] for r, keep in zip(rows, initial) if keep)
            # This support rule uses prediction counts, never labels or test outcomes.
            supported = sorted(league for league, n in counts.items() if n >= cfg["minimum_validation_selected_per_league"])
            mask = select(rows, probabilities, threshold, layer, supported)
            summary = summarize(rows, probabilities, mask)
            fold_stats = []
            for fold in sorted(set(fold_ids)):
                indices = np.asarray([i for i, f in enumerate(fold_ids) if f == fold], dtype=int)
                fold_stats.append(summarize([rows[i] for i in indices], np.asarray(probabilities)[indices], mask[indices]))
            tiers = []
            failures = {}
            for tier in cfg["tiers"]:
                checks = {"sample": summary["n"] >= cfg["minimum_validation_selected"], "fold_samples": all(f["n"] >= cfg["minimum_selected_each_fold"] for f in fold_stats), "coverage": summary["coverage"] >= cfg["minimum_coverage"], "point_target": (summary["accuracy"] or 0) >= tier["minimum_point_accuracy"], "wilson_lower": summary["wilson95"] is not None and summary["wilson95"][0] >= tier["minimum_wilson_lower"], "cluster_lower": summary["date_cluster95"] is not None and summary["date_cluster95"][0] >= tier["minimum_date_cluster_lower"], "calibration_gap": summary.get("absolute_calibration_gap", 1) <= cfg["max_abs_probability_hit_rate_gap"]}
                failures[tier["id"]] = [name for name, passed in checks.items() if not passed]
                if all(checks.values()):
                    tiers.append(tier["id"])
            candidates.append({"id": layer+"-p"+str(int(threshold*100)), "layer": layer, "threshold": threshold, "supported_leagues": supported, "summary": summary, "folds": fold_stats, "qualified_tiers": tiers, "failures": failures})
    chosen = None
    for tier in cfg["tiers"]:
        eligible = [c for c in candidates if tier["id"] in c["qualified_tiers"]]
        if eligible:
            chosen = dict(sorted(eligible, key=lambda c: (-c["summary"]["coverage"], -c["summary"]["date_cluster95"][0], c["id"]))[0])
            chosen["selected_tier"] = tier["id"]
            break
    return chosen, candidates
