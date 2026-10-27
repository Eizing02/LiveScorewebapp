import copy
import json
from datetime import date, timedelta

import numpy as np
import pytest

from ml.enrichment import eligible_snapshot, injury_summary
from ml.pipeline import ROOT
from ml.precision.calibration import fit_platt, fit_temperature, temperature_transform
from ml.precision.features import CACHE, FEATURES, team_features
from ml.precision.goals import DixonColes
from ml.precision.selection import history_reasons, select


def synthetic_matches():
    rng = np.random.default_rng(123)
    strengths = {"strong": .5, "middle": .0, "weak": -.4}
    teams = list(strengths)
    rows = []
    for i in range(100):
        home, away = teams[i % 3], teams[(i+1+i//3 % 2) % 3]
        if home == away:
            away = teams[(teams.index(home)+1) % 3]
        h = int(rng.poisson(np.exp(.3+.2+strengths[home]-strengths[away])))
        a = int(rng.poisson(np.exp(.3+strengths[away]-strengths[home])))
        rows.append({"date": (date(2024, 1, 1)+timedelta(days=i)).isoformat(), "home_id": home, "away_id": away, "goals": [h, a]})
    return rows


def test_opponent_adjusted_model_serializes_and_reproduces():
    rows = synthetic_matches()
    one = DixonColes().fit(rows, "2024-06-01")
    two = DixonColes().fit(rows, "2024-06-01")
    assert np.allclose(one.theta, two.theta, atol=1e-10)
    p = one.predict("strong", "weak", "2024-06-02")
    assert p["probabilities"][0] > p["probabilities"][2]
    assert sum(p["probabilities"]) == pytest.approx(1)
    assert p["markets"]["over_1.5"] >= p["markets"]["over_2.5"] >= p["markets"]["over_3.5"]
    assert p["markets"]["btts_yes"] <= p["markets"]["over_1.5"]
    restored = DixonColes.from_dict(one.to_dict())
    assert restored.predict("strong", "weak", "2024-06-02") == p


def test_goal_training_and_prediction_reject_future_information():
    rows = synthetic_matches()
    with pytest.raises(ValueError, match="future"):
        DixonColes().fit(rows, rows[-1]["date"])
    model = DixonColes().fit(rows, "2024-06-01")
    with pytest.raises(ValueError, match="future"):
        model.predict("strong", "weak", "2024-02-01")


def test_temporal_calibration_never_uses_current_season_labels():
    p = np.tile([.75, .15, .1], (300, 1))
    y = np.arange(300) % 3
    dates = ["2023-01-01"]*300
    t = fit_temperature(p, y, dates, "2023-07-01")
    q = temperature_transform(p, t)
    assert np.allclose(q.sum(axis=1), 1)
    assert np.array_equal(q.argmax(axis=1), p.argmax(axis=1))
    with pytest.raises(ValueError, match="temporal"):
        fit_temperature(p, y, ["2024-07-01"]*300, "2024-07-01")
    with pytest.raises(ValueError, match="temporal"):
        fit_platt([.7]*300, [1]*300, ["2024-07-01"]*300, "2024-07-01")


def test_selection_uses_no_target_or_target_match_score():
    row = {"date": "2025-01-01", "cutoff_date": "2024-12-28", "league": "en.1", "history_matches": 100, "context": {"venue": [20, 20], "last365": [30, 30], "season_matches": [15, 15], "gaps": [4, 4]}, "target": 0, "goals": [1, 0]}
    changed = copy.deepcopy(row)
    changed.update({"target": 2, "goals": [0, 9]})
    assert np.array_equal(select([row], [[.8, .1, .1]], .75, "standard_history"), select([changed], [[.8, .1, .1]], .75, "standard_history"))
    changed["cutoff_date"] = changed["date"]
    assert "invalid_feature_cutoff" in history_reasons(changed, "standard_history")


def test_missing_enrichment_is_unknown_and_target_statistics_are_rejected():
    assert injury_summary(None)["count"] is None
    assert injury_summary([])["count"] is None
    assert injury_summary([], coverage_verified=True)["count"] == 0
    snap = {"license_permits_use": True, "coverage_verified": True, "kind": "xg", "fixture_id": "target", "first_seen_at": "2026-10-26T12:00:00Z", "available_at": "2026-10-26T12:00:00Z", "match_ended_at": "2026-10-26T13:00:00Z"}
    passed, reasons = eligible_snapshot(snap, "target", "2026-10-26T11:00:00Z", "2026-10-26T12:30:00Z")
    assert not passed and "target_match_post_kickoff_statistics" in reasons
    snap.update({"fixture_id": "previous", "first_seen_at": "2026-10-25T12:00:00Z", "available_at": "2026-10-25T12:00:00Z", "match_ended_at": "2026-10-25T11:00:00Z"})
    assert eligible_snapshot(snap, "target", "2026-10-26T11:00:00Z", "2026-10-26T12:30:00Z")[0]


def test_actual_feature_cache_is_finite_and_strictly_past():
    if not (CACHE/"features.jsonl").exists():
        pytest.skip("Build precision features for integration")
    rows = [json.loads(line) for line in (CACHE/"features.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(FEATURES) == 58
    assert all(len(r["features"]) == 58 and np.all(np.isfinite(r["features"])) for r in rows)
    assert all(r["cutoff_date"] < r["date"] for r in rows)
    assert all(not p["training_last_date"] or p["training_last_date"] < r["date"] for r in rows for p in r["dc"].values())


def test_forward_feature_parity_and_no_fake_scores():
    registry = ROOT/"ml/models/precision-v3-registry.json"
    if not registry.exists():
        pytest.skip("Train precision models for forward parity")
    from ml.precision_predict import PrecisionEngine
    engine = PrecisionEngine()
    rows = [json.loads(line) for line in (CACHE/"features.jsonl").read_text(encoding="utf-8").splitlines()]
    # Current-month fitted strengths were trained before this target date.
    target = next(r for r in reversed(rows) if r["league"] == "de.1" and r["date"] >= "2026-10-01")
    fixture = {k: target[k] for k in ["id", "league", "date", "season", "home_id", "away_id"]}
    snapshot, _ = engine.snapshot(fixture, target["date"])
    assert np.allclose(snapshot["features"], target["features"], atol=1e-10)
    assert "goals" not in snapshot
    altered = {**fixture, "goals": [99, 99], "target": 2}
    other, _ = engine.snapshot(altered, target["date"])
    assert np.allclose(snapshot["features"], other["features"], atol=1e-12)


def test_small_team_history_shrinks_to_prior_instead_of_invented_results():
    values = team_features([], "2026-10-26", "2026-27", 1.4, 1.35)
    assert values[0] == pytest.approx(1.35)
    assert values[3] == pytest.approx(1.4)
    assert values[-1] == 0
