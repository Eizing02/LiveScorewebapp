"""Build real-fixture research, immutable observations and local D1 import SQL."""
import hashlib
import json
from datetime import datetime, timezone

from ml.expanded import CONFIG as DATA_CONFIG
from ml.live.context import context_for
from ml.live.ledger import DIRECTORY, accepted_history, ingest, latest_observations, read_kind, save_manifest, write_once
from ml.live.normalize import mapping_config, moment, sha, stamp
from ml.live.predict import LivePrecisionEngine
from ml.pipeline import ROOT, canonical_json, write_json


def history_rows(matches, fixture, asof, enrichments=None):
    from zoneinfo import ZoneInfo
    day = min(fixture["date"], moment(asof).astimezone(ZoneInfo(fixture["competition_timezone"])).date().isoformat())
    rows = []
    for match in matches:
        if match["date"] >= day or match.get("available_at") and moment(match["available_at"]) > moment(asof):
            continue
        rows.append({"id": match["id"], "league_id": DATA_CONFIG["leagues"][match["league"]]["id"], "league_name": DATA_CONFIG["leagues"][match["league"]]["name"], "season": match["season"], "match_date": match["date"], "home_id": match["home_id"], "away_id": match["away_id"], "home": match["home"], "away": match["away"], "home_goals": match["goals"][0], "away_goals": match["goals"][1], "quality": match.get("quality", "historical_unverified_time")})
    for enrichment in enrichments or []:
        if enrichment["route"] != "/fixtures/headtohead" or enrichment["fixture_id"] != fixture["fixture_id"] or moment(enrichment["available_at"]) > moment(asof):
            continue
        provider_ids = {fixture["home_provider_id"]: fixture["home_id"], fixture["away_provider_id"]: fixture["away_id"]}
        canonical_names = {fixture["home_id"]: fixture["home"], fixture["away_id"]: fixture["away"]}
        for raw in enrichment["rows"]:
            try:
                from ml.live.normalize import LEAGUES, score_pair
                kickoff = moment(raw["fixture"]["date"])
                match_day = kickoff.astimezone(ZoneInfo(fixture["competition_timezone"])).date().isoformat()
                if raw["fixture"]["status"]["short"] != "FT" or match_day < DATA_CONFIG["window_start"] or match_day >= day:
                    continue
                h, a = provider_ids[raw["teams"]["home"]["id"]], provider_ids[raw["teams"]["away"]["id"]]
                score = score_pair(raw.get("score", {}).get("fulltime"))
                if score is None:
                    continue
                lid = raw["league"]["id"]
                canonical_league = LEAGUES[lid][1] if lid in LEAGUES else "provider-competition-"+str(lid)
                if any(r["home_id"] == h and r["away_id"] == a and r["match_date"] == match_day and r["league_id"] == canonical_league for r in rows):
                    continue
                rows.append({"id": "api-h2h-"+str(raw["fixture"]["id"]), "league_id": canonical_league, "league_name": raw["league"]["name"], "season": str(raw["league"]["season"]), "match_date": match_day, "home_id": h, "away_id": a, "home": canonical_names[h], "away": canonical_names[a], "home_goals": score[0], "away_goals": score[1], "quality": "api_h2h_display_only"})
            except (KeyError, TypeError, ValueError):
                continue
    rows.sort(key=lambda r: (r["match_date"], r["id"]), reverse=True)
    home, away, league = fixture["home_id"], fixture["away_id"], fixture["league_id"]
    return {"cutoff_date_exclusive": day, "home": [r for r in rows if r["league_id"] == league and home in [r["home_id"], r["away_id"]]][:20], "away": [r for r in rows if r["league_id"] == league and away in [r["home_id"], r["away_id"]]][:20], "home_venue": [r for r in rows if r["league_id"] == league and r["home_id"] == home][:20], "away_venue": [r for r in rows if r["league_id"] == league and r["away_id"] == away][:20], "h2h_all": [r for r in rows if {home, away} == {r["home_id"], r["away_id"]}][:20], "h2h_league": [r for r in rows if r["league_id"] == league and {home, away} == {r["home_id"], r["away_id"]}][:20]}


def runtime_version():
    names = ["ml/live/predict.py", "ml/live/normalize.py", "ml/live/context.py", "ml/live/ledger.py", "ml/live/pipeline.py", "ml/config/provider_identity_v1.json", "ml/config/provider_access_policy.json"]
    return "live-runtime-"+sha({p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in names})[:16]


