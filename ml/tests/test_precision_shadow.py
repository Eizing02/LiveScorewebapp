from datetime import datetime, timezone

import pytest

from ml.precision_shadow import upcoming_records, write_once


def test_private_research_rejects_unknown_team_missing_timezone_and_late_matches():
    now = datetime(2026, 10, 26, tzinfo=timezone.utc)
    match = {"matchID": 1, "leagueSeason": 2026, "matchDateTimeUTC": "2026-10-27T18:00:00Z", "matchIsFinished": False, "team1": {"teamName": "Bayern München"}, "team2": {"teamName": "Borussia Dortmund"}}
    vocabulary = {"Bayern München", "Borussia Dortmund"}
    rows, held = upcoming_records([match], "de.1", vocabulary, now)
    assert len(rows) == 1 and not held
    assert rows[0]["kickoff_utc"].endswith("+00:00")
    assert rows[0]["source_verified"] is False
    assert "goals" not in rows[0]
    assert not upcoming_records([{**match, "matchDateTimeUTC": "2026-10-26T01:00:00Z"}], "de.1", vocabulary, now)[0]
    assert upcoming_records([{**match, "matchDateTimeUTC": "2026-10-27T18:00:00"}], "de.1", vocabulary, now)[1][0]["reason"] == "missing_timezone"
    assert upcoming_records([match], "de.1", {"Bayern München"}, now)[1][0]["reason"] == "unresolved_cross_source_team"


def test_prospective_record_is_immutable(tmp_path):
    path = tmp_path/"prediction.json"
    record = {"probability": .8, "target_score": None}
    write_once(path, record)
    write_once(path, record)
    with pytest.raises(ValueError, match="immutable"):
        write_once(path, {**record, "target_score": [1, 0]})
