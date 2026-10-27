"""Frozen v2 retrospective comparison; explicitly not a new unseen holdout."""
import json
import platform
from pathlib import Path

import numpy as np

from ml.evaluate import cluster_ci, metric_values, predict, train_challengers
from ml.expanded import CONFIG, OUTPUT
from ml.goal_markets import goal_markets
from ml.models import FEATURES, replay
from ml.pipeline import POLICY, ROOT, digest, write_json


def assess(rows, probabilities):
    result = {}
    for league in ["all", *CONFIG["leagues"]]:
        mask = np.array([league == "all" or r["league"] == league for r in rows])
        subset = [r for r, keep in zip(rows, mask) if keep]
        if not subset:
            continue
        metrics, values = metric_values([r["target"] for r in subset], probabilities[mask])
        metrics["ci95_date_cluster_bootstrap"] = dict(zip(["log_loss", "brier", "accuracy"], cluster_ci(values, [r["date"] for r in subset], repeats=500)))
        result[league] = metrics
    return result


def binary_metrics(y, p, dates):
    y, p = np.asarray(y, dtype=float), np.asarray(p, dtype=float)
    loss = -(y * np.log(np.clip(p, 1e-15, 1)) + (1-y) * np.log(np.clip(1-p, 1e-15, 1)))
    brier = (y-p)**2
    correct = ((p >= .5) == y).astype(float)
    bins = []
    for index in range(10):
        mask = (p >= index / 10) & (p < (index+1)/10 if index < 9 else p <= 1)
        if mask.any():
            bins.append({"bin": index, "n": int(mask.sum()), "predicted": float(p[mask].mean()), "observed": float(y[mask].mean())})
    return {"n": len(y), "log_loss": float(loss.mean()), "brier": float(brier.mean()), "accuracy": float(correct.mean()), "ece": sum(b["n"] / len(y) * abs(b["predicted"]-b["observed"]) for b in bins), "calibration_bins": bins, "ci95_date_cluster_bootstrap": dict(zip(["log_loss", "brier", "accuracy"], cluster_ci(np.column_stack([loss, brier, correct]), dates, repeats=500)))}