def build(asof=None, directory=DIRECTORY):
    now = stamp(asof or datetime.now(timezone.utc).isoformat())
    imported = ingest(directory)
    observations = [o for o in read_kind(directory, "observations") if o["mapping_version"] == sha(mapping_config())]
    enrichments = read_kind(directory, "enrichments")
    latest = latest_observations(observations, now)
    matches, manifest = accepted_history(observations, now)
    save_manifest(manifest, directory, matches)
    runtime = runtime_version()
    engine = LivePrecisionEngine(matches, now, manifest["dataset_version"], runtime_version=runtime, component_directory=directory)
    predictions, features, failures = [], [], []
    archived_before = read_kind(directory, "predictions")
    for fixture in sorted(latest, key=lambda f: (f["kickoff_utc"], f["fixture_id"])):
        if moment(fixture["kickoff_utc"]) <= moment(now) or fixture["status"] != "scheduled":
            continue
        try:
            context = context_for(fixture, enrichments, latest, now)
            stages = {p.get("stage", "initial") for p in archived_before if p["fixture_id"] == fixture["fixture_id"] and p["occurrence_id"] == fixture["occurrence_id"]}
            stage = "initial" if "initial" not in stages else "final" if context["lineups"]["confirmed"] and "final" not in stages else "pre_lineup" if (moment(fixture["kickoff_utc"])-moment(now)).total_seconds() <= 3600 and "pre_lineup" not in stages else None
            if stage is None:
                continue
            prediction, feature = engine.predict_live(fixture)
            prediction["runtime_version"] = runtime
            prediction["rich_context"] = context
            prediction["stage"] = stage
            prediction["feature_snapshot_id"] = feature["id"]
            write_once(directory, "features", feature)
            write_once(directory, "predictions", prediction)
            predictions.append(prediction)
            features.append(feature)
        except ValueError as error:
            failures.append({"fixture_id": fixture["fixture_id"], "reason": str(error)})
    archived_predictions = read_kind(directory, "predictions")
    details = []
    for fixture in latest:
        eligible = [p for p in archived_predictions if p["fixture_id"] == fixture["fixture_id"] and p["occurrence_id"] == fixture["occurrence_id"] and moment(p["generated_at"]) <= moment(now)]
        prediction = max(eligible, key=lambda p: p["generated_at"], default=None)
        cutoff = min(moment(now), moment(fixture["kickoff_utc"]))
        detail = {"fixture": fixture, "analysis": prediction, "history": history_rows(matches, fixture, cutoff.isoformat(), enrichments), "context": context_for(fixture, enrichments, latest, cutoff.isoformat()), "recorded_enrichments": [{"route": e["route"], "available_at": e["available_at"], "coverage": e["coverage"], "prematch_available": moment(e["available_at"]) < moment(fixture["kickoff_utc"]), "response_rows": len(e["rows"])} for e in enrichments if e["fixture_id"] == fixture["fixture_id"]], "generated_at": now, "dataset_version": manifest["dataset_version"], "mode": "private_research", "production_approved": False, "state": "snapshot_available" if prediction else "already_started_no_backdated_prediction" if moment(fixture["kickoff_utc"]) <= moment(now) else "insufficient_verified_data"}
        stats = [e for e in enrichments if e["fixture_id"] == fixture["fixture_id"] and e["route"] == "/fixtures/statistics" and moment(e["available_at"]) <= moment(now)]
        detail["postmatch_statistics"] = [e["rows"] for e in sorted(stats, key=lambda e: e["available_at"])[-1:]]
        detail["id"] = sha(detail)
        write_once(directory, "details", detail)
        details.append(detail)
    summary = {"generated_at": now, "runtime_version": runtime, **imported, "latest_fixtures": len(latest), "reviewed_mapping_fixtures": sum(f["mapping_status"] == "reviewed" for f in latest), "quarantined_fixtures": sum(bool(f["quarantine_reasons"]) for f in latest), "new_predictions_before_kickoff": len(predictions), "archived_predictions": len(archived_predictions), "future_fixtures": sum(moment(f["kickoff_utc"]) > moment(now) for f in latest), "rejected_predictions": failures, "dataset": manifest, "active_model": None, "model_auto_promote": False, "enrichment_used_in_weights": False}
    from ml.live.evaluate import evaluate
    summary["prospective_evaluation"] = evaluate(directory, now)
    export_sql(directory, observations, enrichments, details, manifest, runtime, summary)
    write_json(ROOT/"reports/live-research/implementation.json", summary)
    print(json.dumps({k: summary[k] for k in ["latest_fixtures", "reviewed_mapping_fixtures", "quarantined_fixtures", "new_predictions_before_kickoff", "future_fixtures"]}))
    return summary


