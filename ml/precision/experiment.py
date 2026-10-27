"""Predeclared model/calibration/filter experiments; preserve every result version."""
import hashlib
import json
import platform
from collections import defaultdict, deque
from itertools import groupby

import numpy as np
import scipy
import xgboost as xgb

from ml.evaluate import LogisticModel, cluster_ci, metric_values
from ml.expanded import CONFIG as DATA_CONFIG, OUTPUT
from ml.goal_markets import goal_markets
from ml.pipeline import ROOT, digest, write_json, write_jsonl
from ml.precision.calibration import fit_platt, fit_temperature, platt_transform, temperature_transform
from ml.precision.features import CACHE, CONFIG, FEATURES, build
from ml.precision.selection import choose_policy, select, summarize
from ml.recent_evaluate import binary_metrics


def json_digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def immutable_json(path, value):
    if path.exists() and digest(json.loads(path.read_text(encoding="utf-8"))) != digest(value):
        raise ValueError("precision_evidence_is_immutable_use_new_version: "+path.name)
    write_json(path, value)


def fit_models(rows):
    if not rows:
        raise ValueError("empty_training")
    x = np.asarray([r["features"] for r in rows], dtype=float)
    y = np.asarray([r["target"] for r in rows], dtype=int)
    models = {"legacy-logistic": LogisticModel().fit(np.asarray([r["legacy_features"] for r in rows]), y), "enhanced-logistic": LogisticModel().fit(x, y)}
    local = {}
    for league in sorted({r["league"] for r in rows}):
        mask = np.asarray([r["league"] == league for r in rows])
        if mask.sum() >= 200 and len(np.unique(y[mask])) == 3:
            local[league] = {"n": int(mask.sum()), "model": LogisticModel().fit(x[mask], y[mask])}
    models["league-shrunk-logistic"] = local
    cfg = CONFIG["xgboost"]
    for depth in [2, 3]:
        booster = xgb.train({"objective": "multi:softprob", "num_class": 3, "eval_metric": "mlogloss", "max_depth": depth, **{k: v for k, v in cfg.items() if k != "rounds"}}, xgb.DMatrix(x, label=y, feature_names=FEATURES), num_boost_round=cfg["rounds"])
        models[f"enhanced-xgb-d{depth}"] = booster
    return models


def model_predictions(models, rows):
    x = np.asarray([r["features"] for r in rows])
    result = {"legacy-logistic": models["legacy-logistic"].predict_proba(np.asarray([r["legacy_features"] for r in rows])), "enhanced-logistic": models["enhanced-logistic"].predict_proba(x), "league-prior": np.asarray([r["league_prior"] for r in rows]), "legacy-elo": np.asarray([r["elo"] for r in rows]), "legacy-poisson": np.asarray([r["legacy_poisson"] for r in rows])}
    local = result["enhanced-logistic"].copy()
    for league, item in models["league-shrunk-logistic"].items():
        indices = np.asarray([i for i, r in enumerate(rows) if r["league"] == league], dtype=int)
        if len(indices):
            w = item["n"]/(item["n"]+1000)
            local[indices] = w*item["model"].predict_proba(x[indices])+(1-w)*local[indices]
    result["league-shrunk-logistic"] = local
    for depth in [2, 3]:
        name = f"enhanced-xgb-d{depth}"
        result[name] = models[name].predict(xgb.DMatrix(x, feature_names=FEATURES))
    for config in CONFIG["goal_models"]:
        result[config["id"]] = np.asarray([r["dc"][config["id"]]["probabilities"] for r in rows])
    result[CONFIG["ensemble"]["id"]] = .5*result["enhanced-logistic"]+.5*result["dc365-r4"]
    return result


def all_metrics(rows, probabilities, per_league=False):
    metrics = {}
    for league in ["all", *sorted({r["league"] for r in rows})] if per_league else ["all"]:
        mask = np.asarray([league == "all" or r["league"] == league for r in rows])
        subset = [r for r, keep in zip(rows, mask) if keep]
        values, samples = metric_values([r["target"] for r in subset], np.asarray(probabilities)[mask])
        values["ci95_date_cluster_bootstrap"] = dict(zip(["log_loss", "brier", "accuracy"], cluster_ci(samples, [r["date"] for r in subset])))
        metrics[league] = values
    return metrics


def binary_labels(goals, market):
    h, a = goals
    return int(h+a > float(market.split("_")[1])) if market.startswith("over_") else int(h > 0 and a > 0)