def run(output=None):
    output = Path(output or ROOT / "reports/recent-v2")
    output.mkdir(parents=True, exist_ok=True)
    accepted = [json.loads(line) for line in (OUTPUT / "accepted.jsonl").read_text(encoding="utf-8").splitlines()]
    quality = json.loads((OUTPUT / "quality-report.json").read_text(encoding="utf-8"))
    protocol = {"config": CONFIG, "dataset_version": quality["dataset_version"], "mode": "retrospective_exploratory_previously_seen_dates", "parameter_source": "legacy frozen protocol-1 parameters, unchanged; no hyperparameter search", "market_protocol": "independent Poisson half-goal lines 1.5/2.5/3.5 and BTTS; no tuning, no promotion", "selection": "minimum pooled validation 1X2 log loss; no claim of significance or live eligibility"}
    lock = output / "protocol-before-evaluation.json"
    if lock.exists() and json.loads(lock.read_text(encoding="utf-8")) != protocol:
        raise ValueError("v2_protocol_or_dataset_changed_use_new_version")
    write_json(lock, protocol)
    rows, states = replay(accepted)
    rows = [r for r in rows if r["history_matches"] >= 40]
    validations, pooled = [], []
    names = ["league", "elo", "poisson", "logistic", "xgboost"]
    for start, end in CONFIG["validation"]:
        train = [r for r in rows if r["date"] < start]
        validation = [r for r in rows if start <= r["date"] < end]
        predictions = predict(validation, train_challengers(train))
        validations.append({"start": start, "end_exclusive": end, "training_last_date": max(r["date"] for r in train), "metrics": {name: assess(validation, predictions[name]) for name in names}})
        pooled.extend((r, {name: predictions[name][i].tolist() for name in names}) for i, r in enumerate(validation))
    validation_scores = {name: metric_values([r[0]["target"] for r in pooled], [r[1][name] for r in pooled])[0]["log_loss"] for name in names}
    selected = min(names, key=lambda name: (validation_scores[name], name))
    write_json(output / "selection-before-test.json", {"selected": selected, "validation_log_loss": validation_scores, "auto_promoted": False, "status": protocol["mode"]})
    start, end = CONFIG["retrospective_test"]
    train = [r for r in rows if r["date"] < start]
    test = [r for r in rows if start <= r["date"] < end]
    predictions = predict(test, train_challengers(train))
    results = {name: assess(test, predictions[name]) for name in names}
    labels = {r["id"]: r["goals"] for r in accepted}
    markets = {name: {} for name in goal_markets(1, 1)}
    for name in markets:
        for league in ["all", *CONFIG["leagues"]]:
            subset = [r for r in test if league == "all" or r["league"] == league]
            if not subset:
                continue
            probabilities = [goal_markets(r["home_rate"], r["away_rate"])[name] for r in subset]
            target = []
            for row in subset:
                h, a = labels[row["id"]]
                if name.startswith("over_"):
                    target.append(int(h+a > float(name.split("_")[1])))
                elif name.startswith("under_"):
                    target.append(int(h+a < float(name.split("_")[1])))
                else:
                    target.append(int((h > 0 and a > 0) == name.endswith("yes")))
            markets[name][league] = binary_metrics(target, probabilities, [r["date"] for r in subset])
    report = {"protocol": protocol, "dataset_version": quality["dataset_version"], "quality": quality, "validation": validations, "selection": {"selected": selected, "validation_log_loss": validation_scores, "auto_promoted": False}, "test": {"start": start, "end_exclusive": end, "n": len(test), "training_last_date": max(r["date"] for r in train), "metrics": results}, "goal_markets": markets, "live_approved": False, "limitations": [*quality["limitations"], CONFIG["test_status"], "Raw goal-market probabilities uncalibrated; no selected hit-rate claim", "No inference that more leagues improves each league; reported separately", "No prospective bundle performance evidence; live selections remain blocked"]}
    write_json(output / "backtest.json", report)
    # A separate, checksummed candidate, leaving every legacy artifact/registry unchanged.
    models = train_challengers(rows)
    training_code = {name: hashlib_file(ROOT / name) for name in ["ml/models.py", "ml/evaluate.py", "ml/expanded.py", "ml/recent_evaluate.py", "ml/goal_markets.py", "requirements.lock"]}
    model_fingerprint = digest([models["logistic"].to_dict(), models["xgboost"].booster.save_raw(raw_format="json").hex(), report])
    version = "recent-v2-" + digest([quality["dataset_version"], CONFIG, selected, training_code, model_fingerprint])[:12]
    artifact = ROOT / "ml/models" / version
    artifact.mkdir(parents=True, exist_ok=True)
    write_json(artifact / "logistic.json", models["logistic"].to_dict())
    models["xgboost"].save_model(artifact / "xgboost.json")
    write_json(artifact / "baseline-state.json", {league: state.to_dict() for league, state in sorted(states.items())})
    write_json(artifact / "feature-schema.json", {"version": "features-v1", "features": FEATURES, "new_post_match_features": False})
    write_json(artifact / "config.json", {"data_protocol": CONFIG, "parameters": POLICY["parameters"], "challengers": POLICY["challengers"], "training_code_sha256": training_code})
    write_json(artifact / "metrics.json", {"selection": report["selection"], "test": report["test"], "goal_markets": markets})
    checksums = {path.name: hashlib_file(path) for path in sorted(artifact.iterdir()) if path.name != "metadata.json"}
    import scipy
    import xgboost
    write_json(artifact / "metadata.json", {"version": version, "selected": selected, "dataset_version": quality["dataset_version"], "training_last_date": max(r["date"] for r in rows), "training_cutoff_exclusive": CONFIG["asof_exclusive"], "source_commit": CONFIG["source_commit"], "source_manifest_sha256": hashlib_file(OUTPUT / "source-manifest.json"), "checksums": checksums, "feature_schema": "features-v1", "runtime": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__, "xgboost": xgboost.__version__}, "training_code_sha256": training_code, "status": "research_candidate_not_promoted", "license_notice": quality["licenses"], "validation_test_interpretation": CONFIG["test_status"]})
    write_json(ROOT / "ml/models/recent-v2-registry.json", {"active_version": None, "candidate": version, "auto_promote": False})
    print(json.dumps({"accepted": len(accepted), "test_n": len(test), "selected": selected, "test": {name: {key: results[name]["all"][key] for key in ["log_loss", "brier", "accuracy"]} for name in names}, "candidate": version}))
    return report


def hashlib_file(path):
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    run()
