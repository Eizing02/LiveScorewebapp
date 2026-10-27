"""Six explicit, read-only endpoint samples for the account integration analysis.

Do not attach these responses to predictions or historical training automatically.
"""
import argparse
import json
import math
from datetime import datetime, timezone

from ml.pipeline import ROOT, write_json
from scripts.api_football_probe import PRIVATE, Probe, ProbeError, load_key


class CapabilityProbe(Probe):
    allowed_routes = frozenset({"/fixtures/statistics", "/fixtures/lineups", "/fixtures/players", "/injuries", "/predictions", "/fixtures/headtohead"})


def nonnegative_number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (ValueError, TypeError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def summarize(route, payload):
    rows = payload.get("response")
    if not isinstance(rows, list):
        raise ProbeError("unexpected_endpoint_response_shape")
    result = {"response_rows": len(rows), "data_present": bool(rows), "account_access": "nonempty_sample_verified" if rows else "empty_sample_inconclusive"}
    if route == "/fixtures/statistics":
        types = sorted({s.get("type", "") for row in rows for s in row.get("statistics", [])})
        xg = [{"team_id": row.get("team", {}).get("id"), "type": s.get("type"), "value_present": s.get("value") is not None, "numeric_value": nonnegative_number(s.get("value"))} for row in rows for s in row.get("statistics", []) if s.get("type", "").lower() in {"xg", "expected_goals", "expected goals"}]
        result.update({"statistic_types": types, "xg_fields": xg, "xg_value_verified": any(item["numeric_value"] is not None for item in xg)})
    elif route == "/fixtures/lineups":
        result["teams"] = [{"team_id": r.get("team", {}).get("id"), "formation": r.get("formation"), "starting_players": len(r.get("startXI", [])), "substitutes": len(r.get("substitutes", []))} for r in rows]
    elif route == "/fixtures/players":
        result["teams"] = [{"team_id": r.get("team", {}).get("id"), "player_records": len(r.get("players", [])), "with_minutes": sum(any(s.get("games", {}).get("minutes") is not None for s in p.get("statistics", [])) for p in r.get("players", [])), "with_rating": sum(any(s.get("games", {}).get("rating") is not None for s in p.get("statistics", [])) for p in r.get("players", []))} for r in rows]
    elif route == "/injuries":
        result["types"] = sorted({r.get("player", {}).get("type", "unknown") for r in rows})
        result["note"] = "Empty response does not prove no absentees; questionable is different from confirmed missing."
    elif route == "/predictions" and rows:
        prediction = rows[0].get("predictions", {})
        percentages = prediction.get("percent", {})
        parsed = []
        for name in ["home", "draw", "away"]:
            try:
                value = float(str(percentages[name]).rstrip("%"))/100
                if not math.isfinite(value) or not 0 <= value <= 1:
                    raise ValueError("invalid_probability")
                parsed.append(value)
            except (KeyError, ValueError, TypeError):
                parsed = []
                break
        result.update({"fields": sorted(prediction), "percent": percentages, "probabilities_valid": len(parsed) == 3 and abs(sum(parsed)-1) < .001, "comparison_fields": sorted(rows[0].get("comparison", {})), "bundled_h2h_rows": len(rows[0].get("h2h", [])), "provider_forecast_not_our_model": True})
    elif route == "/fixtures/headtohead":
        result["competition_ids"] = sorted({r.get("league", {}).get("id") for r in rows if isinstance(r.get("league", {}).get("id"), int)})
        result["note"] = "Filter competition, cutoff and 90-minute status locally before deriving H2H features."
    return result


def collect(execute=False):
    report = {"purpose": "account_endpoint_samples_not_production_integration", "maximum_requests": 6, "automatic_retries": 0, "samples": [], "model_promoted": False, "production_deployed": False, "status": "dry_run"}
    if not execute:
        return report
    snapshot = json.loads((PRIVATE/"provider-preview.json").read_text(encoding="utf-8"))
    fixtures = [f for league in snapshot["leagues"] for f in league["fixtures"]]
    completed = next(f for f in fixtures if f["status"] == "FT" and f["league_id"] == 39)
    now = datetime.now(timezone.utc)
    upcoming = sorted((f for f in fixtures if f["status"] == "NS" and datetime.fromisoformat(f["kickoff_utc"]) > now), key=lambda f: f["kickoff_utc"])
    target = upcoming[-1] if upcoming else completed
    tasks = [("/fixtures/statistics", {"fixture": completed["provider_fixture_id"]}, completed), ("/fixtures/players", {"fixture": completed["provider_fixture_id"]}, completed), ("/fixtures/lineups", {"fixture": target["provider_fixture_id"]}, target), ("/injuries", {"fixture": target["provider_fixture_id"]}, target), ("/predictions", {"fixture": target["provider_fixture_id"]}, target), ("/fixtures/headtohead", {"h2h": str(target["home_provider_id"])+"-"+str(target["away_provider_id"])}, target)]
    probe = CapabilityProbe(load_key())
    recent = [r for r in probe.ledger if now.timestamp()-r["attempted_at"] < 1800 and "x-ratelimit-requests-remaining" in r.get("rate_headers", {})]
    if not recent:
        raise ProbeError("fresh_verified_quota_required_before_capability_samples")
    probe.remaining = recent[-1]["rate_headers"]["x-ratelimit-requests-remaining"]
    if probe.remaining < 16:
        raise ProbeError("six_samples_plus_ten_reserve_required")
    for route, query, fixture in tasks:
        observed = datetime.now(timezone.utc)
        item = {"route": route, "query": query, "fixture_id": fixture["provider_fixture_id"], "fixture_kickoff_utc": fixture["kickoff_utc"], "fixture": fixture["home"]+" / "+fixture["away"], "observed_at": observed.isoformat(), "observed_before_kickoff": observed < datetime.fromisoformat(fixture["kickoff_utc"])}
        try:
            item.update(summarize(route, probe.get(route, query)))
            item["status"] = "response_verified"
        except ProbeError as error:
            item.update({"status": "blocked", "reason": str(error).replace(probe.key, "[REDACTED]")})
            if probe.calls and probe.calls[-1].get("status") in {401, 403, 429}:
                report["samples"].append(item)
                break
        if probe.calls and probe.calls[-1].get("first_seen_at"):
            item["request_queued_at"] = item["observed_at"]
            item["observed_at"] = probe.calls[-1]["first_seen_at"]
            item["observed_before_kickoff"] = datetime.fromisoformat(item["observed_at"]) < datetime.fromisoformat(fixture["kickoff_utc"])
            item["response_sha256"] = probe.calls[-1]["response_sha256"]
        report["samples"].append(item)
        print(json.dumps({"route": route, "status": item["status"], "rows": item.get("response_rows")}), flush=True)
    report.update({"status": "samples_complete_unpromoted", "captured_at": datetime.now(timezone.utc).isoformat(), "calls": probe.calls, "requests_actual": len(probe.calls), "remaining_conservative": probe.remaining, "last_rate_headers": probe.rates})
    write_json(ROOT/"reports/api-football/capability-samples.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    result = collect(args.execute)
    print(json.dumps({k: result.get(k) for k in ["status", "requests_actual", "remaining_conservative"]}))
