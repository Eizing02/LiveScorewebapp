"""Refresh a local 06:00 Bangkok schedule through the verified date endpoint.

Explicit execution: at most one non-billable status call and two date requests.
Never invokes model inference or enables scheduled/production integration.
"""
import argparse
import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from ml.pipeline import ROOT, write_json
from scripts.api_football_probe import LEAGUES, ManagedProbe, Probe, ProbeError, account_summary, fixture_summary, load_key, round_bounds


def collect(execute=False, day=None, probe=None):
    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    day = day or (now-timedelta(hours=6)).date().isoformat()
    start, end = round_bounds(day)
    season = start.astimezone(ZoneInfo("Asia/Bangkok")).year
    if start.astimezone(ZoneInfo("Asia/Bangkok")).month < 7:
        season -= 1
    report = {"purpose": "documented_date_filter_connectivity_test", "business_date": day, "round_start_utc": start.isoformat(), "round_end_exclusive_utc": end.isoformat(), "model_promoted": False, "production_deployed": False, "worker_live_enabled": False, "days": [], "status": "dry_run", "maximum_http_requests": 3, "maximum_billable_requests": 2, "minimum_daily_reserve": 10, "automatic_retries": 0}
    if not execute:
        return report
    try:
        if probe is None:
            from ml.provider_broker import local_settings
            factory = ManagedProbe if local_settings().get("PROVIDER_BROKER_ENABLED") == "true" else Probe
            probe = factory(load_key())
        account = account_summary(probe.get("/status"))
        if not account["active"] or account["plan"].lower() != "free":
            raise ProbeError("active_free_plan_required")
        probe.remaining = min(probe.remaining, account["daily_remaining"]) if probe.remaining is not None else account["daily_remaining"]
        if probe.remaining < 12:
            raise ProbeError("two_calls_plus_ten_reserve_required")
        for date in [day, (datetime.fromisoformat(day)+timedelta(days=1)).date().isoformat()]:
            payload = probe.get("/fixtures", {"date": date, "timezone": "Asia/Bangkok"})
            if payload.get("paging", {}).get("total") != 1 or not isinstance(payload.get("response"), list):
                raise ProbeError("unexpected_date_endpoint_paging_or_schema")
            groups = []
            for league_id, name in LEAGUES.items():
                rows = [r for r in payload["response"] if r.get("league", {}).get("id") == league_id]
                summary = fixture_summary({"paging": {"total": 1}, "response": rows}, league_id, season, day)
                groups.append({"league_id": league_id, "name": name, **summary})
            report["days"].append({"requested_date": date, "global_response_rows": len(payload["response"]), "leagues": groups})
        report["status"] = "date_endpoint_connected_not_live_activated"
    except (ProbeError, ValueError) as error:
        report["status"] = "blocked"
        report["reason"] = str(error).replace(probe.key, "[REDACTED]") if probe else str(error)
    report["checked_at"] = datetime.now(timezone.utc).isoformat()
    report["calls"] = probe.calls if probe else []
    report["remaining_conservative"] = probe.remaining if probe else None
    report["target_fixtures_in_business_round"] = sum(len(g["fixtures"]) for d in report["days"] for g in d["leagues"])
    destination = ROOT/"reports/api-football/date-smoke-test.json"
    if report["status"] == "blocked":
        # Preserve the last good snapshot on network, plan or quota failure.
        destination = destination.with_name("schedule-last-failure.json")
    write_json(destination, report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--date")
    args = parser.parse_args()
    result = collect(args.execute, args.date)
    print(json.dumps({k: result.get(k) for k in ["status", "reason", "maximum_http_requests", "maximum_billable_requests", "target_fixtures_in_business_round", "remaining_conservative"]}))
