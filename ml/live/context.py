"""Availability-aware API context; kept outside the frozen score model's weights."""
from collections import defaultdict

from ml.live.normalize import finite_number, moment


def context_for(fixture, enrichments, observations, asof):
    cutoff = moment(asof)
    available = [e for e in enrichments if moment(e["available_at"]) <= cutoff]
    target = [e for e in available if e["fixture_id"] == fixture["fixture_id"]]
    latest = {}
    for value in sorted(target, key=lambda e: (moment(e["available_at"]), e["id"])):
        latest[value["route"]] = value
    injury = latest.get("/injuries")
    identities = {(r.get("player", {}).get("id"), r.get("team", {}).get("id"), r.get("player", {}).get("type")) for r in injury["rows"] if isinstance(r.get("player", {}).get("id"), int) and r.get("team", {}).get("id") in {fixture["home_provider_id"], fixture["away_provider_id"]}} if injury and injury["rows"] else set()
    availability = {"raw_records": len(injury["rows"]) if injury else 0, "duplicates_merged": len(injury["rows"])-len(identities) if injury else 0, "known": bool(identities), "records": len(identities) if identities else None, "missing": sum(kind == "Missing Fixture" for _, _, kind in identities) if identities else None, "questionable": sum(kind == "Questionable" for _, _, kind in identities) if identities else None, "available_at": injury["available_at"] if injury else None}
    lineup = latest.get("/fixtures/lineups")
    confirmed = lineup is not None and len(lineup["rows"]) == 2 and {r.get("team", {}).get("id") for r in lineup["rows"]} == {fixture["home_provider_id"], fixture["away_provider_id"]} and all(len(r.get("startXI", [])) == 11 for r in lineup["rows"])
    lineups = {"confirmed": confirmed, "teams": [{"id": r.get("team", {}).get("id"), "formation": r.get("formation"), "startXI": r.get("startXI", [])} for r in lineup["rows"]] if confirmed else [], "available_at": lineup["available_at"] if lineup else None}
    forecast = latest.get("/predictions")
    external = {"probabilities": forecast.get("probabilities") if forecast else None, "available_at": forecast["available_at"] if forecast else None, "source": "API-Football", "calibration_verified": False}
    finished = {r["fixture_id"]: r for r in observations if r["status"] == "finished" and not r["quarantine_reasons"] and moment(r["first_seen_at"]) <= cutoff and moment(r["kickoff_utc"]) < cutoff}
    games = defaultdict(list)
    for value in available:
        if value["route"] != "/fixtures/statistics" or value["fixture_id"] == fixture["fixture_id"] or value["fixture_id"] not in finished:
            continue
        match = finished[value["fixture_id"]]
        for row in value["rows"]:
            team = row.get("team", {}).get("id")
            xg = next((finite_number(s.get("value")) for s in row.get("statistics", []) if s.get("type") == "expected_goals"), None)
            if xg is not None:
                games[team].append({"fixture_id": value["fixture_id"], "kickoff_utc": match["kickoff_utc"], "xg": xg, "available_at": value["available_at"]})
    rolling = {}
    for side in ["home", "away"]:
        unique = {r["fixture_id"]: r for r in sorted(games[fixture[side+"_provider_id"]], key=lambda r: r["available_at"])}
        recent = sorted(unique.values(), key=lambda r: r["kickoff_utc"])[-5:]
        rolling[side] = {"n": len(recent), "xg_for_mean": sum(r["xg"] for r in recent)/len(recent) if recent else None}
    return {"information_asof": asof, "availability": availability, "lineups": lineups, "provider_forecast": external, "past_xg": rolling, "used_in_model_weights": False, "target_match_statistics_excluded": True}
