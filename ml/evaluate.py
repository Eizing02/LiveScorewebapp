"""Frozen validation protocol and untouched final holdout; no auto promotion."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
import xgboost as xgb

from ml.models import FEATURES, PARAMS, replay
from ml.pipeline import POLICY, ROOT, digest, load_accepted, write_json, write_jsonl


def metric_values(y, p):
    y, p = np.asarray(y, dtype=int), np.asarray(p, dtype=float)
    if len(y) == 0 or p.shape != (len(y), 3) or not np.all(np.isfinite(p)) or np.any(p < 0) or not np.allclose(p.sum(axis=1), 1, atol=1e-6):
        raise ValueError("invalid_probabilities_or_empty_evaluation")
    losses = -np.log(np.clip(p[np.arange(len(y)), y], 1e-15, 1))
    brier = ((p - np.eye(3)[y]) ** 2).sum(axis=1)
    correct = (p.argmax(axis=1) == y).astype(float)
    bins = []
    confidence = p.max(axis=1)
    for b in range(10):
        mask = (confidence >= b / 10) & (confidence < (b + 1) / 10 if b < 9 else confidence <= 1)
        if mask.any():
            bins.append({"bin": b, "n": int(mask.sum()), "confidence": float(confidence[mask].mean()), "accuracy": float(correct[mask].mean())})
    ece = sum(v["n"] / len(y) * abs(v["confidence"] - v["accuracy"]) for v in bins)
    reliability = []
    for c in range(3):
        for b in range(10):
            mask = (p[:, c] >= b / 10) & (p[:, c] < (b + 1) / 10 if b < 9 else p[:, c] <= 1)
            if mask.any():
                reliability.append({"class": c, "bin": b, "n": int(mask.sum()), "predicted": float(p[mask, c].mean()), "observed": float((y[mask] == c).mean())})
    return {"n": len(y), "log_loss": float(losses.mean()), "brier": float(brier.mean()), "accuracy": float(correct.mean()), "ece": ece, "calibration_bins": bins, "reliability": reliability}, np.column_stack([losses, brier, correct])


def cluster_ci(values, dates, repeats=None):
    # Resample whole match dates, preserving correlation between same-day matches.
    values = np.asarray(values)
    days = np.unique(dates)
    groups = [values[np.asarray(dates) == day] for day in days]
    sums = np.array([g.sum(axis=0) for g in groups])
    sizes = np.array([len(g) for g in groups])
    rng = np.random.default_rng(PARAMS["seed"])
    draws = rng.integers(0, len(days), size=(repeats or POLICY["bootstrap_repeats"], len(days)))
    estimates = sums[draws].sum(axis=1) / sizes[draws].sum(axis=1)[:, None]
    return np.quantile(estimates, [0.025, 0.975], axis=0).T.tolist()


def train_challengers(rows):
    x, y = np.array([r["features"] for r in rows]), np.array([r["target"] for r in rows])
    logistic = LogisticModel().fit(x, y)
    booster = xgb.train({"max_depth": POLICY["challengers"]["xgb_max_depth"], "eta": POLICY["challengers"]["xgb_learning_rate"], "objective": "multi:softprob", "num_class": 3, "eval_metric": "mlogloss", "subsample": 1, "colsample_bytree": 1, "nthread": 1, "seed": PARAMS["seed"], "tree_method": "hist"}, xgb.DMatrix(x, label=y, feature_names=FEATURES), num_boost_round=POLICY["challengers"]["xgb_n_estimators"])
    return {"logistic": logistic, "xgboost": XGBoostModel(booster)}


class LogisticModel:
    """Multinomial softmax + L2, standardized training-only features, JSON serialization."""
    @staticmethod
    def softmax(z):
        exp = np.exp(z - z.max(axis=1, keepdims=True))
        return exp / exp.sum(axis=1, keepdims=True)

    def fit(self, x, y):
        self.mean = x.mean(axis=0)
        self.scale = x.std(axis=0)
        self.scale[self.scale < 1e-12] = 1
        design = np.column_stack([(x - self.mean) / self.scale, np.ones(len(x))])
        target = np.eye(3)[y]
        penalty = 1 / (POLICY["challengers"]["logistic_C"] * len(x))

        def objective(flat):
            weights = flat.reshape(design.shape[1], 3)
            p = self.softmax(design @ weights)
            loss = -np.log(np.clip(p[np.arange(len(y)), y], 1e-15, 1)).mean() + penalty / 2 * (weights[:-1] ** 2).sum()
            grad = design.T @ (p - target) / len(y)
            grad[:-1] += penalty * weights[:-1]
            return loss, grad.ravel()

        result = minimize(objective, np.zeros(design.shape[1] * 3), jac=True, method="L-BFGS-B", options={"maxiter": 1000, "ftol": 1e-12, "gtol": 1e-8})
        if not result.success:
            raise RuntimeError("logistic_optimization_failed: " + result.message)
        self.weights = result.x.reshape(design.shape[1], 3)
        return self

    def predict_proba(self, x):
        design = np.column_stack([(np.asarray(x) - self.mean) / self.scale, np.ones(len(x))])
        return self.softmax(design @ self.weights)

    def to_dict(self):
        return {"classes": [0, 1, 2], "mean": self.mean.tolist(), "scale": self.scale.tolist(), "weights": self.weights.tolist(), "implementation": "numpy-scipy-softmax-l2-v1"}

    @classmethod
    def from_dict(cls, data):
        obj = cls()
        obj.mean, obj.scale, obj.weights = np.array(data["mean"]), np.array(data["scale"]), np.array(data["weights"])
        return obj


class XGBoostModel:
    def __init__(self, booster):
        self.booster = booster

    def predict_proba(self, x):
        return self.booster.predict(xgb.DMatrix(x, feature_names=FEATURES))

    def save_model(self, path):
        self.booster.save_model(path)


def predict(rows, models):
    predictions = {}
    # r['league'] is competition code; the prior is renamed during feature preparation.
    for name in ["league_prior", "elo", "poisson"]:
        predictions["league" if name == "league_prior" else name] = np.array([r[name]["probabilities"] if name == "poisson" else r[name] for r in rows])
    x = np.array([r["features"] for r in rows])
    for name, model in models.items():
        predictions[name] = model.predict_proba(x)
    return predictions


def assess(rows, predictions):
    report = {}
    for name, p in predictions.items():
        report[name] = {}
        for league in ["all", *POLICY["leagues"]]:
            mask = np.array([league == "all" or r["league"] == league for r in rows])
            selected = [r for r, keep in zip(rows, mask) if keep]
            metrics, values = metric_values([r["target"] for r in selected], p[mask])
            ci = cluster_ci(values, [r["date"] for r in selected])
            metrics["ci95_date_cluster_bootstrap"] = dict(zip(["log_loss", "brier", "accuracy"], ci))
            report[name][league] = metrics
    return report


def run(output=ROOT / "reports"):
    output = Path(output)
    output.mkdir(exist_ok=True, parents=True)
    quality = json.loads((ROOT / "data/processed/quality-report.json").read_text(encoding="utf-8"))
    if quality["policy_sha256"] != digest(POLICY):
        raise ValueError("policy_changed_since_ingestion")
    accepted = load_accepted()
    feature_rows, _ = replay(accepted)
    rows = [r for r in feature_rows if r["history_matches"] >= PARAMS["min_history_matches"]]
    validation, fold_predictions = [], []
    for start, end in POLICY["validation_folds"]:
        train = [r for r in rows if r["date"] < start]
        test = [r for r in rows if start <= r["date"] < end]
        models = train_challengers(train)
        preds = predict(test, models)
        validation.append({"start": start, "end_exclusive": end, "training_n": len(train), "metrics": assess(test, preds)})
        fold_predictions.append((test, preds))
    names = ["league", "elo", "poisson", "logistic", "xgboost"]
    pooled_rows = [r for rs, _ in fold_predictions for r in rs]
    pooled_predictions = {n: np.concatenate([p[n] for _, p in fold_predictions]) for n in names}
    pooled = assess(pooled_rows, pooled_predictions)
    baseline = min(["league", "elo", "poisson"], key=lambda n: pooled[n]["all"]["log_loss"])
    challenger = min(["logistic", "xgboost"], key=lambda n: pooled[n]["all"]["log_loss"])
    gates = {}
    thresholds = POLICY["promotion"]
    for league in POLICY["leagues"]:
        a, b = pooled[challenger][league], pooled[baseline][league]
        mask = np.array([r["league"] == league for r in pooled_rows])
        y = [r["target"] for r in pooled_rows if r["league"] == league]
        _, av = metric_values(y, pooled_predictions[challenger][mask])
        _, bv = metric_values(y, pooled_predictions[baseline][mask])
        paired_ci = cluster_ci((av[:, 0] - bv[:, 0])[:, None], [r["date"] for r in pooled_rows if r["league"] == league])[0]
        wins = sum(f["metrics"][challenger][league]["log_loss"] < f["metrics"][baseline][league]["log_loss"] for f in validation)
        passed = a["n"] >= thresholds["min_samples_per_league"] and a["log_loss"] <= b["log_loss"] - thresholds["min_log_loss_improvement"] and a["brier"] <= b["brier"] + thresholds["max_brier_regression"] and a["ece"] <= b["ece"] + thresholds["max_ece_regression"] and wins >= thresholds["min_winning_folds"] and paired_ci[1] < 0
        gates[league] = {"passed": bool(passed), "winning_folds": wins, "paired_delta_log_loss_ci95": paired_ci}
    selected = challenger if all(g["passed"] for g in gates.values()) else baseline
    # The selected candidate is fixed now, before final holdout probabilities/metrics.
    selection = {"policy_sha256": digest(POLICY), "baseline": baseline, "challenger": challenger, "gates": gates, "selected_before_holdout": selected, "auto_promoted": False}
    write_json(output / "validation-selection.json", selection)
    start, end = POLICY["final_holdout"]
    models = train_challengers([r for r in rows if r["date"] < start])
    holdout = [r for r in rows if start <= r["date"] < end]
    final_predictions = predict(holdout, models)
    final_metrics = assess(holdout, final_predictions)
    report = {"protocol": POLICY, "policy_sha256": digest(POLICY), "dataset_version": quality["dataset_version"], "source_commit": POLICY["source_commit"], "validation_folds": validation, "validation_pooled": pooled, "selection": selection, "final_holdout": {"start": start, "end_exclusive": end, "n": len(holdout), "metrics": final_metrics, "best_observed_log_loss": min(names, key=lambda n: final_metrics[n]["all"]["log_loss"]), "selection_unchanged_after_holdout": True}, "limitations": [quality["quality_scope"], "Retrospective replay of corrected-later source, not prospective snapshots", "95% season coverage gate; missing La Liga 2024/25 results may cause selection bias", "Date-cluster CI does not fully model season/team dependence", "No odds, injuries, xG or target-match post-kickoff features"]}
    write_json(output / "backtest.json", report)
    write_jsonl(ROOT / "data/processed/features.jsonl", rows)
    write_jsonl(output / "holdout-predictions.jsonl", [{"id": r["id"], "date": r["date"], "league": r["league"], "target": r["target"], "information_cutoff_date": r["information_cutoff_date"], "predictions": {n: final_predictions[n][i].tolist() for n in names}} for i, r in enumerate(holdout)])
    with (output / "metrics.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["split", "model", "league", "n", "log_loss", "brier", "accuracy", "ece"])
        for split, metrics in [("validation", pooled), ("holdout", final_metrics)]:
            for model, groups in metrics.items():
                for league, m in groups.items():
                    writer.writerow([split, model, league, *[m[k] for k in ["n", "log_loss", "brier", "accuracy", "ece"]]])
    report["artifact_version"] = save_registry(rows, accepted, report)
    write_json(output / "backtest.json", report)
    plot_calibration(report, output)
    print(json.dumps({"selection": selection, "holdout": {n: {k: final_metrics[n]["all"][k] for k in ["n", "log_loss", "brier", "accuracy", "ece"]} for n in names}}, indent=2))
    return report


def save_registry(rows, accepted, report):
    cutoff = POLICY["deployment_cutoff_exclusive"]
    training_rows = [r for r in rows if r["date"] < cutoff]
    models = train_challengers(training_rows)
    _, states = replay([r for r in accepted if r["date"] < cutoff])
    import hashlib
    import tempfile
    import importlib.metadata
    import platform
    code_hashes = {name: hashlib.sha256((ROOT / "ml" / name).read_bytes()).hexdigest() for name in ["pipeline.py", "models.py", "evaluate.py"]}
    runtime = {"python": platform.python_version(), "os": platform.system(), "machine": platform.machine(), "packages": {p: importlib.metadata.version(p) for p in ["numpy", "scipy", "xgboost"]}}
    version = "v1-" + digest([report["dataset_version"], POLICY, code_hashes, runtime])[:12]
    model_root = ROOT / "ml/models"
    model_root.mkdir(parents=True, exist_ok=True)
    staging = tempfile.TemporaryDirectory(dir=model_root, prefix=".candidate-")
    directory = Path(staging.name)
    write_json(directory / "baseline-state.json", {league: state.to_dict() for league, state in states.items()})
    write_json(directory / "logistic.json", models["logistic"].to_dict())
    models["xgboost"].save_model(directory / "xgboost.json")
    write_json(directory / "feature-schema.json", {"version": "features-v1", "columns": FEATURES, "class_order": ["home", "draw", "away"], "cutoff": "strictly prior source dates; date-batched updates"})
    write_json(directory / "config.json", POLICY)
    write_json(directory / "metrics.json", {"validation": report["validation_pooled"], "holdout": report["final_holdout"]["metrics"]})
    checksums = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.iterdir()) if p.name != "metadata.json"}
    metadata = {"version": version, "algorithm_selected": report["selection"]["selected_before_holdout"], "status": "candidate_requires_manual_approval", "training_dataset_version": report["dataset_version"], "training_cutoff_exclusive": cutoff, "last_training_result_date": max(r["date"] for r in training_rows), "source_commit": POLICY["source_commit"], "feature_schema_version": "features-v1", "policy_sha256": digest(POLICY), "checksums": checksums, "runtime_versions": {p: importlib.metadata.version(p) for p in ["numpy", "scipy", "xgboost"]}, "logistic_implementation": "NumPy/SciPy softmax L2; sklearn DLL blocked by host Application Control", "evaluation_weights_cutoff": POLICY["final_holdout"][0], "deployment_refit_includes_holdout": True, "note": "Metrics describe fold-specific frozen estimators, not evaluation of the deployment refit on its training set."}
    metadata["training_code_sha256"] = code_hashes
    metadata["runtime_fingerprint"] = runtime
    write_json(directory / "metadata.json", metadata)
    target = model_root / version
    if target.exists():
        for file in directory.iterdir():
            if not (target / file.name).exists() or (target / file.name).read_bytes() != file.read_bytes():
                raise ValueError("immutable_model_version_collision")
    else:
        import shutil
        shutil.copytree(directory, target)
    staging.cleanup()
    registry_path = ROOT / "ml/models/registry.json"
    if not registry_path.exists():
        write_json(registry_path, {"active": None, "previous": None, "latest_candidate": version, "candidates": [version], "MODEL_AUTO_PROMOTE": False})
    else:
        registry = json.loads(registry_path.read_text())
        registry["candidates"] = sorted(set(registry["candidates"] + [version]))
        registry["latest_candidate"] = version
        write_json(registry_path, registry)
    return version


def plot_calibration(report, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    for c, ax in enumerate(axes):
        ax.plot([0, 1], [0, 1], "--", color="gray")
        for name, groups in report["final_holdout"]["metrics"].items():
            bins = [b for b in groups["all"]["reliability"] if b["class"] == c and b["n"] >= 20]
            ax.plot([b["predicted"] for b in bins], [b["observed"] for b in bins], marker=".", label=name)
        ax.set(title=["Home", "Draw", "Away"][c], xlabel="Predicted probability", ylabel="Observed fraction", xlim=(0, 1), ylim=(0, 1))
    axes[-1].legend(fontsize=8)
    fig.suptitle("Final temporal holdout reliability (bins n >= 20)")
    fig.tight_layout()
    fig.savefig(output / "calibration.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "reports")
    run(parser.parse_args().output)
