import copy

import numpy as np
import pytest

from ml.live.challengers import impute_train, train, transform
from ml.live.context import context_for
from ml.live.evaluate import grade
from ml.provider_policy import validate_query


def prediction():
    return {"snapshot_id": "unit-only", "fixture_id": "unit-fixture", "occurrence_id": "unit-occurrence", "generated_at": "2026-10-26T10:00:00Z", "probabilities": [.8, .1, .1]}


def observation():
    return {"fixture_id": "unit-fixture", "occurrence_id": "unit-occurrence", "observation_id": "unit-result-one", "first_seen_at": "2026-10-26T15:00:00Z", "kickoff_utc": "2026-10-26T12:00:00Z", "status": "finished_penalties", "score_90": [1, 1], "quarantine_reasons": []}


def test_grading_uses_90_minutes_and_result_corrections_do_not_change_forecasts():
    p, result = prediction(), observation()
    original = copy.deepcopy(p)
    first = grade(p, result, "2026-10-27T00:00:00Z")
    assert first["grade"] == "loss" and first["outcome"] == 1
    corrected = {**result, "score_90": [2, 0], "observation_id": "unit-corrected"}
    second = grade(p, corrected, "2026-10-27T00:00:00Z")
    assert second["grade"] == "win" and second["id"] != first["id"]
    assert p == original
    assert grade(p, {**result, "occurrence_id": "rescheduled"}, "2026-10-27T00:00:00Z")["grade"] == "void"
    assert grade(p, result, "2026-10-26T14:00:00Z") == grade(p, None, "2026-10-26T14:00:00Z")
    with pytest.raises(ValueError, match="probabilities"):
        grade({**p, "probabilities": [.8, .8, .8]}, result, "2026-10-27T00:00:00Z")


def test_imputation_uses_training_only_and_distinguishes_zero_from_missing():
    medians, values = impute_train([[0., None], [2., 4.], [4., 8.]])
    assert medians.tolist() == [2., 6.]
    assert values[0].tolist() == [0., 6., 0., 1.]
    outside = transform([[10000., None]], medians)
    assert outside[0].tolist() == [10000., 6., 0., 1.]
    assert np.all(np.isfinite(values))


def test_rich_training_stops_without_prospective_labels(tmp_path, monkeypatch):
    from ml.live import challengers
    monkeypatch.setattr(challengers, "ROOT", tmp_path)
    result = train(tmp_path/"empty-ledger")
    assert result["status"] == "insufficient_prospective_training_data"
    assert result["rows"] == 0 and not result["model_promoted"]
    assert not (tmp_path/"ml/models").exists()


def test_availability_deduplicates_and_rejects_wrong_team_or_incomplete_lineups():
    fixture = {"fixture_id": "unit-fixture", "home_provider_id": 1, "away_provider_id": 2}
    row = {"player": {"id": 11, "type": "Missing Fixture"}, "team": {"id": 1}}
    injury = {"id": "unit-inj", "fixture_id": "unit-fixture", "route": "/injuries", "available_at": "2026-10-26T09:00:00Z", "rows": [row, row]}
    result = context_for(fixture, [injury], [], "2026-10-26T10:00:00Z")
    assert result["availability"]["records"] == 1 and result["availability"]["duplicates_merged"] == 1
    wrong = {**injury, "rows": [{**row, "team": {"id": 999}}]}
    assert context_for(fixture, [wrong], [], "2026-10-26T10:00:00Z")["availability"]["records"] is None


def test_known_free_plan_denials_are_rejected_before_transport():
    validate_query("/fixtures", {"date": "2026-10-26", "timezone": "Asia/Bangkok"})
    for query in [{"ids": "1-2"}, {"league": 39, "season": 2026}, {"date": "2026-02-30"}]:
        with pytest.raises(ValueError):
            validate_query("/fixtures", query)


def test_challengers_fit_real_estimators_in_an_isolated_synthetic_test_fixture(tmp_path, monkeypatch):
    """Exercise the previously gated fit/save path; never publish these test metrics."""
    import hashlib
    import json
    from datetime import date, timedelta

    from ml.live import challengers
    rng = np.random.default_rng(42)
    rows = []
    for day in range(80):
        for match in range(20):
            x = rng.normal(size=66)
            target = int(np.argmax(x[:3]))
            when = (date(2026, 1, 1)+timedelta(days=day)).isoformat()
            rows.append({"fixture_id": f"synthetic-test-{day}-{match}", "date": when, "label_available_at": when+"T23:00:00Z", "features": x.tolist(), "rich_observed": True, "target": target, "baseline_probabilities": [1/3]*3})
    monkeypatch.setattr(challengers, "training_rows", lambda directory, asof: rows)
    monkeypatch.setattr(challengers, "ROOT", tmp_path)
    registry = tmp_path/"ml/models/precision-v3-registry.json"
    registry.parent.mkdir(parents=True)
    registry.write_text('{"candidate":"synthetic-test-reference"}', encoding="utf-8")
    report = train(tmp_path/"test-ledger")
    assert report["status"] == "evaluated_research_only"
    assert report["selected"] != "frozen_v3"
    assert report["split_counts"] == [960, 320, 320]
    assert report["test"]["log_loss"] < report["baseline_test"]["log_loss"]
    folder = tmp_path/"ml/models"/report["version"]
    for name, digest in report["checksums"].items():
        assert hashlib.sha256((folder/name).read_bytes()).hexdigest() == digest
    assert json.loads((folder/"training-manifest.json").read_text())["training_cutoff_exclusive"] == "2026-02-18"
    assert not report["model_promoted"] and not report["prospective_certified"]


def test_training_dataset_version_cannot_be_overwritten(tmp_path, monkeypatch):
    from ml.live import ledger
    monkeypatch.setattr(ledger, "ROOT", tmp_path)
    manifest = {"dataset_version": "unit-dataset"}
    ledger.save_manifest(manifest, tmp_path/"ledger", [{"id": "unit-record"}])
    assert manifest["accepted_training_rows"] == 1
    ledger.save_manifest(manifest, tmp_path/"ledger", [{"id": "unit-record"}])
    with pytest.raises(ValueError, match="immutable"):
        ledger.save_manifest(manifest, tmp_path/"ledger", [{"id": "different-record"}])
