import json
from pathlib import Path

import pytest

from ml.pipeline import ROOT, deduplicate, digest, import_dataset, normalize_score, normalize_status, team_identity, validate_time


@pytest.mark.parametrize("value,expected", [({"ft": [0, 0]}, ([0, 0], "ft_object")), ([0, 0], ([0, 0], "numeric_array")), ([2, 1], ([2, 1], "numeric_array")), ({}, (None, "missing")), (None, (None, "missing"))])
def test_score_schemas_and_missing(value, expected):
    assert normalize_score(value) == expected


@pytest.mark.parametrize("value", [[True, 0], [-1, 2], [1.5, 0], [0], {"ft": ["1", 0]}])
def test_invalid_score(value):
    with pytest.raises(ValueError):
        normalize_score(value)


def test_time_not_invented_and_explicit_offset():
    assert validate_time("2025-08-01", "15:00")["kickoff_utc"] is None
    assert validate_time("2025-08-01", "15:00 UTC+1")["kickoff_utc"] == "2025-08-01T14:00:00+00:00"
    with pytest.raises(ValueError):
        validate_time("2025-02-30", None)


def test_alias_and_placeholder():
    assert team_identity("en.1", "Manchester City") == team_identity("en.1", "Manchester City FC")
    assert team_identity("es.1", "Real Madrid") == team_identity("es.1", "Real Madrid CF")
    with pytest.raises(ValueError):
        team_identity("en.1", "N.N.")
    assert normalize_status("canceled") == "cancelled"
    assert normalize_status("awarded") == "awarded"
    assert normalize_status("anything_else") == "unverified"


def test_duplicate_and_conflicting_results():
    a = {"league": "en.1", "season": "2020-21", "home_id": "h", "away_id": "a", "date": "2020-10-01", "goals": [1, 0], "status": "result_recorded", "source_index": 1, "source_record_id": "a"}
    b = {**a, "source_index": 2, "source_record_id": "b"}
    kept, removed = deduplicate([a, b])
    assert len(kept) == len(removed) == 1
    assert removed[0]["reason"] == "duplicate_merged"
    kept, removed = deduplicate([a, {**b, "goals": [0, 0]}])
    assert not kept and len(removed) == 2


@pytest.fixture(scope="session")
def actual_pipeline(tmp_path_factory):
    return import_dataset(ROOT / "data/source/openfootball", tmp_path_factory.mktemp("pipeline"))


def test_full_pinned_snapshot_reconciles_and_quarantines(actual_pipeline):
    r = actual_pipeline
    assert r["total_source_rows"] == 97082
    assert r["quarantine_reasons"]["epl_2019_20_misdated_66"] == 66
    assert r["quarantine_reasons"]["season_chronology_hold"] == 314
    assert r["quarantine_reasons"]["duplicate_merged"] == 12
    assert r["accepted"] + r["quarantined"] + r["excluded"] == r["total_source_rows"]
    assert r["accepted"] > 15000
    assert r["corrections_applied"] == 0


def test_repeat_ingestion_dataset_hash(actual_pipeline, tmp_path):
    other = import_dataset(ROOT / "data/source/openfootball", tmp_path)
    assert other["dataset_version"] == actual_pipeline["dataset_version"]
    rows = [json.loads(line) for line in (Path(tmp_path) / "accepted.jsonl").read_text(encoding="utf-8").splitlines()]
    assert digest(rows) == other["dataset_version"]
    assert all(r["kickoff_utc"] is None and r["timezone_status"] == "unverified" for r in rows)
    assert not any(r["season"] == "2019-20" and r["league"] == "en.1" for r in rows)
