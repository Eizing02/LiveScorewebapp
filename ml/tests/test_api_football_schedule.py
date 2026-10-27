import json

from scripts import api_football_schedule as schedule
from scripts.api_football_probe import ProbeError


class ProbeFixture:
    key = "fake-test-key"

    def __init__(self, fail=False):
        self.calls, self.remaining, self.fail = [], None, fail

    def get(self, route, query=None):
        self.calls.append({"route": route, "budgeted_billable": route != "/status"})
        if route == "/status":
            return {"response": {"subscription": {"plan": "Free", "active": True}, "requests": {"current": 7, "limit_day": 100}}}
        if self.fail:
            raise ProbeError("provider_http_429")
        self.remaining -= 1
        return {"paging": {"total": 1}, "response": []}


def test_schedule_dry_run_uses_no_transport_and_success_has_two_dates(tmp_path, monkeypatch):
    monkeypatch.setattr(schedule, "ROOT", tmp_path)
    probe = ProbeFixture()
    assert schedule.collect(False, "2026-10-26", probe)["status"] == "dry_run"
    assert not probe.calls
    result = schedule.collect(True, "2026-10-26", probe)
    assert len(probe.calls) == 3
    assert result["round_start_utc"] == "2026-10-25T23:00:00+00:00"
    assert [d["requested_date"] for d in result["days"]] == ["2026-10-26", "2026-10-27"]
    assert result["remaining_conservative"] == 91
    assert result["target_fixtures_in_business_round"] == 0


def test_failed_refresh_keeps_last_good_snapshot_and_does_not_retry(tmp_path, monkeypatch):
    monkeypatch.setattr(schedule, "ROOT", tmp_path)
    path = tmp_path/"reports/api-football/date-smoke-test.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"last_good":true}', encoding="utf-8")
    probe = ProbeFixture(fail=True)
    result = schedule.collect(True, "2026-10-26", probe)
    assert result["status"] == "blocked"
    assert len(probe.calls) == 2
    assert json.loads(path.read_text(encoding="utf-8")) == {"last_good": True}
    assert path.with_name("schedule-last-failure.json").exists()
