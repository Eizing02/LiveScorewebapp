import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from ml.expanded import identity
from ml.pipeline import ROOT, canonical_json

LEAGUES = {39: ("en.1", "eng-premier", "Premier League", "England", "Europe/London"), 40: ("en.2", "eng-championship", "Championship", "England", "Europe/London"), 140: ("es.1", "esp-laliga", "La Liga", "Spain", "Europe/Madrid"), 78: ("de.1", "de-bundesliga", "Bundesliga", "Germany", "Europe/Berlin"), 135: ("it.1", "ita-serie-a", "Serie A", "Italy", "Europe/Rome")}
STATUSES = {"NS": "scheduled", "TBD": "unverified", "1H": "live", "HT": "live", "2H": "live", "ET": "live", "BT": "live", "P": "live", "LIVE": "live", "FT": "finished", "AET": "finished_extra_time", "PEN": "finished_penalties", "PST": "postponed", "CANC": "cancelled", "ABD": "abandoned", "SUSP": "suspended", "INT": "interrupted", "AWD": "awarded", "WO": "walkover"}


def sha(value):
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def moment(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone_required")
    return parsed.astimezone(timezone.utc)


def business_date(kickoff):
    return (moment(kickoff).astimezone(ZoneInfo("Asia/Bangkok"))-timedelta(hours=6)).date().isoformat()


def stamp(value):
    return moment(value).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def score_pair(value):
    if not isinstance(value, dict):
        return None
    pair = [value.get("home"), value.get("away")]
    if any(v is None for v in pair):
        return None
    if any(not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= 100 for v in pair):
        raise ValueError("invalid_score")
    return pair


def mapping_config():
    return json.loads((ROOT/"ml/config/provider_identity_v1.json").read_text(encoding="utf-8"))


def resolve_team(team, league_id, config):
    code, _, _, country, _ = LEAGUES[league_id]
    candidates = [r for r in config["teams"] if r["provider_id"] == team["id"] and r["league"] == code and r["provider_name"] == team["name"] and r["status"] == "reviewed"]
    if len(candidates) != 1:
        return None
    row = candidates[0]
    canonical_id, name = identity(code, row["canonical_name"])
    if row["country"] != country or row["canonical_id"] != canonical_id:
        raise ValueError("invalid_mapping_evidence")
    return {"id": canonical_id, "name": name, "provider_id": team["id"], "provider_name": team["name"], "quality": "reviewed_source_name_context", "evidence": row["evidence"]}


def normalize_fixture(raw, seen_at, source_hash, config=None):
    seen = moment(seen_at)
    config = config or mapping_config()
    fixture, league, teams = raw["fixture"], raw["league"], raw["teams"]
    league_id = league["id"]
    if league_id not in LEAGUES:
        raise ValueError("unsupported_league")
    code, canonical_league, league_name, country, tz = LEAGUES[league_id]
    if league.get("country") != country:
        raise ValueError("league_country_mismatch")
    kickoff = moment(fixture["date"])
    if not isinstance(fixture["id"], int) or fixture["id"] <= 0 or not isinstance(league["season"], int):
        raise ValueError("invalid_fixture_identity")
    if abs(kickoff.timestamp()-fixture["timestamp"]) > 1:
        raise ValueError("kickoff_timestamp_mismatch")
    home, away = resolve_team(teams["home"], league_id, config), resolve_team(teams["away"], league_id, config)
    if teams["home"]["id"] == teams["away"]["id"] or (home and away and home["id"] == away["id"]):
        raise ValueError("same_team")
    state = STATUSES.get(fixture["status"]["short"], "unverified")
    scores = raw.get("score", {})
    ft, extra, penalties = score_pair(scores.get("fulltime")), score_pair(scores.get("extratime")), score_pair(scores.get("penalty"))
    current = score_pair(raw.get("goals"))
    reasons = []
    if not home or not away:
        reasons.append("identity_mapping_pending")
    if state == "finished" and (ft is None or current != ft):
        reasons.append("missing_or_conflicting_fulltime_score")
    if state.startswith("finished") and kickoff >= seen:
        reasons.append("finished_in_future")
    if state == "scheduled" and current is not None:
        reasons.append("scheduled_fixture_has_score")
    if state in {"unverified", "awarded", "walkover", "abandoned", "interrupted", "suspended"}:
        reasons.append("unverified_or_nonstandard_outcome")
    kickoff_text = stamp(kickoff.isoformat())
    occurrence = sha([fixture["id"], kickoff_text])
    result = {"fixture_id": "api-football-"+str(fixture["id"]), "provider_fixture_id": fixture["id"], "occurrence_id": occurrence, "league": code, "league_id": canonical_league, "provider_league_id": league_id, "league_name": league_name, "country": country, "season": f'{league["season"]}-{str(league["season"]+1)[2:]}', "date": kickoff.astimezone(ZoneInfo(tz)).date().isoformat(), "business_date": business_date(kickoff_text), "kickoff_utc": kickoff_text, "competition_timezone": tz, "home_id": home["id"] if home else None, "away_id": away["id"] if away else None, "home": home["name"] if home else teams["home"]["name"], "away": away["name"] if away else teams["away"]["name"], "home_provider_id": teams["home"]["id"], "away_provider_id": teams["away"]["id"], "mapping_version": sha(config), "mapping_status": "reviewed" if home and away else "pending", "status": state, "provider_status": fixture["status"]["short"], "score_90": ft, "score_extra_time": extra, "score_penalties": penalties, "current_score": current, "first_seen_at": seen.isoformat(), "source_sha256": source_hash, "quarantine_reasons": reasons, "source": "api_football", "provider_identity_independently_verified": False}
    result["observation_id"] = sha(result)
    return result


def finite_number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(str(value).rstrip("%"))
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def normalize_enrichment(route, payload, available_at, source_hash, fixture_id):
    moment(available_at)
    rows = payload.get("response")
    if not isinstance(rows, list):
        raise ValueError("invalid_enrichment_response")
    result = {"fixture_id": fixture_id, "route": route, "available_at": available_at, "source_sha256": source_hash, "coverage": "observed_nonempty" if rows else "unknown_empty", "rows": rows, "used_in_model": False}
    if route == "/predictions" and rows:
        raw = rows[0].get("predictions", {}).get("percent", {})
        p = [finite_number(raw.get(k)) for k in ["home", "draw", "away"]]
        if any(v is None for v in p) or abs(sum(p)-100) > .1:
            raise ValueError("invalid_provider_probabilities")
        result["probabilities"] = [v/100 for v in p]
    result["id"] = sha(result)
    return result
