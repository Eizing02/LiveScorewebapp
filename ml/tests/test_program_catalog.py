import copy
import hashlib
import json

import pytest

from ml.program_catalog import build, normalize


def fixture():
    return {"fixture": {"id": 9001, "date": "2026-10-28T00:30:00+07:00", "status": {"short": "NS"}}, "league": {"id": 143, "name": "Copa del Rey", "country": "Spain", "season": 2026}, "teams": {"home": {"id": 1, "name": "Unit Home"}, "away": {"id": 2, "name": "Unit Away"}}, "goals": {"home": None, "away": None}, "score": {"fulltime": {"home": None, "away": None}}}


def test_other_competitions_and_missing_scores_are_displayable_not_training():
    value = normalize(fixture(), "2026-10-27T08:00:00Z", "2026-10-28", "a"*64)
    assert value["league_id"] == "provider-143"
    assert value["business_date"] == "2026-10-27"
    assert value["current_score"] is None and value["score_90"] is None
    assert value["analysis"] is None and not value["model_supported"]
    assert value["quality"] == "display_only_not_training"


def test_date_boundary_status_and_invalid_identity():
    raw = fixture()
    raw["fixture"]["date"] = "2026-10-28T06:00:00+07:00"
    assert normalize(raw, "2026-10-27T08:00:00Z", "2026-10-28", "a"*64)["business_date"] == "2026-10-28"
    raw["fixture"]["status"]["short"] = "PST"
    assert normalize(raw, "2026-10-27T08:00:00Z", "2026-10-28", "a"*64)["status"] == "postponed"
    raw["teams"]["away"]["id"] = raw["teams"]["home"]["id"]
    with pytest.raises(ValueError, match="same_team"):
        normalize(raw, "2026-10-27T08:00:00Z", "2026-10-28", "a"*64)


def test_reproducible_cache_import_keeps_corrections_without_training(tmp_path):
    source = tmp_path / "source"
    (source / "responses").mkdir(parents=True)
    ledger = []
    for n in range(2):
        row = copy.deepcopy(fixture())
        row["fixture"]["date"] = f"2026-10-{28+n}T00:30:00+07:00"
        raw = json.dumps({"response": [row, row], "errors": [], "paging": {"total": 1}}).encode()
        digest = hashlib.sha256(raw).hexdigest()
        (source / "responses" / (digest + ".json")).write_bytes(raw)
        ledger.append({"route": f"/fixtures?date=2026-10-{28+n}", "first_seen_at": f"2026-10-27T0{8+n}:00:00Z", "response_sha256": digest})
    (source / "request-ledger.json").write_text(json.dumps(ledger))
    first = build(source, tmp_path / "one", "2026-10-27T10:00:00Z")
    second = build(source, tmp_path / "two", "2026-10-27T10:00:00Z")
    assert first == second
    assert first["observations"] == 2 and first["unique_fixtures"] == 1
    assert first["training_labels_added"] == first["provider_requests"] == 0
    assert (tmp_path / "one/import-batches.json").read_bytes() == (tmp_path / "two/import-batches.json").read_bytes()
    assert build(source, tmp_path / "past", "2026-10-27T08:30:00Z")["observations"] == 1
    (source / "responses" / (ledger[0]["response_sha256"] + ".json")).write_text("{}")
    with pytest.raises(ValueError, match="checksum"):
        build(source, tmp_path / "broken", "2026-10-27T10:00:00Z")
