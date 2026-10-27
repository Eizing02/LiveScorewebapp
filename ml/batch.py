"""Offline inference from verified registry artifacts; export/import network is separate."""
import argparse
import json
from pathlib import Path

import numpy as np
import xgboost as xgb

from ml.evaluate import LogisticModel, XGBoostModel
from ml.models import elo_probabilities, poisson_prediction
from ml.pipeline import ROOT, write_json
from ml.registry import verify


def predict_export(source, output, version=None, generated_at="2026-10-25T00:00:00Z"):
    registry = json.loads((ROOT / "ml/models/registry.json").read_text(encoding="utf-8"))
    version = version or registry["active"]
    algorithm = "poisson"
    model = None
    if version:
        meta = verify(version)
        algorithm = meta["algorithm_selected"]
        directory = ROOT / "ml/models" / version
        if algorithm == "logistic":
            model = LogisticModel.from_dict(json.loads((directory / "logistic.json").read_text()))
        elif algorithm == "xgboost":
            booster = xgb.Booster()
            booster.load_model(directory / "xgboost.json")
            model = XGBoostModel(booster)
    data = json.loads(Path(source).read_text(encoding="utf-8"))
    predictions = []
    for item in data["items"]:
        features = item["payload"]
        if isinstance(features, str):
            features = json.loads(features)
        if features["feature_schema_version"] != "features-v1":
            raise ValueError("feature_schema_mismatch")
        if features["information_cutoff_date"] >= item["kickoff_utc"][:10] or generated_at >= item["kickoff_utc"]:
            raise ValueError("batch_cutoff_violation")
        if model:
            p = model.predict_proba(np.array([features["features"]]))[0].tolist()
        elif algorithm == "elo":
            p = elo_probabilities(features["features"][0])
        elif algorithm == "league":
            p = features["league_prior"]
        else:
            p = poisson_prediction(features["home_rate"], features["away_rate"])["probabilities"]
        predictions.append({"id": f'{item["fixture_id"]}:{version or "poisson-v1"}:initial', "fixture_id": item["fixture_id"], "model_version": version or "poisson-v1", "generated_at": generated_at, "information_cutoff_date": features["information_cutoff_date"], "stage": "initial", "probabilities": p, "feature_snapshot_hash": item["snapshot_hash"]})
    write_json(output, {"predictions": predictions})
    return predictions


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(ROOT / "data/mock-feature-export.json"))
    parser.add_argument("--output", default=str(ROOT / "reports/batch-predictions.json"))
    parser.add_argument("--version")
    parser.add_argument("--generated-at", default="2026-10-25T00:00:00Z")
    args = parser.parse_args()
    print(f"Offline predictions: {len(predict_export(args.source, args.output, args.version, args.generated_at))}; no HTTP requests.")
