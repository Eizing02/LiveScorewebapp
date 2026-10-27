"""Gated, temporal ablations for future API context; refuses invented training data."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import xgboost as xgb

from ml.evaluate import LogisticModel, metric_values
from ml.live.evaluate import grade
from ml.live.ledger import DIRECTORY, latest_observations, read_kind
from ml.live.normalize import moment, sha
from ml.pipeline import ROOT, write_json

CONFIG = json.loads((ROOT/"ml/config/live_challenger_v1.json").read_text(encoding="utf-8"))


def rich_values(context):
    availability = context["availability"]
    p = context["provider_forecast"].get("probabilities") or [None]*3
    return [context["past_xg"]["home"]["xg_for_mean"], context["past_xg"]["away"]["xg_for_mean"], availability.get("missing"), availability.get("questionable"), 1. if context["lineups"]["confirmed"] else None]+p


def impute_train(x):
    x = np.asarray(x, dtype=float)
    medians = np.array([float(np.median(column[np.isfinite(column)])) if np.isfinite(column).any() else 0. for column in x.T])
    return medians, transform(x, medians)


def transform(x, medians):
    x = np.asarray(x, dtype=float)
    missing = ~np.isfinite(x)
    return np.column_stack([np.where(missing, medians, x), missing.astype(float)])


def training_rows(directory, asof):
    observations = {r["fixture_id"]: r for r in latest_observations(read_kind(directory, "observations"), asof)}
    features = {r["id"]: r for r in read_kind(directory, "features")}
    unique = {}
    for p in sorted(read_kind(directory, "predictions"), key=lambda p: p["generated_at"]):
        if p.get("stage", "initial") != "initial" or moment(p["generated_at"]) > moment(asof):
            continue
        key = (p["fixture_id"], p["occurrence_id"])
        unique.setdefault(key, p)
    rows = []
    for prediction in unique.values():
        observation = observations.get(prediction["fixture_id"])
        label = grade(prediction, observation, asof)
        if label["outcome"] is None:
            continue
        feature = features[prediction["feature_snapshot_id"]]
        if moment(feature["available_at"]) > moment(prediction["generated_at"]):
            raise ValueError("future_feature_snapshot")
        extra = rich_values(prediction["rich_context"])
        rows.append({"fixture_id": prediction["fixture_id"], "date": prediction["generated_at"][:10], "label_available_at": observation["first_seen_at"], "features": feature["values"]+extra, "rich_observed": any(v is not None for v in extra), "target": label["outcome"], "baseline_probabilities": prediction["probabilities"]})
    return sorted(rows, key=lambda r: (r["date"], r["fixture_id"]))


def train(directory=DIRECTORY, check_only=False):
    now = datetime.now(timezone.utc).isoformat()
    rows = training_rows(directory, now)
    dates = sorted({r["date"] for r in rows})
    missing = []
    if len(rows) < CONFIG["minimum_settled_fixtures"]:
        missing.append("minimum_settled_fixtures")
    if len(dates) < CONFIG["minimum_distinct_dates"]:
        missing.append("minimum_distinct_dates")
    if sum(r["rich_observed"] for r in rows) < CONFIG["minimum_observed_rich_rows"]:
        missing.append("minimum_observed_rich_rows")
    report = {"status": "insufficient_prospective_training_data" if missing else "training", "rows": len(rows), "distinct_dates": len(dates), "rich_observed": sum(r["rich_observed"] for r in rows), "blocked_gates": missing, "protocol": CONFIG, "model_promoted": False, "accuracy_invented": False}
    destination = ROOT/"reports/live-research/challenger-training.json"
    if missing:
        write_json(destination, report)
        print(json.dumps({k: report[k] for k in ["status", "rows", "rich_observed", "blocked_gates"]}))
        return report
    if check_only:
        report["status"] = "ready_for_training_requires_durable_model_store"
        write_json(destination, report)
        return report
    val_start, test_start = dates[int(len(dates)*.6)], dates[int(len(dates)*.8)]
    train_rows = [r for r in rows if r["date"] < val_start and moment(r["label_available_at"]) < moment(val_start+"T00:00:00Z")]
    validation = [r for r in rows if val_start <= r["date"] < test_start and moment(r["label_available_at"]) < moment(test_start+"T00:00:00Z")]
    test = [r for r in rows if r["date"] >= test_start]
    if len(train_rows) < 500 or len(validation) < 100 or len(test) < CONFIG["test_acceptance"]["minimum_test_fixtures"]:
        report.update({"status": "insufficient_chronological_partitions", "split_counts": [len(train_rows), len(validation), len(test)]})
        write_json(destination, report)
        return report
    code_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    run_id = "live-challenger-"+sha([CONFIG, rows, code_hash])[:16]
    folder = ROOT/"ml/models"/run_id
    folder.mkdir(parents=True, exist_ok=True)
    limits = {"score58": 58, "score58_xg": 60, "score58_xg_availability": 63, "score58_xg_availability_provider": 66}
    models, validation_metrics = {}, {}
    y = np.array([r["target"] for r in train_rows])
    for ablation, width in limits.items():
        medians, x = impute_train([r["features"][:width] for r in train_rows])
        vx = transform([r["features"][:width] for r in validation], medians)
        logistic = LogisticModel().fit(x, y)
        booster = xgb.train({"objective": "multi:softprob", "num_class": 3, "max_depth": 2, "eta": .04, "min_child_weight": 20, "lambda": 5, "subsample": 1, "colsample_bytree": 1, "nthread": 1, "seed": 20261026, "tree_method": "hist"}, xgb.DMatrix(x, label=y), num_boost_round=150)
        for name, model in [("logistic", logistic), ("xgboost_depth2", booster)]:
            key = ablation+":"+name
            p = model.predict_proba(vx) if name == "logistic" else model.predict(xgb.DMatrix(vx))
            validation_metrics[key] = metric_values([r["target"] for r in validation], p)[0]
            models[key] = (model, medians, width, name)
    validation_metrics["frozen_v3"] = metric_values([r["target"] for r in validation], [r["baseline_probabilities"] for r in validation])[0]
    chosen = min(validation_metrics, key=lambda k: (validation_metrics[k]["log_loss"], k))
    write_json(folder/"selection-before-test.json", {"selected": chosen, "validation": validation_metrics, "test_start": test_start, "protocol": CONFIG})
    baseline = metric_values([r["target"] for r in test], [r["baseline_probabilities"] for r in test])[0]
    if chosen == "frozen_v3":
        test_metrics = baseline
    else:
        model, medians, width, family = models[chosen]
        x = transform([r["features"][:width] for r in test], medians)
        p = model.predict_proba(x) if family == "logistic" else model.predict(xgb.DMatrix(x))
        test_metrics = metric_values([r["target"] for r in test], p)[0]
        write_json(folder/"imputer.json", {"medians": medians.tolist(), "width": width, "missing_indicators": True})
        if family == "logistic":
            write_json(folder/"model.json", model.to_dict())
        else:
            model.save_model(folder/"model.json")
    acceptance = CONFIG["test_acceptance"]
    passed = test_metrics["log_loss"] <= baseline["log_loss"]*(1-acceptance["minimum_relative_log_loss_improvement"]) and test_metrics["ece"] <= acceptance["maximum_ece"]
    from ml.pipeline import POLICY
    from ml.precision.features import FEATURES
    names = FEATURES+CONFIG["api_feature_fields"]
    write_json(folder/"feature-schema.json", {"version": CONFIG["version"], "fields": names, "selected_width": 58 if chosen == "frozen_v3" else models[chosen][2], "missing_indicators": chosen != "frozen_v3", "classes": ["home", "draw", "away"]})
    write_json(folder/"training-manifest.json", {"dataset_version": sha(rows), "training_rows_sha256": sha(train_rows), "validation_rows_sha256": sha(validation), "test_rows_sha256": sha(test), "source_commit": POLICY["source_commit"], "training_cutoff_exclusive": val_start, "validation_cutoff_exclusive": test_start, "training_configuration": CONFIG, "training_code_sha256": code_hash, "random_seed": 20261026})
    report.update({"version": run_id, "status": "evaluated_research_only", "selected": chosen, "validation": validation_metrics, "test": test_metrics, "baseline_test": baseline, "statistical_gate_point_estimate": passed, "prospective_certified": False, "split_counts": [len(train_rows), len(validation), len(test)], "scope": "Fold-trained candidate artifact, not a refit or promoted production model. Per-league selection confirmation and paired uncertainty remain required."})
    report["checksums"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.glob("*.json")) if p.name != "metadata.json"}
    report["frozen_model_reference"] = json.loads((ROOT/"ml/models/precision-v3-registry.json").read_text(encoding="utf-8"))["candidate"]
    report["artifact_storage"] = "Versioned local directory with checksums. A reviewed immutable Release is required before cloud training; temporary Actions artifacts are not the sole model store."
    write_json(folder/"metadata.json", report)
    write_json(destination, report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    train(check_only=parser.parse_args().check_only)