def prior_markets():
    matches = [json.loads(line) for line in (OUTPUT/"accepted.jsonl").read_text(encoding="utf-8").splitlines()]
    history = defaultdict(lambda: deque(maxlen=380))
    prior = goal_markets(1.5, 1.2)
    result = {}
    markets = CONFIG["goal_market_diagnostics"]["markets"]
    for _, items in groupby(matches, key=lambda m: m["date"]):
        batch = list(items)
        for match in batch:
            values = history[match["league"]]
            result[match["id"]] = {name: (sum(v[name] for v in values)+30*prior[name])/(len(values)+30) for name in markets}
        for match in batch:
            history[match["league"]].append({name: binary_labels(match["goals"], name) for name in markets})
    return result


def market_variants(rows, previous_rows, baselines, cutoff):
    output, calibration = {}, {}
    for market in CONFIG["goal_market_diagnostics"]["markets"]:
        output[market], calibration[market] = {}, {}
        y = [binary_labels(r["goals"], market) for r in previous_rows]
        for goal_name in ["dc180-r4", "dc365-r4"]:
            for weight in CONFIG["goal_market_diagnostics"]["blend_weights"]:
                name = goal_name+"-w"+str(int(weight*100))
                raw = np.asarray([weight*r["dc"][goal_name]["markets"][market]+(1-weight)*baselines[r["id"]][market] for r in rows])
                old = np.asarray([weight*r["dc"][goal_name]["markets"][market]+(1-weight)*baselines[r["id"]][market] for r in previous_rows])
                parameters = fit_platt(old, y, [r["date"] for r in previous_rows], cutoff) if len(previous_rows) >= 300 else [1., 0.]
                output[market][name+":raw"] = raw
                output[market][name+":previous-oof-platt"] = platt_transform(raw, parameters)
                calibration[market][name] = parameters
    return output, calibration


def confirmation(summary, policy):
    if policy is None:
        return {"passed": False, "reasons": ["no_validation_policy_qualified"], "prospective_certified": False}
    cfg = CONFIG["selective"]["test_confirmation"]
    tier = next(t for t in CONFIG["selective"]["tiers"] if t["id"] == policy["selected_tier"])
    checks = {"sample": summary["n"] >= cfg["minimum_selected"], "each_supported_league": all(summary["per_league"].get(league, {}).get("n", 0) >= cfg["minimum_each_supported_league"] for league in policy["supported_leagues"]), "coverage": summary["coverage"] >= cfg["minimum_coverage"], "point_target": (summary["accuracy"] or 0) >= tier["minimum_point_accuracy"], "wilson_lower": summary["wilson95"] is not None and summary["wilson95"][0] >= cfg["minimum_wilson_lower"], "cluster_lower": summary["date_cluster95"] is not None and summary["date_cluster95"][0] >= cfg["minimum_date_cluster_lower"]}
    return {"passed": all(checks.values()), "checks": checks, "reasons": [k for k, v in checks.items() if not v], "prospective_certified": False}


