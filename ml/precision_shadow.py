"""Private prospective research records from the public licensed OpenLigaDB feed.

No API-Football, deployment, approval or user-facing live tips. Preserve actual
first-seen time and immutable bytes; provider results still need verification.
"""
import argparse
import hashlib
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from ml.expanded import CONFIG, OUTPUT, identity, map_name
from ml.pipeline import ROOT, canonical_json, write_json
from ml.precision_predict import PrecisionEngine

DIRECTORY = ROOT/"data/processed/precision-v3-shadow"


def write_once(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json(value)+"\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != payload:
            raise ValueError("prospective_record_immutable")
        return
    with path.open("x", encoding="utf-8") as stream:
        stream.write(payload)


def upcoming_records(payload, league, vocabulary, now, days=7):
    results, rejected = [], []
    for match in payload:
        try:
            kickoff = datetime.fromisoformat(match["matchDateTimeUTC"].replace("Z", "+00:00"))
            if kickoff.tzinfo is None:
                raise ValueError("missing_timezone")
            if match.get("matchIsFinished") or not now+timedelta(hours=2) <= kickoff < now+timedelta(days=days):
                continue
            home, home_method = map_name(match["team1"]["teamName"], vocabulary)
            away, away_method = map_name(match["team2"]["teamName"], vocabulary)
            home_id, _ = identity(league, home)
            away_id, _ = identity(league, away)
            if home_id == away_id or not isinstance(match.get("matchID"), int):
                raise ValueError("invalid_fixture_identity")
            results.append({"id": "openliga-"+str(match["matchID"]), "provider_fixture_id": match["matchID"], "league": league, "league_id": CONFIG["leagues"][league]["id"], "season": f'{match["leagueSeason"]}-{str(match["leagueSeason"]+1)[2:]}', "date": kickoff.astimezone(ZoneInfo("Europe/Berlin")).date().isoformat(), "kickoff_utc": kickoff.astimezone(timezone.utc).isoformat(), "home_id": home_id, "away_id": away_id, "home": home, "away": away, "mapping_methods": [home_method, away_method], "source": "openligadb_public_research", "source_verified": False})
        except (ValueError, KeyError, TypeError) as error:
            rejected.append({"provider_fixture_id": match.get("matchID"), "reason": str(error)})
    return results, rejected


def fetch_current(shortcut, season):
    url = f"https://api.openligadb.de/getmatchdata/{shortcut}/{season}"
    request = urllib.request.Request(url, headers={"User-Agent": "FootballPredictionAI-local-prospective-research/0.3"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read(10_000_001)
    if len(payload) > 10_000_000:
        raise ValueError("public_feed_too_large")
    return json.loads(payload), payload, url


def collect(days=7):
    engine = PrecisionEngine()
    accepted = [json.loads(line) for line in (OUTPUT/"accepted.jsonl").read_text(encoding="utf-8").splitlines()]
    recorded, skipped = [], []
    for league, shortcut in [("de.1", "bl1"), ("de.2", "bl2")]:
        now = datetime.now(timezone.utc)
        local_year = now.astimezone(ZoneInfo("Europe/Berlin")).year
        season = local_year if now.month >= 7 else local_year-1
        payload, raw, url = fetch_current(shortcut, season)
        seen = datetime.now(timezone.utc)
        source_hash = hashlib.sha256(raw).hexdigest()
        source_path = DIRECTORY/"sources"/(source_hash+".json")
        source_path.parent.mkdir(parents=True, exist_ok=True)
        if not source_path.exists():
            with source_path.open("xb") as stream:
                stream.write(raw)
        vocabulary = {row[side] for row in accepted if row["league"] == league for side in ["home", "away"]}
        fixtures, rejected = upcoming_records(payload, league, vocabulary, seen, days)
        skipped.extend(rejected)
        for fixture in fixtures:
            generated = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
            snapshot = engine.predict(fixture, generated)
            if datetime.fromisoformat(generated) >= datetime.fromisoformat(fixture["kickoff_utc"]):
                raise ValueError("prospective_prediction_after_kickoff")
            record = {"fixture": fixture, "prediction": snapshot, "first_seen_at": seen.isoformat(), "generated_at": generated, "source_url": url, "source_sha256": source_hash, "source_license": "ODbL-1.0", "status": "private_prospective_research_unverified", "not_mock": True, "live_approved": False, "prospective_certified": False, "verification_blockers": ["community_fixture_mapping_requires_review", "historical_feature_feed_not_current", "future_result_not_available", "local_timestamp_not_independently_notarized"], "target_score": None}
            key = hashlib.sha256(canonical_json(record).encode()).hexdigest()
            write_once(DIRECTORY/"predictions"/(key+".json"), record)
            recorded.append({"id": fixture["id"], "league": league, "kickoff_utc": fixture["kickoff_utc"], "research_eligible": snapshot["research_eligible"], "checksum": key})
    summary = {"collected_at": datetime.now(timezone.utc).isoformat(), "mode": "private_research_not_live_publication", "records": recorded, "skipped": skipped, "public_openligadb_requests": 2, "api_football_requests": 0, "certified_accuracy": None, "warning": "These records are prospective timestamps, not proof of future accuracy. No result labels are invented and no application model is promoted."}
    write_json(ROOT/"reports/precision-v3/prospective-collection.json", summary)
    print(json.dumps({"saved_before_kickoff": len(recorded), "research_eligible": sum(r["research_eligible"] for r in recorded), "skipped": len(skipped), "api_football_requests": 0, "certified_accuracy": None}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7, choices=range(1, 15))
    args = parser.parse_args()
    collect(args.days)
