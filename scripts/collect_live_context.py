"""Budgeted context collection before forecasts; only explicit execution calls API."""
import argparse
import json
from datetime import datetime, timezone

from ml.live.ledger import DIRECTORY, ingest, latest_observations, read_kind
from ml.live.normalize import moment
from ml.pipeline import ROOT, write_json
from scripts.api_football_probe import ManagedProbe, ProbeError, load_key


class ContextProbe(ManagedProbe):
    allowed_routes = frozenset({"/status", "/injuries", "/predictions", "/fixtures/lineups", "/fixtures/statistics", "/fixtures/players"})


def tasks_for(fixtures, enrichments, asof, archive_finished=False):
    now = moment(asof)
    tasks = []
    for fixture in sorted(fixtures, key=lambda f: (f["kickoff_utc"], f["fixture_id"])):
        if fixture["mapping_status"] != "reviewed" or fixture["quarantine_reasons"]:
            continue
        seconds = (moment(fixture["kickoff_utc"])-now).total_seconds()
        previous = [e for e in enrichments if e["fixture_id"] == fixture["fixture_id"] and moment(e["available_at"]) <= now]
        routes = []
        if fixture["status"] == "scheduled" and 120 < seconds <= 86400:
            routes = ["/injuries", "/predictions"]
            lineups = [e for e in previous if e["route"] == "/fixtures/lineups"]
            expected_teams = {fixture["home_provider_id"], fixture["away_provider_id"]}
            confirmed = any(len(e["rows"]) == 2 and {t.get("team", {}).get("id") for t in e["rows"]} == expected_teams and all(len(t.get("startXI", [])) == 11 for t in e["rows"]) for e in lineups)
            if seconds <= 2400 and not confirmed and len(lineups) < 2 and (not lineups or (now-max(moment(e["available_at"]) for e in lineups)).total_seconds() >= 900):
                routes.insert(0, "/fixtures/lineups")
        elif archive_finished and fixture["status"] == "finished" and -172800 < seconds < 0:
            routes = ["/fixtures/statistics", "/fixtures/players"]
        for route in routes:
            if route != "/fixtures/lineups" and any(e["route"] == route for e in previous):
                continue
            tasks.append({"route": route, "query": {"fixture": fixture["provider_fixture_id"]}, "fixture_id": fixture["fixture_id"], "kickoff_utc": fixture["kickoff_utc"], "prematch": seconds > 0})
    return sorted(tasks, key=lambda t: (not t["prematch"], t["kickoff_utc"], t["route"] != "/fixtures/lineups", t["fixture_id"]))


def collect(execute=False, archive_finished=False, maximum=3):
    if not 1 <= maximum <= 3:
        raise ValueError("context_budget_must_be_one_to_three")
    now = datetime.now(timezone.utc).isoformat()
    ingest()
    tasks = tasks_for(latest_observations(read_kind(DIRECTORY, "observations"), now), read_kind(DIRECTORY, "enrichments"), now, archive_finished)[:maximum]
    report = {"generated_at": now, "mode": "executed" if execute else "dry_run", "maximum_billable_requests": maximum, "tasks": tasks, "results": [], "model_promoted": False}
    if execute and tasks:
        probe = ContextProbe(load_key())
        from scripts.api_football_probe import account_summary
        account = account_summary(probe.get("/status"))
        if not account["active"] or account["plan"].lower() != "free":
            raise ValueError("active_free_account_required")
        probe.remaining = min(probe.remaining, account["daily_remaining"]) if probe.remaining is not None else account["daily_remaining"]
        for task in tasks:
            if task["prematch"] and (moment(task["kickoff_utc"])-datetime.now(timezone.utc)).total_seconds() <= 90:
                report["results"].append({"fixture_id": task["fixture_id"], "status": "deadline_missed_skipped"})
                continue
            try:
                payload = probe.get(task["route"], task["query"])
                report["results"].append({"fixture_id": task["fixture_id"], "route": task["route"], "response_rows": len(payload.get("response", [])), "status": "received"})
            except ProbeError as error:
                report["results"].append({"fixture_id": task["fixture_id"], "status": "blocked", "reason": str(error).replace(probe.key, "[REDACTED]")})
                break
        report["provider_http_requests"] = len(probe.calls)
        ingest()
    else:
        report["provider_http_requests"] = 0
    write_json(ROOT/"reports/live-research/context-collection.json", report)
    print(json.dumps({"mode": report["mode"], "tasks": len(tasks), "provider_http_requests": report["provider_http_requests"]}))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--archive-finished", action="store_true")
    args = parser.parse_args()
    collect(args.execute, args.archive_finished)
