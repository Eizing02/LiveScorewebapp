"""Display-only fixture catalogue. Never supplies training labels or predictions."""
import hashlib
import json
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from ml.live.normalize import LEAGUES, STATUSES, business_date, moment, score_pair, sha, stamp
from ml.pipeline import ROOT, canonical_json, write_json

SOURCE = ROOT / "data/processed/api-football"
OUTPUT = ROOT / "data/processed/program"


def positive_id(value):
    if type(value) is not int or not 0 < value < 2**53:
        raise ValueError("invalid_provider_identity")
    return value


def label(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 200:
        raise ValueError("invalid_display_name")
    return value.strip()


def normalize(row, observed_at, source_date, source_sha256):
    fixture, league, teams = row["fixture"], row["league"], row["teams"]
    identity = positive_id(fixture["id"])
    league_id = positive_id(league["id"])
    home_id, away_id = [positive_id(teams[side]["id"]) for side in ["home", "away"]]
    if home_id == away_id:
        raise ValueError("same_team_both_sides")
    kickoff = stamp(fixture["date"])
    if fixture.get("timestamp") is not None and abs(moment(kickoff).timestamp() - fixture["timestamp"]) > 1:
        raise ValueError("kickoff_timestamp_conflict")
    status = STATUSES.get(fixture["status"]["short"], "unverified")
    home, away = [label(teams[side]["name"]) for side in ["home", "away"]]
    pair = score_pair(row.get("goals"))
    fulltime = score_pair(row.get("score", {}).get("fulltime"))
    value = {
        "id": f"api-football-{identity}", "provider_fixture_id": identity,
        "provider_league_id": league_id, "league_id": LEAGUES[league_id][1] if league_id in LEAGUES else f"provider-{league_id}",
        "league_name": label(league["name"]), "country": label(league.get("country") or "Unknown"),
        "competition_type": league.get("type") if league.get("type") in {"League", "Cup"} else "unknown",
        "season": str(league.get("season", "unknown")), "home": home, "away": away,
        "home_provider_id": home_id, "away_provider_id": away_id, "home_id": "", "away_id": "",
        "kickoff_utc": kickoff, "match_date": kickoff[:10], "business_date": business_date(kickoff),
        "status": status, "provider_status": fixture["status"]["short"],
        "current_score": None if status in {"scheduled", "unverified"} else pair,
        "score_90": fulltime if status.startswith("finished") else None,
        "observed_at": stamp(observed_at), "source_date": source_date, "source_sha256": source_sha256,
        "source": "api_football_recorded", "quality": "display_only_not_training", "mapping_status": "unreviewed",
        "model_supported": league_id in LEAGUES, "analysis": None,
        "search_text": unicodedata.normalize("NFKC", home + " " + away).lower(),
    }
    value["observation_id"] = sha(value)
    return value


def build(source=SOURCE, output=OUTPUT, asof=None):
    now = moment(asof or datetime.now(timezone.utc).isoformat())
    ledger = json.loads((Path(source) / "request-ledger.json").read_text(encoding="utf-8"))
    observations, sources, quarantine = {}, {}, []
    for call in ledger:
        route = urlsplit(call.get("route", ""))
        day = parse_qs(route.query).get("date", [None])[0]
        if route.path != "/fixtures" or not day or not call.get("response_sha256"):
            continue
        datetime.strptime(day, "%Y-%m-%d")
        seen = call.get("first_seen_at")
        if not seen or moment(seen) > now:
            continue
        digest = call["response_sha256"]
        raw = (Path(source) / "responses" / (digest + ".json")).read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("catalog_source_checksum_mismatch")
        payload = json.loads(raw)
        errors = payload.get("errors")
        rows = payload.get("response")
        error_text = json.dumps(errors).lower()
        denied = bool(errors) and any(word in error_text for word in ["access", "free plan", "subscription", "not allowed", "not subscribed"])
        state = "denied" if denied else "recorded" if not errors and isinstance(rows, list) and payload.get("paging", {}).get("total") == 1 else "partial"
        info = {"source_date": day, "observed_at": stamp(seen), "state": state, "rows": len(rows) if isinstance(rows, list) else 0, "source_sha256": digest}
        sources[sha(info)] = info
        if state != "recorded":
            continue
        for row in rows:
            try:
                value = normalize(row, seen, day, digest)
                observations[value["observation_id"]] = value
            except (KeyError, TypeError, ValueError) as error:
                quarantine.append({"source_sha256": digest, "fixture_id": row.get("fixture", {}).get("id"), "reason": str(error)})
    records = []
    for key, value in sorted(sources.items()):
        records.append({"kind": "source", "values": [key, value["source_date"], value["observed_at"], value["state"], value["rows"], value["source_sha256"]]})
    for value in sorted(observations.values(), key=lambda r: (r["observed_at"], r["observation_id"])):
        text = canonical_json(value)
        records.append({"kind": "fixture", "values": [value["observation_id"], value["id"], value["provider_league_id"], value["kickoff_utc"], value["business_date"], value["observed_at"], value["status"], value["source_date"], value["search_text"], text, hashlib.sha256(text.encode()).hexdigest()]})
    batches, batch = [], []
    for record in records:
        if len(batch) >= 20 or len(canonical_json({"records": batch + [record]}).encode()) > 80000:
            batches.append(batch)
            batch = []
        batch.append(record)
    if batch:
        batches.append(batch)
    latest = {}
    for row in observations.values():
        previous = latest.get(row["id"])
        if previous is None or (row["observed_at"], row["observation_id"]) > (previous["observed_at"], previous["observation_id"]):
            latest[row["id"]] = row
    summary = {"generated_at": stamp(now.isoformat()), "unique_fixtures": len(latest), "observations": len(observations), "source_observations": len(sources), "competitions": len({r["provider_league_id"] for r in latest.values()}), "quarantined": len(quarantine), "provider_requests": 0, "training_labels_added": 0, "model_promoted": False}
    write_json(Path(output) / "import-batches.json", batches)
    write_json(Path(output) / "quarantine.json", quarantine)
    write_json(Path(output) / "summary.json", summary)
    return summary
