import io
import json
from datetime import datetime, timezone

import pytest

from scripts.api_football_probe import Probe, ProbeError, account_summary, fixture_summary, league_summary, load_key, rate_headers, round_bounds


def test_key_file_is_read_without_execution_and_placeholder_rejected(tmp_path, monkeypatch):
    monkeypatch.delenv("API_FOOTBALL_KEY", raising=False)
    path = tmp_path/".dev.vars"
    path.write_text('API_FOOTBALL_KEY="unit-test-credential"\n', encoding="utf-8")
    assert load_key(path) == "unit-test-credential"
    path.write_text('API_FOOTBALL_KEY=REPLACE_LOCALLY\n', encoding="utf-8")
    with pytest.raises(ProbeError, match="missing_api_key"):
        load_key(path)


def test_status_redacts_account_identity_and_preserves_actual_limits():
    payload = {"response": {"account": {"email": "private@example.test", "firstname": "Private"}, "subscription": {"active": True, "plan": "Free"}, "requests": {"current": 5, "limit_day": 100}}}
    summary = account_summary(payload)
    assert summary["daily_remaining"] == 95
    assert "private" not in json.dumps(summary).lower()
    assert rate_headers({"X-RateLimit-Remaining": "4", "X-Ratelimit-Requests-Remaining": "94", "set-cookie": "private"}) == {"x-ratelimit-remaining": 4, "x-ratelimit-requests-remaining": 94}
    payload["response"]["requests"]["current"] = 101
    with pytest.raises(ProbeError, match="quota"):
        account_summary(payload)


def test_catalog_coverage_does_not_implicitly_approve_account_or_xg():
    payload = {"response": [{"league": {"id": 39, "name": "Premier League"}, "seasons": [{"year": 2026, "coverage": {"fixtures": {"lineups": True}}}]}]}
    summary = league_summary(payload, 39, 2026)
    assert summary["requested_season_listed"]
    assert summary["account_fixture_access"] == "unverified"
    assert "xg" not in summary["coverage"]
    with pytest.raises(ProbeError, match="identity"):
        league_summary(payload, 140, 2026)


def test_fixture_round_half_open_boundaries_duplicates_and_missing_goals():
    def row(identity, when):
        return {"fixture": {"id": identity, "date": when, "status": {"short": "NS"}}, "league": {"id": 39, "season": 2026}, "teams": {"home": {"id": 1, "name": "H"}, "away": {"id": 2, "name": "A"}}, "goals": {"home": None, "away": None}}
    first = row(1, "2026-10-25T23:00:00Z")
    payload = {"paging": {"total": 1}, "response": [first, first, row(2, "2026-10-26T22:59:59Z"), row(3, "2026-10-26T23:00:00Z")]}
    summary = fixture_summary(payload, 39, 2026, "2026-10-26")
    assert len(summary["fixtures"]) == 2
    assert summary["fixtures"][0]["goals"] == [None, None]
    assert summary["quarantined"][0]["reason"] == "duplicate_provider_fixture"
    assert round_bounds("2026-10-26")[0] == datetime(2026, 10, 25, 23, tzinfo=timezone.utc)


class Response(io.BytesIO):
    status = 200
    headers = {"x-ratelimit-requests-remaining": "90", "x-ratelimit-limit": "10"}


class Transport:
    def __init__(self, payload):
        self.payload, self.requests = payload, []

    def open(self, request, timeout):
        self.requests.append(request)
        return Response(json.dumps(self.payload).encode())


def test_transport_has_hard_budget_reserve_fixed_host_and_no_status_pii_on_disk(tmp_path):
    transport = Transport({"response": {"account": {"email": "private@example.test"}, "subscription": {"active": True, "plan": "Free"}, "requests": {"current": 10, "limit_day": 100}}, "errors": []})
    now = [100.]
    probe = Probe("secret-test", tmp_path, transport, lambda seconds: now.__setitem__(0, now[0]+seconds), lambda: now[0])
    probe.get("/status")
    assert not (tmp_path/"responses").exists()
    assert "private@example" not in probe.path.read_text(encoding="utf-8")
    assert transport.requests[0].full_url == "https://v3.football.api-sports.io/status"
    probe.remaining = 10
    with pytest.raises(ProbeError, match="reserve"):
        probe.get("/leagues", {"id": 39})
    with pytest.raises(ProbeError, match="allowlist"):
        probe.get("https://example.test")
    probe.calls = [{}]*7
    with pytest.raises(ProbeError, match="session_request_budget"):
        probe.get("/status")


def test_provider_error_never_logs_key_and_has_no_retry(tmp_path):
    transport = Transport({"errors": {"token": "secret-test"}, "response": []})
    probe = Probe("secret-test", tmp_path, transport, clock=lambda: 100.)
    with pytest.raises(ProbeError) as caught:
        probe.get("/status")
    assert "secret-test" not in str(caught.value)
    assert "secret-test" not in probe.path.read_text(encoding="utf-8")
    assert len(transport.requests) == 1
