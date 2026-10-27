import copy
import json

import numpy as np
import pytest

from ml.live.context import context_for
from ml.live.ledger import accepted_history, latest_observations, write_once
from ml.live.normalize import business_date, mapping_config, normalize_fixture, score_pair
from ml.live.predict import LivePrecisionEngine
from ml.pipeline import ROOT


def raw_fixture(status="NS", day="2026-10-28T12:00:00Z"):
    from ml.live.normalize import moment
    return {"fixture": {"id": 999001, "date": day, "timestamp": int(moment(day).timestamp()), "status": {"short": status}}, "league": {"id": 39, "country": "England", "season": 2026}, "teams": {"home": {"id": 40, "name": "Liverpool"}, "away": {"id": 51, "name": "Brighton"}}, "goals": {"home": None, "away": None}, "score": {"fulltime": {"home": None, "away": None}}}


def test_business_round_and_mapping_have_explicit_evidence():
    assert business_date("2026-10-26T22:59:59Z") == "2026-10-26"
    assert business_date("2026-10-26T23:00:00Z") == "2026-10-27"
    row = normalize_fixture(raw_fixture(), "2026-10-27T12:00:00Z", "source-test")
    assert row["mapping_status"] == "reviewed"
    assert row["provider_identity_independently_verified"] is False
    assert row["score_90"] is None and not row["quarantine_reasons"]
    changed = raw_fixture()
    changed["teams"]["home"]["name"] = "Liverpool Youth"
    assert "identity_mapping_pending" in normalize_fixture(changed, "2026-10-27T12:00:00Z", "test")["quarantine_reasons"]
    assert len(mapping_config()["teams"]) >= 32


def test_missing_and_90_minute_scores_are_not_zero_or_penalty_wins():
    raw = raw_fixture("FT", "2026-10-25T12:00:00Z")
    assert "missing_or_conflicting_fulltime_score" in normalize_fixture(raw, "2026-10-26T12:00:00Z", "test")["quarantine_reasons"]
    raw["fixture"]["status"]["short"] = "PEN"
    raw["score"] = {"fulltime": {"home": 1, "away": 1}, "penalty": {"home": 5, "away": 4}}
    raw["goals"] = {"home": 1, "away": 1}
    row = normalize_fixture(raw, "2026-10-26T12:00:00Z", "test")
    assert row["score_90"] == [1, 1] and row["score_penalties"] == [5, 4]
    with pytest.raises(ValueError):
        score_pair({"home": True, "away": 0})
    raw["fixture"]["timestamp"] += 120
    with pytest.raises(ValueError, match="timestamp"):
        normalize_fixture(raw, "2026-10-26T12:00:00Z", "test")


def test_append_ledger_deduplicates_conflicts_and_respects_availability(tmp_path):
    raw = raw_fixture("FT", "2026-10-25T12:00:00Z")
    raw["score"]["fulltime"] = raw["goals"] = {"home": 2, "away": 1}
    row = normalize_fixture(raw, "2026-10-25T15:00:00Z", "test")
    before = latest_observations([row], "2026-10-25T14:00:00Z")
    assert before == []
    base = [{"id": "original", "league": row["league"], "season": row["season"], "date": row["date"], "home_id": row["home_id"], "away_id": row["away_id"], "goals": [2, 1]}]
    accepted, manifest = accepted_history([row], "2026-10-26T12:00:00Z", base)
    assert len(accepted) == 1 and manifest["duplicates_agreed"] == 1
    changed = copy.deepcopy(row)
    changed["score_90"] = [0, 3]
    accepted, manifest = accepted_history([changed], "2026-10-26T12:00:00Z", base)
    assert accepted[0]["goals"] == [2, 1] and len(manifest["conflicts"]) == 1
    write_once(tmp_path, "observations", row)
    write_once(tmp_path, "observations", row)
    assert len(list((tmp_path/"observations").glob("*.json"))) == 1


def test_fresh_feature_cutoff_updates_state_without_retraining_or_future_leakage():
    registry = ROOT/"ml/models/precision-v3-registry.json"
    if not registry.exists():
        pytest.skip("precision artifact not built")
    source = [json.loads(line) for line in (ROOT/"data/processed/recent-v2/accepted.jsonl").read_text(encoding="utf-8").splitlines()]
    fixture = normalize_fixture(raw_fixture(), "2026-10-27T12:00:00Z", "unit-only")
    added = {"id": "unit-test-only-result", "league": fixture["league"], "season": fixture["season"], "date": "2026-10-26", "home_id": fixture["home_id"], "away_id": fixture["away_id"], "goals": [4, 0], "available_at": "2026-10-27T01:00:00Z"}
    one = LivePrecisionEngine(source, "2026-10-27T12:00:00Z", "unit")
    two = LivePrecisionEngine(source+[added], "2026-10-27T12:00:00Z", "unit")
    before, _ = one.snapshot(fixture, "2026-10-27")
    after, _ = two.snapshot(fixture, "2026-10-27")
    assert after["history_matches"] == before["history_matches"]+1
    assert not np.allclose(before["features"], after["features"])
    future = {**added, "available_at": "2026-10-28T01:00:00Z"}
    three = LivePrecisionEngine(source+[future], "2026-10-27T12:00:00Z", "unit")
    blocked, _ = three.snapshot(fixture, "2026-10-27")
    assert np.allclose(before["features"], blocked["features"])
    snapshot, feature = two.predict_live(fixture)
    assert snapshot["training_cutoff"] == one.meta["training_cutoff_exclusive"]
    assert snapshot["feature_information_cutoff_exclusive"] == "2026-10-27"
    assert sum(snapshot["probabilities"]) == pytest.approx(1)
    assert len(feature["values"]) == 58
    with pytest.raises(ValueError, match="kickoff"):
        LivePrecisionEngine(source, "2026-10-29T12:00:00Z", "unit").predict_live(fixture)


def test_api_context_excludes_target_statistics_and_late_reports():
    fixture = normalize_fixture(raw_fixture(), "2026-10-27T12:00:00Z", "test")
    injury = {"id": "test", "fixture_id": fixture["fixture_id"], "route": "/injuries", "available_at": "2026-10-29T12:00:00Z", "rows": [{"player": {"id": 1, "type": "Missing Fixture"}, "team": {"id": 40}}]}
    ctx = context_for(fixture, [injury], [], "2026-10-27T12:00:00Z")
    assert ctx["availability"]["records"] is None
    assert ctx["past_xg"]["home"]["xg_for_mean"] is None
    assert not ctx["lineups"]["confirmed"]
    assert ctx["target_match_statistics_excluded"]
