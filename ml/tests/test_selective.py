import copy
from datetime import datetime, timezone

import numpy as np
import pytest

from ml.selective import history_reasons, live_rejection_reasons, prior_context, qualification, select_one, temperature_probabilities, wilson_interval


def test_selector_abstains_on_missing_or_invalid_information():
    models = {"elo": [.7, .2, .1], "poisson": [.8, .1, .1]}
    stress = np.array([[.72, .18, .1]] * 4)
    assert select_one([.8, .1, .1], models, [], stress, "robust", .75)["selected"]
    assert not select_one([.8, .1, .1], models, ["sparse"], stress, "history", .75)["selected"]
    assert not select_one([float("nan"), .1, .1], models, [], stress, "probability", .75)["selected"]
    assert not select_one([.8, .1, .1], {}, [], stress, "consensus", .75)["selected"]
    assert not select_one([.8, .1, .1], models, [], [], "robust", .75)["selected"]
    stress[0] = [.45, .5, .05]
    assert not select_one([.8, .1, .1], models, [], stress, "robust", .75)["selected"]


def test_model_agreement_is_a_separate_measured_condition():
    models = {"elo": [.2, .3, .5], "poisson": [.8, .1, .1]}
    decision = select_one([.8, .1, .1], models, [], [], "consensus", .75)
    assert decision["reasons"] == ["elo_disagrees"]
    # At >=75%, a margin of >=50 percentage points is already implied by probability sum=1.
    assert .75 - max(.2, .05) >= .5


def test_temperature_preserves_argmax_and_probability_sum():
    p = np.array([[.8, .1, .1], [.2, .3, .5]])
    for t in [.5, 1, 2.5, 3]:
        result = temperature_probabilities(p, t)
        assert np.array_equal(result.argmax(axis=1), p.argmax(axis=1))
        assert np.allclose(result.sum(axis=1), 1)
    with pytest.raises(ValueError):
        temperature_probabilities(p, 0)


def test_context_uses_only_prior_dates_and_not_target_scores():
    matches = [{"id": str(i), "date": day, "league": "en.1", "season": "2025-26", "home_id": "h", "away_id": "a", "goals": [1, 0]} for i, day in enumerate(["2025-08-01", "2025-08-02", "2025-08-02", "2025-08-03"])]
    context = prior_context(matches)
    assert context["1"]["home"]["season_matches"] == 1
    assert context["2"]["home"]["season_matches"] == 1
    changed = copy.deepcopy(matches)
    for match in changed:
        match["goals"] = [0, 99]
    changed.append({**matches[-1], "id": "future", "date": "2025-08-10"})
    later = prior_context(changed)
    assert all(context[key] == later[key] for key in context)
    assert history_reasons({"features": []}, {}) == ["incomplete_or_invalid_history_context"]


def test_small_samples_do_not_pass_from_perfect_accuracy():
    summary = {"n": 10, "coverage": .01, "accuracy": 1, "wilson95": wilson_interval(10, 10), "date_cluster95": [1, 1], "absolute_calibration_gap": .01, "per_league": {"en.1": {"n": 10}, "es.1": {"n": 0}, "de.1": {"n": 0}}}
    failed = qualification(summary, [{"n": 5, "accuracy": 1}] * 2)
    assert "too_few_validation_samples" in failed
    assert "league_support_too_small" in failed
    assert "fold_support_too_small" in failed


def test_live_gates_fail_closed_without_verified_fresh_data():
    now = datetime(2026, 10, 25, 12, tzinfo=timezone.utc)
    assert live_rejection_reasons({}, now)
    evidence = {"kickoff_verified": True, "team_mapping_verified": True, "provider_coverage_verified": True, "feature_cutoff_verified": True, "model_approved": True, "is_mock": False, "fixture_status": "scheduled", "fixture_feed_fetched_at": "2026-10-25T11:00:00Z", "results_feed_fetched_at": "2026-10-25T10:00:00Z", "kickoff_utc": "2026-10-25T18:00:00Z", "information_cutoff_utc": "2026-10-25T11:00:00Z"}
    assert live_rejection_reasons(evidence, now) == []
    evidence["is_mock"] = True
    assert "mock_or_unknown_source" in live_rejection_reasons(evidence, now)
    evidence["results_feed_fetched_at"] = "2026-10-20T10:00:00Z"
    assert "results_feed_fetched_at_stale_or_future" in live_rejection_reasons(evidence, now)
