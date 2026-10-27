"""Append-only observations; verified label conflicts are quarantined, never overwritten."""
import json
from pathlib import Path

from ml.expanded import OUTPUT
from ml.live.normalize import LEAGUES, mapping_config, moment, normalize_enrichment, normalize_fixture, sha
from ml.pipeline import ROOT, canonical_json, write_json

DIRECTORY = ROOT/"data/processed/live-research"
SOURCE = ROOT/"data/processed/api-football"


def write_once(directory, kind, value):
    path = Path(directory)/kind/(sha(value)+".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json(value)+"\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != payload:
            raise ValueError("live_record_immutable")
        return
    with path.open("x", encoding="utf-8") as stream:
        stream.write(payload)


def read_kind(directory, kind):
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((Path(directory)/kind).glob("*.json"))]


def ingest(directory=DIRECTORY, source=SOURCE, config=None):
    config = config or mapping_config()
    ledger_path = Path(source)/"request-ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else []
    imported, held, enrichment = 0, 0, 0
    for call in ledger:
        digest, seen = call.get("response_sha256"), call.get("first_seen_at")
        if not digest or not seen:
            continue
        path = Path(source)/"responses"/(digest+".json")
        import hashlib
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("provider_response_hash_mismatch")
        payload = json.loads(path.read_text(encoding="utf-8"))
        route, _, query = call["route"].partition("?")
        if route == "/fixtures":
            for raw in payload.get("response", []):
                if raw.get("league", {}).get("id") not in LEAGUES:
                    continue
                try:
                    value = normalize_fixture(raw, seen, digest, config)
                    write_once(directory, "observations", value)
                    imported += 1
                except (KeyError, TypeError, ValueError) as error:
                    write_once(directory, "quarantine", {"provider_fixture_id": raw.get("fixture", {}).get("id"), "source_sha256": digest, "first_seen_at": seen, "reason": str(error)})
                    held += 1
        elif route in {"/fixtures/statistics", "/fixtures/players", "/fixtures/lineups", "/injuries", "/predictions"}:
            from urllib.parse import parse_qs
            target = parse_qs(query).get("fixture", [])
            if len(target) != 1:
                continue
            value = normalize_enrichment(route, payload, seen, digest, "api-football-"+target[0])
            write_once(directory, "enrichments", value)
            enrichment += 1
        elif route == "/fixtures/headtohead":
            from urllib.parse import parse_qs
            try:
                pair = {int(v) for v in parse_qs(query)["h2h"][0].split("-")}
            except (KeyError, ValueError):
                continue
            candidates = [r for r in read_kind(directory, "observations") if {r["home_provider_id"], r["away_provider_id"]} == pair]
            if candidates:
                target = min(candidates, key=lambda r: abs((moment(r["kickoff_utc"])-moment(seen)).total_seconds()))
                value = normalize_enrichment(route, payload, seen, digest, target["fixture_id"])
                write_once(directory, "enrichments", value)
                enrichment += 1
    return {"observations_ingested": imported, "enrichment_responses": enrichment, "structural_quarantine": held}


def latest_observations(observations, asof):
    latest = {}
    for row in observations:
        if moment(row["first_seen_at"]) > moment(asof):
            continue
        previous = latest.get(row["fixture_id"])
        if previous is None or (moment(row["first_seen_at"]), row["observation_id"]) > (moment(previous["first_seen_at"]), previous["observation_id"]):
            latest[row["fixture_id"]] = row
    return list(latest.values())


def accepted_history(observations, asof, base=None):
    base = base if base is not None else [json.loads(line) for line in (OUTPUT/"accepted.jsonl").read_text(encoding="utf-8").splitlines()]
    result = list(base)
    pairs = {(r["league"], r["season"], r["home_id"], r["away_id"]): r for r in base}
    held, duplicate = [], 0
    for row in latest_observations(observations, asof):
        if row["status"] != "finished" or row["score_90"] is None or row["quarantine_reasons"] or row["mapping_status"] != "reviewed":
            continue
        key = (row["league"], row["season"], row["home_id"], row["away_id"])
        if key in pairs:
            existing = pairs[key]
            if existing["date"] == row["date"] and existing["goals"] == row["score_90"]:
                duplicate += 1
            else:
                held.append({"fixture_id": row["fixture_id"], "reason": "historical_identity_date_or_score_conflict", "observation_id": row["observation_id"], "original_id": existing["id"]})
            continue
        known = [o for o in observations if o["fixture_id"] == row["fixture_id"] and o["occurrence_id"] == row["occurrence_id"] and o["status"] == "finished" and o["score_90"] == row["score_90"] and not o["quarantine_reasons"] and moment(o["first_seen_at"]) <= moment(asof)]
        label_source = min(known, key=lambda o: (moment(o["first_seen_at"]), o["observation_id"]))
        value = {"id": row["fixture_id"], "league": row["league"], "season": row["season"], "date": row["date"], "home_id": row["home_id"], "away_id": row["away_id"], "home": row["home"], "away": row["away"], "goals": row["score_90"], "quality": "provider_recorded_reviewed_mapping", "available_at": label_source["first_seen_at"], "observation_id": label_source["observation_id"]}
        result.append(value)
        pairs[key] = value
    result.sort(key=lambda r: (r["date"], r["league"], r["id"]))
    manifest = {"base_dataset_version": json.loads((OUTPUT/"quality-report.json").read_text(encoding="utf-8"))["dataset_version"], "base_rows": len(base), "accepted_new_rows": len(result)-len(base), "duplicates_agreed": duplicate, "conflicts": held, "asof": asof, "new_result_ids": [r["observation_id"] for r in result if r.get("observation_id")], "training_labels_not_retrained": True}
    manifest["dataset_version"] = sha([manifest["base_dataset_version"], manifest["new_result_ids"]])
    return result, manifest


def save_manifest(manifest, directory=DIRECTORY, matches=None):
    if matches is not None:
        import hashlib
        payload = "".join(canonical_json(r)+"\n" for r in matches)
        path = Path(directory)/"training-datasets"/(manifest["dataset_version"]+".jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_text(encoding="utf-8") != payload:
                raise ValueError("training_dataset_version_immutable")
        else:
            with path.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(payload)
        manifest.update({"accepted_training_rows": len(matches), "dataset_content_sha256": hashlib.sha256(payload.encode()).hexdigest(), "dataset_file": path.relative_to(Path(directory)).as_posix()})
    write_once(directory, "datasets", manifest)
    write_json(ROOT/"reports/live-research/latest-dataset.json", manifest)