def run():
    rows = build()
    dataset = json.loads((OUTPUT/"quality-report.json").read_text(encoding="utf-8"))
    feature_manifest = json.loads((CACHE/"manifest.json").read_text(encoding="utf-8"))
    code = {path.relative_to(ROOT).as_posix(): json_digest(path) for path in sorted((ROOT/"ml/precision").glob("*.py"))}
    for name in ["ml/models.py", "ml/evaluate.py", "ml/selective.py", "ml/goal_markets.py", "ml/expanded.py", "ml/precision_predict.py", "requirements.lock"]:
        code[name] = json_digest(ROOT/name)
    runtime = {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__, "xgboost": xgb.__version__, "os": platform.system(), "machine": platform.machine()}
    run_id = "precision-v3-"+digest([CONFIG, dataset["dataset_version"], feature_manifest["signature"], code, runtime])[:12]
    output = ROOT/"reports/precision-v3"/run_id
    output.mkdir(parents=True, exist_ok=True)
    protocol = {"run_id": run_id, "config": CONFIG, "dataset_version": dataset["dataset_version"], "feature_signature": feature_manifest["signature"], "code_sha256": code, "runtime": runtime, "live_approved": False}
    immutable_json(output/"protocol-before-evaluation.json", protocol)
    baselines = prior_markets()
    yearly, previous, previous_rows, calibration_logs = {}, [], [], []
    validation_rows, validation_probabilities, fold_ids = [], defaultdict(list), []
    validation_market = defaultdict(lambda: defaultdict(list))
    model_files = {}
    for year in range(2022, 2027):
        start, end = f"{year}-07-01", f"{year+1}-07-01"
        train, fold = [r for r in rows if r["date"] < start], [r for r in rows if start <= r["date"] < end]
        if not fold:
            continue
        models = fit_models(train)
        raw = model_predictions(models, fold)
        predictions, temperatures = {}, {}
        for name, probabilities in raw.items():
            old = np.concatenate([part["raw"][name] for part in previous]) if previous else np.empty((0, 3))
            temperature = fit_temperature(old, [r["target"] for r in previous_rows], [r["date"] for r in previous_rows], start) if len(old) >= 300 else 1.
            predictions[name+":raw"] = probabilities
            predictions[name+":previous-oof-temperature"] = temperature_transform(probabilities, temperature)
            temperatures[name] = temperature
        market_probs, market_calibration = market_variants(fold, previous_rows, baselines, start)
        yearly[year] = {"rows": fold, "raw": raw, "predictions": predictions, "markets": market_probs, "temperatures": temperatures}
        calibration_logs.append({"year": year, "classifier_training_last_date": max(r["date"] for r in train), "calibration_training_last_date": max((r["date"] for r in previous_rows), default=None), "n_prior_oof": len(previous_rows), "temperatures": temperatures, "market_platt": market_calibration})
        if year in [2023, 2024]:
            validation_rows.extend(fold)
            fold_ids.extend([year]*len(fold))
            for name, values in predictions.items():
                validation_probabilities[name].extend(values.tolist())
            for market, variants in market_probs.items():
                for name, values in variants.items():
                    validation_market[market][name].extend(values.tolist())
        previous.append({"rows": fold, "raw": raw})
        previous_rows.extend(fold)
        model_files[year] = models
        print(json.dumps({"phase": "out_of_time_prediction", "year": year, "train": len(train), "predicted": len(fold), "prior_oof": len(previous_rows)-len(fold)}), flush=True)
    val_scores = {name: metric_values([r["target"] for r in validation_rows], values)[0] for name, values in validation_probabilities.items()}
    selected_name = min(val_scores, key=lambda name: (val_scores[name]["log_loss"], name))
    selected_probs = np.asarray(validation_probabilities[selected_name])
    policy, candidates = choose_policy(validation_rows, selected_probs, fold_ids)
    market_choices, market_validation_scores = {}, {}
    for market, variants in validation_market.items():
        target = [binary_labels(r["goals"], market) for r in validation_rows]
        scores = {name: binary_metrics(target, values, [r["date"] for r in validation_rows]) for name, values in variants.items()}
        market_validation_scores[market] = scores
        market_choices[market] = min(scores, key=lambda name: (scores[name]["log_loss"], name))
    selection = {"selected_model": selected_name, "selected_policy": policy, "selective_candidates": candidates, "validation_metrics": val_scores, "market_choices": market_choices, "market_validation_scores": market_validation_scores, "model_candidates_compared": len(val_scores), "selective_candidates_compared": len(candidates), "market_candidates_per_target": len(next(iter(validation_market.values()))), "auto_promote": False, "interpretation": CONFIG["test_interpretation"]}
    immutable_json(output/"selection-before-test.json", selection)
    evaluations = {}
    for year, label in [(2025, "retrospective_test"), (2026, "current_season_audit")]:
        part = yearly.get(year)
        if not part:
            continue
        subset = part["rows"]
        probabilities = part["predictions"][selected_name]
        mask = select(subset, probabilities, policy["threshold"], policy["layer"], policy["supported_leagues"]) if policy else np.zeros(len(subset), dtype=bool)
        summary = summarize(subset, probabilities, mask)
        market_metrics = {}
        for market, choice in market_choices.items():
            target = [binary_labels(r["goals"], market) for r in subset]
            selected_market_p = part["markets"][market][choice]
            baseline_p = [baselines[r["id"]][market] for r in subset]
            market_metrics[market] = {"model": choice, "selected": binary_metrics(target, selected_market_p, [r["date"] for r in subset]), "league_baseline": binary_metrics(target, baseline_p, [r["date"] for r in subset])}
        controls = {name: all_metrics(subset, values)["all"] for name, values in part["predictions"].items()}
        evaluations[label] = {"n": len(subset), "start": min(r["date"] for r in subset), "last_date": max(r["date"] for r in subset), "selected_model_metrics": all_metrics(subset, probabilities, per_league=True), "selective": summary, "confirmation": confirmation(summary, policy), "fixed_model_controls": controls, "goal_markets": market_metrics}
        immutable_json(output/(label+".json"), evaluations[label])
        write_jsonl(output/(label+"-predictions.jsonl"), [{"id": r["id"], "league": r["league"], "date": r["date"], "home": r["home"], "away": r["away"], "goals": r["goals"], "target": r["target"], "probabilities": probabilities[i].tolist(), "selected": bool(mask[i]), "context": r["context"], "information_cutoff_date": r["cutoff_date"], "goal_training_last_date": r["dc"]["dc365-r4"]["training_last_date"]} for i, r in enumerate(subset)])
    write_json(output/"calibration-audit.json", calibration_logs)
    # Forward research artifact: refit with known rows, never use this refit to score old tests.
    final_models = fit_models(rows)
    artifact = ROOT/"ml/models"/run_id
    artifact.mkdir(parents=True, exist_ok=True)
    for name in ["legacy-logistic", "enhanced-logistic"]:
        write_json(artifact/(name+".json"), final_models[name].to_dict())
    for depth in [2, 3]:
        final_models[f"enhanced-xgb-d{depth}"].save_model(artifact/f"enhanced-xgb-d{depth}.json")
    write_json(artifact/"league-logistics.json", {league: {"n": item["n"], "model": item["model"].to_dict()} for league, item in final_models["league-shrunk-logistic"].items()})
    write_json(artifact/"feature-schema.json", {"version": "features-v3", "features": FEATURES})
    write_json(artifact/"selection.json", selection)
    write_json(artifact/"config.json", CONFIG)
    write_json(artifact/"goal-models.json", json.loads((CACHE/"goal_models.json").read_text(encoding="utf-8")))
    forward_calibration = {}
    for name in yearly[2026]["raw"]:
        values = np.concatenate([part["raw"][name] for part in previous])
        forward_calibration[name] = fit_temperature(values, [r["target"] for r in previous_rows], [r["date"] for r in previous_rows], DATA_CONFIG["asof_exclusive"])
    _, forward_market = market_variants([], previous_rows, baselines, DATA_CONFIG["asof_exclusive"])
    write_json(artifact/"forward-calibration.json", {"temperatures": forward_calibration, "markets": forward_market, "last_oof_date": max(r["date"] for r in previous_rows), "cutoff_exclusive": DATA_CONFIG["asof_exclusive"], "purpose": "future inference only, never substitutes test calibrators"})
    metadata = {"version": run_id, "status": "research_only_not_promoted", "training_last_date": max(r["date"] for r in rows), "training_cutoff_exclusive": DATA_CONFIG["asof_exclusive"], "dataset_version": dataset["dataset_version"], "source_commit": DATA_CONFIG["source_commit"], "feature_schema": "features-v3", "source_manifest_sha256": json_digest(OUTPUT/"source-manifest.json"), "training_code_sha256": code, "checksums": {p.name: json_digest(p) for p in sorted(artifact.glob("*.json")) if p.name != "metadata.json"}, "live_approved": False, "limitations": [CONFIG["test_interpretation"], "No new licensed injuries/lineups/xG/odds; enriched features remain score-derived", "Classifier calibration and selection are fitted using earlier OOF predictions only", "Multiple candidates searched; validation confidence intervals are not multiplicity-adjusted", "All source dates/mappings remain unverified; no prospective certification", "58-feature research artifact requires a matching feature engine before production inference"]}
    write_json(artifact/"metadata.json", metadata)
    metadata["runtime"] = runtime
    metadata["requirements_sha256"] = json_digest(ROOT/"requirements.lock")
    write_json(artifact/"metadata.json", metadata)
    report = {"version": run_id, "protocol": protocol, "selection": selection, "evaluations": evaluations, "metadata": metadata, "live_approved": False, "auto_promote": False}
    write_json(output/"report.json", report)
    write_json(ROOT/"reports/precision-v3/latest.json", {"version": run_id, "report": str((output/"report.json").relative_to(ROOT)), "status": "research_only"})
    write_json(ROOT/"ml/models/precision-v3-registry.json", {"active_version": None, "candidate": run_id, "auto_promote": False})
    print(json.dumps({"run_id": run_id, "selected_model": selected_name, "policy": policy and {k: policy[k] for k in ["id", "selected_tier", "supported_leagues"]}, "test": evaluations["retrospective_test"]["selective"], "model_test": evaluations["retrospective_test"]["selected_model_metrics"]["all"]["log_loss"], "prospective_certified": False}), flush=True)
    return report


if __name__ == "__main__":
    run()
