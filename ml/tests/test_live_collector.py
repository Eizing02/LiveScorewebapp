import json

import pytest

from ml.provider_broker import BrokerClient, NoRedirect
from scripts.collect_live_context import tasks_for


def fixture(**changes):
    return {"fixture_id": "unit-fixture", "provider_fixture_id": 901, "home_provider_id": 1, "away_provider_id": 2, "kickoff_utc": "2026-10-26T12:00:00Z", "mapping_status": "reviewed", "quarantine_reasons": [], "status": "scheduled", **changes}


def enrichment(when, rows=None):
    return {"fixture_id": "unit-fixture", "route": "/fixtures/lineups", "available_at": when, "rows": rows or []}


def test_lineups_have_a_bounded_retry_window_and_require_the_right_teams():
    upcoming = fixture()
    early = tasks_for([upcoming], [], "2026-10-26T11:00:00Z")
    assert {t["route"] for t in early} == {"/injuries", "/predictions"}
    at_window = tasks_for([upcoming], [], "2026-10-26T11:30:00Z")
    assert at_window[0]["route"] == "/fixtures/lineups"
    first = enrichment("2026-10-26T11:29:00Z")
    assert "/fixtures/lineups" not in {t["route"] for t in tasks_for([upcoming], [first], "2026-10-26T11:30:00Z")}
    second = enrichment("2026-10-26T11:45:00Z")
    assert "/fixtures/lineups" in {t["route"] for t in tasks_for([upcoming], [first], "2026-10-26T11:45:00Z")}
    assert "/fixtures/lineups" not in {t["route"] for t in tasks_for([upcoming], [first, second], "2026-10-26T11:58:00Z")}
    wrong_teams = enrichment("2026-10-26T11:20:00Z", [{"team": {"id": 7}, "startXI": [None]*11}, {"team": {"id": 8}, "startXI": [None]*11}])
    assert tasks_for([upcoming], [wrong_teams], "2026-10-26T11:40:00Z")[0]["route"] == "/fixtures/lineups"


def test_started_unreviewed_and_quarantined_fixtures_never_get_prematch_requests():
    for f in [fixture(status="live"), fixture(mapping_status="unverified"), fixture(quarantine_reasons=["invalid_score"])]:
        assert tasks_for([f], [], "2026-10-26T11:30:00Z") == []
    assert tasks_for([fixture()], [], "2026-10-26T11:58:01Z") == []
    finished = fixture(status="finished")
    assert tasks_for([finished], [], "2026-10-26T16:00:00Z") == []
    assert {t["route"] for t in tasks_for([finished], [], "2026-10-26T16:00:00Z", True)} == {"/fixtures/statistics", "/fixtures/players"}


def test_signed_broker_never_transmits_provider_key_or_follows_redirects():
    settings = {"PROVIDER_BROKER_URL": "http://127.0.0.1:8787", "INTERNAL_SYNC_SECRET": "unit-secret-"*4, "API_FOOTBALL_KEY": "provider-test-secret"}
    client = BrokerClient(settings)
    class Opener:
        def open(self, request, timeout):
            import io
            assert request.full_url == "http://127.0.0.1:8787/internal/provider-quota/reserve"
            serialized = json.dumps(dict(request.header_items()))+request.data.decode()
            assert "provider-test-secret" not in serialized
            assert "unit-secret-" not in serialized
            assert request.get_header("X-signature")
            return io.BytesIO(b'{"id":"ticket"}')
    client.opener = Opener()
    assert client.reserve("/status") == {"id": "ticket"}
    with pytest.raises(ValueError, match="redirect"):
        NoRedirect().redirect_request(None, None, 302, None, {}, "https://other.test")
    with pytest.raises(ValueError, match="origin"):
        BrokerClient({**settings, "PROVIDER_BROKER_URL": "https://example.test/unexpected-path"})
