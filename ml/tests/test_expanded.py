import hashlib
import json

import pytest

from ml.expanded import CONFIG, OUTPUT, map_name, merge_results, normalize_openliga
from ml.goal_markets import goal_markets
from ml.pipeline import ROOT, digest, normalize_score


def row(source="openfootball", day="2025-01-01", goals=None):
    return {"source": source, "source_record_id": source, "league": "en.1", "season": "2024-25", "home_id": "h", "away_id": "a", "date": day, "goals": goals or [1, 0], "provenance": [{"source": source}], "kickoff_utc": None}


def test_duplicate_evidence_not_extra_training_matches():
    accepted, held, duplicates = merge_results([row(), row("openligadb")])
    assert len(accepted) == 1 and not held and len(duplicates) == 1
    assert accepted[0]["cross_source_agreement"]
    assert len(accepted[0]["provenance"]) == 2


@pytest.mark.parametrize("other", [row("openligadb", goals=[2, 0]), row("openligadb", day="2025-01-02")])
def test_conflict_quarantines_both_without_inventing_correction(other):
    accepted, held, _ = merge_results([row(), other])
    assert not accepted and len(held) == 2
    assert held[0]["reason"].startswith("cross_source_")


def test_identity_mapping_requires_unique_exact_normalization():
    assert map_name("Bayern München", {"FC Bayern München"})[0] == "FC Bayern München"
    with pytest.raises(ValueError, match="unresolved"):
        map_name("United", {"Manchester United", "Newcastle United"})
    with pytest.raises(ValueError):
        map_name("FC Example", {"Example", "SC Example"})


def test_openliga_never_converts_missing_or_halftime_to_zero_zero():
    match = {"matchIsFinished": False}
    with pytest.raises(ValueError, match="unplayed"):
        normalize_openliga(match, "de.1", "2024-25", set(), {})
    match.update({"matchIsFinished": True, "matchResults": [{"resultTypeKind": "HalfTime", "pointsTeam1": 0, "pointsTeam2": 0}]})
    with pytest.raises(ValueError, match="90_minute"):
        normalize_openliga(match, "de.1", "2024-25", set(), {})
    assert normalize_score({}) == (None, "missing")
    assert normalize_score([0, 0])[0] == [0, 0]


def test_markets_have_mathematical_complements_and_monotone_lines():
    p = goal_markets(1.8, .9)
    assert p["over_2.5"] == pytest.approx(.506375508926538)
    assert p["btts_yes"] == pytest.approx(.4953369647775641)
    assert p["over_1.5"] > p["over_2.5"] > p["over_3.5"]
    for line in [1.5, 2.5, 3.5]:
        assert p[f"over_{line}"] + p[f"under_{line}"] == pytest.approx(1)
    assert p["btts_yes"] + p["btts_no"] == pytest.approx(1)


def test_explicit_provider_local_and_utc_times_must_agree():
    match = {"matchID": 1, "matchIsFinished": True, "matchResults": [{"resultTypeKind": "After90Minutes", "pointsTeam1": 1, "pointsTeam2": 0}], "team1": {"teamName": "Home"}, "team2": {"teamName": "Away"}, "matchDateTimeUTC": "2025-01-01T14:00:00Z", "matchDateTime": "2025-01-01T17:00:00", "timeZoneID": "W. Europe Standard Time", "group": {"groupOrderID": 1}}
    with pytest.raises(ValueError, match="source_local_utc_conflict"):
        normalize_openliga(match, "de.1", "2024-25", {"Home", "Away"}, {"sha256": "test", "url": "test"})
    match["matchDateTime"] = "2025-01-01T15:00:00"
    assert normalize_openliga(match, "de.1", "2024-25", {"Home", "Away"}, {"sha256": "test", "url": "test"})["kickoff_utc"] == "2025-01-01T14:00:00+00:00"


def test_actual_dataset_window_unique_ids_and_checksum():
    if not (OUTPUT / "accepted.jsonl").exists():
        pytest.skip("Run expanded importer for local dataset integration")
    rows = [json.loads(line) for line in (OUTPUT / "accepted.jsonl").read_text(encoding="utf-8").splitlines()]
    report = json.loads((OUTPUT / "quality-report.json").read_text(encoding="utf-8"))
    assert len(rows) == report["accepted"] == len({r["id"] for r in rows})
    assert all(CONFIG["window_start"] <= r["date"] < CONFIG["asof_exclusive"] for r in rows)
    assert [r["date"] for r in rows] == sorted(r["date"] for r in rows)
    assert all(isinstance(g, int) and g >= 0 for r in rows for g in r["goals"])
    assert digest(rows) == report["dataset_version"]
    assert all("2019-20" != r["season"] for r in rows)


def test_recent_artifact_checksums_and_no_promotion():
    registry_path = ROOT / "ml/models/recent-v2-registry.json"
    if not registry_path.exists():
        pytest.skip("Train recent models for artifact integration")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    assert registry["active_version"] is None and registry["auto_promote"] is False
    directory = ROOT / "ml/models" / registry["candidate"]
    meta = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    for name, checksum in meta["checksums"].items():
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == checksum
    assert meta["training_last_date"] < meta["training_cutoff_exclusive"]