def export_sql(directory, observations, enrichments, details, manifest, runtime, summary):
    statements, records = [], []
    def quote(value):
        return "NULL" if value is None else "'"+str(value).replace("'", "''")+"'"
    def insert(table, values):
        text = "INSERT OR IGNORE INTO "+table+" VALUES("+",".join(quote(v) for v in values)+");"
        if len(text.encode()) > 95000:
            raise ValueError("local_import_statement_too_large")
        statements.append(text)
        records.append({"table": table, "values": values})
    config = mapping_config()
    for team in config["teams"]:
        insert("provider_team_mappings", [sha(config), team["provider_id"], team["league"], team["canonical_id"], team["status"], canonical_json(team)])
    for row in observations:
        payload = canonical_json(row)
        insert("provider_fixture_observations", [row["observation_id"], row["fixture_id"], row["occurrence_id"], row["league_id"], row["home_id"], row["away_id"], row["kickoff_utc"], row["business_date"], stamp(row["first_seen_at"]), row["status"], payload, hashlib.sha256(payload.encode()).hexdigest()])
    for row in enrichments:
        payload = canonical_json(row)
        insert("provider_enrichment_observations", [row["id"], row["fixture_id"], row["route"], stamp(row["available_at"]), row["coverage"], payload, hashlib.sha256(payload.encode()).hexdigest()])
    insert("provider_dataset_versions", [manifest["dataset_version"], manifest["base_dataset_version"], manifest["asof"], canonical_json(manifest)])
    for component in read_kind(directory, "goal-components"):
        payload = canonical_json(component)
        insert("provider_goal_components", [sha(component), component["created_at"], payload, hashlib.sha256(payload.encode()).hexdigest()])
    for feature in read_kind(directory, "features"):
        payload = canonical_json(feature)
        insert("live_feature_snapshots", [feature["id"], feature["fixture_id"], feature["cutoff_date"], feature["available_at"], feature["schema_version"], feature["dataset_version"], payload, hashlib.sha256(payload.encode()).hexdigest()])
    fixture_map = {r["observation_id"]: r for r in observations}
    for p in read_kind(directory, "predictions"):
        fixture = fixture_map[p["observation_id"]]
        payload = canonical_json(p)
        insert("live_prediction_snapshots", [p["snapshot_id"], p["fixture_id"], p["occurrence_id"], p["observation_id"], p["generated_at"], fixture["kickoff_utc"], p["feature_snapshot_id"], p.get("weights_version", p["model_version"]), p.get("runtime_version", runtime), "private_research", payload, hashlib.sha256(payload.encode()).hexdigest()])
    for result in read_kind(directory, "evaluations"):
        payload = canonical_json(result)
        insert("live_evaluation_revisions", [result["id"], result["prediction_id"], result["outcome_version"], summary["generated_at"], payload, hashlib.sha256(payload.encode()).hexdigest()])
    for detail in details:
        payload = canonical_json(detail)
        insert("live_match_details", [detail["id"], detail["fixture"]["fixture_id"], detail["generated_at"], detail["dataset_version"], payload, hashlib.sha256(payload.encode()).hexdigest()])
    from urllib.parse import parse_qs
    source_path = ROOT/"data/processed/api-football/request-ledger.json"
    calls = json.loads(source_path.read_text(encoding="utf-8")) if source_path.exists() else []
    archive_path = ROOT/"data/processed/live-research/source-coverage.json"
    archived = json.loads(archive_path.read_text(encoding="utf-8")) if archive_path.exists() else {}
    dates = sorted({parse_qs(r["route"].partition("?")[2])["date"][0] for r in calls if r["route"].startswith("/fixtures?date=") and r.get("response_sha256")})
    dates = sorted(set(dates+json.loads(archived.get("LIVE_SOURCE_DATES", "[]"))))
    captures = [r["first_seen_at"] for r in calls if r["route"].startswith("/fixtures?date=") and r.get("response_sha256")] + ([archived["LIVE_SOURCE_CAPTURED_AT"]] if archived.get("LIVE_SOURCE_CAPTURED_AT") else [])
    captured = stamp(max(captures)) if captures else manifest["asof"]
    for key, value in [("LIVE_IDENTITY_VERSION", sha(config)), ("LIVE_SOURCE_DATES", canonical_json(dates)), ("LIVE_SOURCE_CAPTURED_AT", captured)]:
        statements.append("INSERT OR REPLACE INTO settings VALUES("+quote(key)+","+quote(value)+");")
        records.append({"table": "settings", "values": [key, value]})
    summary_payload = canonical_json(summary)
    statements.append("INSERT OR REPLACE INTO performance VALUES('live-implementation',"+quote(summary_payload)+");")
    records.append({"table": "performance", "values": ["live-implementation", summary_payload]})
    batches, batch = [], []
    for record in records:
        if len(canonical_json({"records": batch+[record]}).encode()) > 80000 or len(batch) >= 20:
            if not batch:
                raise ValueError("live_record_too_large_for_signed_import")
            batches.append(batch)
            batch = []
        batch.append(record)
    if batch:
        batches.append(batch)
    write_json(ROOT/"data/processed/live-research/import-batches.json", batches)
    (ROOT/"db/seed-live-research.sql").write_text("\n".join(statements)+"\n", encoding="utf-8")


if __name__ == "__main__":
    build()
