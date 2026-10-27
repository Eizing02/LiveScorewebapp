import copy

import numpy as np
import pytest
from scipy.stats import skellam

from ml.evaluate import metric_values, train_challengers
from ml.models import LeagueState, elo_probabilities, poisson_prediction, replay
from ml.pipeline import digest
from ml.features import build_features


def fixture(i, day, goals=(1, 0), home="h", away="a"):
    return {"id": str(i), "date": day, "league": "en.1", "season": "2020-21", "home_id": home, "away_id": away, "goals": list(goals)}


def test_poisson_independent_reference_and_symmetry():
    p = poisson_prediction(1.5, 1.2)["probabilities"]
    assert p == pytest.approx([1 - skellam.cdf(0, 1.5, 1.2), skellam.pmf(0, 1.5, 1.2), skellam.cdf(-1, 1.5, 1.2)], abs=1e-10)
    for h, a in [(0.15, 0.15), (5, 5), (1.2, 2), (4, 0.4)]:
        r = poisson_prediction(h, a)
        assert sum(r["probabilities"]) == pytest.approx(1, abs=1e-12)
        assert min(r["probabilities"]) >= 0
    assert elo_probabilities(200)[0] > elo_probabilities(-200)[0]


def test_future_target_and_same_day_results_do_not_change_features():
    rows = [fixture(1, "2020-08-01"), fixture(2, "2020-08-02"), fixture(3, "2020-08-02", home="c", away="d"), fixture(4, "2020-08-03")]
    original, _ = replay(rows)
    changed = copy.deepcopy(rows)
    changed[1]["goals"] = [9, 0]
    changed[3]["goals"] = [0, 9]
    after, _ = replay(changed)
    for before, new in zip(original, after):
        if before["date"] <= "2020-08-02":
            assert before["features"] == new["features"]
    assert all(r["information_cutoff_date"] is None or r["information_cutoff_date"] < r["date"] for r in after)
    prefix, _ = replay(rows[:3])
    assert digest(prefix) == digest(original[:3])


def test_order_cold_start_and_serialization():
    state = LeagueState()
    match = fixture(1, "2020-08-01")
    snapshot = state.snapshot(match)
    assert snapshot["cold_start"] and snapshot["features"][7:9] == [0, 0]
    state.update_batch([match])
    with pytest.raises(ValueError):
        state.snapshot(match)
    with pytest.raises(ValueError):
        state.update_batch([match])
    restored = LeagueState.from_dict(state.to_dict())
    assert restored.snapshot(fixture(2, "2020-08-02")) == state.snapshot(fixture(2, "2020-08-02"))
    rating = state.elo["h"]
    state.start_season("2020-21")
    state.start_season("2021-22")
    assert state.elo["h"] == pytest.approx(1500 + (rating - 1500) * 0.75)


def test_metrics_reference_and_invalid_probability():
    m, _ = metric_values([0, 1, 2], [[1/3]*3]*3)
    assert m["log_loss"] == pytest.approx(np.log(3))
    assert m["brier"] == pytest.approx(2/3)
    assert m["accuracy"] == pytest.approx(1/3)
    with pytest.raises(ValueError):
        metric_values([0], [[0.5, 0.5, 0.5]])


def test_challengers_reproducible():
    rng = np.random.default_rng(10)
    rows = [{"features": x.tolist(), "target": i % 3} for i, x in enumerate(rng.normal(size=(120, 11)))]
    first, second = train_challengers(rows), train_challengers(rows)
    x = np.array([r["features"] for r in rows])
    for name in first:
        assert np.array_equal(first[name].predict_proba(x), second[name].predict_proba(x))


def test_build_features_training_inference_parity():
    history = [fixture(1, "2020-08-01"), fixture(2, "2020-08-02"), fixture(3, "2020-08-03")]
    snapshots, _ = replay(history)
    assert build_features("2020-08-03", history[-1], history)["features"] == snapshots[-1]["features"]
    changed = history + [fixture(4, "2020-08-04", goals=(10, 0))]
    assert build_features("2020-08-03", history[-1], changed)["features"] == snapshots[-1]["features"]
