"""Five-year, multi-source result ledger; legacy evidence stays untouched."""
import csv
import hashlib
import json
import re
import subprocess
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from ml.pipeline import ALIASES, ROOT, digest, normalize_score, normalize_status, validate_time, write_json, write_jsonl

CONFIG = json.loads((ROOT / "ml/config/expanded_policy_v2.json").read_text(encoding="utf-8"))
OUTPUT = ROOT / "data/processed/recent-v2"


def identity(league, name):
    if not isinstance(name, str) or not name.strip() or name in {"TBD", "TBA", "N.N."}:
        raise ValueError("unresolved_team")
    name = ALIASES.get(league, {}).get(name, name).strip()
    return "team-" + digest([CONFIG["leagues"][league]["country"], name])[:16], name


def name_key(name):
    value = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    value = re.sub(r"\b(fc|afc|sc|sv|vfl|vfb|tsg|fsv|[0-9]+)\b", " ", value)
    return re.sub(r"[^a-z]", "", value)


GERMAN_ALIASES = {"DSC Arminia Bielefeld": "Arminia Bielefeld", "Borussia Mönchengladbach": "Borussia Mönchengladbach", "Bor. Mönchengladbach": "Borussia Mönchengladbach", "SpVgg Greuther Fürth": "SpVgg Greuther Fürth", "FC Schalke 04": "FC Schalke 04", "Fortuna Düsseldorf": "Fortuna Düsseldorf"}


def map_name(name, vocabulary):
    if name in vocabulary:
        return name, "exact"
    explicit = GERMAN_ALIASES.get(name)
    if explicit in vocabulary:
        return explicit, "explicit_alias"
    matches = [n for n in vocabulary if name_key(n) == name_key(name)]
    if len(matches) == 1:
        return matches[0], "normalized_exact_unique_unverified"
    raise ValueError("unresolved_cross_source_team")


def read_openfootball(source):
    commit = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if commit != CONFIG["source_commit"]:
        raise ValueError("source_commit_mismatch")
    if subprocess.check_output(["git", "-C", str(source), "status", "--porcelain"], text=True).strip():
        raise ValueError("source_worktree_modified")
    rows, held, manifest, vocabulary = [], [], [], defaultdict(set)
    for path in sorted(source.glob("*/*.json")):
        season = path.parent.name
        league = path.stem
        if league not in CONFIG["leagues"] or not re.fullmatch(r"202[1-6]-\d\d", season):
            continue
        payload = path.read_bytes()
        manifest.append({"source": "openfootball", "file": path.relative_to(source).as_posix(), "sha256": hashlib.sha256(payload).hexdigest(), "commit": commit, "license": "CC0-1.0"})
        for index, match in enumerate(json.loads(payload)["matches"]):
            record = {"source": "openfootball", "source_file": path.relative_to(source).as_posix(), "source_index": index, "league": league, "season": season, "source_record_id": digest([commit, str(path.relative_to(source)), index])}
            try:
                day = match["date"]
                date.fromisoformat(day)
                home_id, home = identity(league, match.get("team1"))
                away_id, away = identity(league, match.get("team2"))
                vocabulary[league].update([home, away])
                if home_id == away_id:
                    raise ValueError("same_team")
                # Knockout matches have different draw/extra-time regimes.
                if not re.fullmatch(r"(?:(?:Regular, )?Matchday \d+|\d+\. Round)", match.get("round", "")):
                    raise ValueError("non_regular_round")
                status = normalize_status(match.get("status"))
                if status != "result_recorded":
                    raise ValueError("status_" + status)
                goals, schema = normalize_score(match.get("score"))
                if goals is None:
                    raise ValueError("missing_score")
                rows.append({**record, "home_id": home_id, "away_id": away_id, "home": home, "away": away, "date": day, "goals": goals, "round": match["round"], "status": "result_recorded", "score_schema": schema, **validate_time(day, match.get("time")), "provenance": [{"source": "openfootball", "commit": commit, "file": record["source_file"], "index": index, "license": "CC0-1.0"}]})
            except (ValueError, KeyError, TypeError) as error:
                held.append({**record, "reason": str(error), "date": match.get("date"), "raw": match})
    return rows, held, manifest, vocabulary


def normalize_openliga(match, league, season, vocabulary, meta):
    if not match.get("matchIsFinished"):
        raise ValueError("unplayed_or_unconfirmed")
    results = [r for r in match.get("matchResults", []) if r.get("resultTypeKind") == "After90Minutes" or (not r.get("resultTypeKind") and r.get("resultTypeID") == 2)]
    if len(results) != 1:
        raise ValueError("missing_or_ambiguous_90_minute_score")
    score = results[0]
    goals, _ = normalize_score([score.get("pointsTeam1"), score.get("pointsTeam2")])
    home, hm = map_name(match["team1"]["teamName"], vocabulary)
    away, am = map_name(match["team2"]["teamName"], vocabulary)
    utc = datetime.fromisoformat(match["matchDateTimeUTC"].replace("Z", "+00:00"))
    if utc.utcoffset() is None:
        raise ValueError("missing_timezone")
    if match.get("timeZoneID") == "W. Europe Standard Time":
        local = datetime.fromisoformat(match["matchDateTime"])
        if local.tzinfo is None and utc.astimezone(ZoneInfo("Europe/Berlin")).replace(tzinfo=None) != local:
            raise ValueError("source_local_utc_conflict")
    day = match["matchDateTime"][:10]
    date.fromisoformat(day)
    home_id, _ = identity(league, home)
    away_id, _ = identity(league, away)
    if home_id == away_id:
        raise ValueError("same_team")
    return {"source": "openligadb", "source_record_id": f'openligadb-{match["matchID"]}', "league": league, "season": season, "home_id": home_id, "away_id": away_id, "home": home, "away": away, "date": day, "goals": goals, "round": f'Matchday {match["group"]["groupOrderID"]}', "status": "result_recorded", "kickoff_utc": utc.astimezone(timezone.utc).isoformat(), "timezone_status": "provider_explicit_utc_unverified", "time_precision": "minute", "score_schema": "openliga_after90", "provenance": [{"source": "openligadb", "record_id": match["matchID"], "sha256": meta["sha256"], "url": meta["url"], "license": "ODbL-1.0", "mapping_methods": [hm, am]}]}


def merge_results(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["league"], row["season"], row["home_id"], row["away_id"])].append(row)
    accepted, held, duplicates = [], [], []
    for key, group in sorted(groups.items()):
        dates = {r["date"] for r in group}
        scores = {tuple(r["goals"]) for r in group}
        if len(dates) != 1 or len(scores) != 1:
            reason = "cross_source_date_conflict" if len(dates) != 1 else "cross_source_score_conflict"
            held.extend({**r, "reason": reason} for r in group)
            continue
        ordered = sorted(group, key=lambda r: (r["source"] != "openfootball", r["source_record_id"]))
        row = dict(ordered[0])
        row["provenance"] = [p for r in ordered for p in r["provenance"]]
        row["id"] = "recent-" + digest([*key, row["date"]])[:24]
        timed = next((r for r in ordered if r.get("kickoff_utc")), None)
        if timed:
            row.update({k: timed[k] for k in ["kickoff_utc", "timezone_status", "time_precision"]})
        row["cross_source_agreement"] = len({r["source"] for r in group}) > 1
        row["quality"] = "cross_source_agreement_unverified" if row["cross_source_agreement"] else "single_source_unverified"
        accepted.append(row)
        duplicates.extend({"source_record_id": r["source_record_id"], "retained_id": row["id"], "reason": "duplicate_evidence_merged"} for r in ordered[1:])
    return accepted, held, duplicates


def run(output=OUTPUT):
    output.mkdir(parents=True, exist_ok=True)
    rows, held, manifest, vocabulary = read_openfootball(ROOT / "data/source/openfootball")
    for path in sorted((ROOT / "data/source/additional/openligadb").glob("*.json")):
        if path.name.endswith(".meta.json"):
            continue
        meta = json.loads(path.with_suffix(".json.meta.json").read_text(encoding="utf-8"))
        if hashlib.sha256(path.read_bytes()).hexdigest() != meta["sha256"]:
            raise ValueError("additional_source_checksum_mismatch")
        shortcut, year = path.stem.split("-")
        league = {"bl1": "de.1", "bl2": "de.2"}[shortcut]
        season = f"{year}-{str(int(year)+1)[2:]}"
        manifest.append({"source": "openligadb", **meta})
        for match in json.loads(path.read_bytes()):
            try:
                rows.append(normalize_openliga(match, league, season, vocabulary[league], meta))
            except (ValueError, KeyError, TypeError) as error:
                held.append({"source": "openligadb", "league": league, "season": season, "reason": str(error), "source_record_id": match.get("matchID"), "raw": match})
    merged, conflicts, duplicates = merge_results(rows)
    held.extend(conflicts)
    before_asof = [r for r in merged if r["date"] < CONFIG["asof_exclusive"]]
    counts = Counter((r["league"], r["season"]) for r in before_asof)
    accepted, excluded = [], []
    for row in merged:
        league = CONFIG["leagues"][row["league"]]
        expected = league["expected"]
        for key, value in league.items():
            if key.startswith("expected_before_") and int(row["season"][:4]) < int(key.removeprefix("expected_before_")):
                expected = value
        if not CONFIG["window_start"] <= row["date"] < CONFIG["asof_exclusive"]:
            excluded.append({**row, "reason": "outside_five_year_window"})
        elif row["season"] != CONFIG["current_season"] and counts[(row["league"], row["season"])] < expected * CONFIG["closed_season_minimum_coverage"]:
            held.append({**row, "reason": "incomplete_closed_season"})
        else:
            accepted.append({**row, "league_id": league["id"], "training_accepted": True, "season_scope": "observed_current_prefix_unverified_coverage" if row["season"] == CONFIG["current_season"] else "closed_season_coverage_passed", "date_status": "source_recorded_unverified"})
    accepted.sort(key=lambda r: (r["date"], r["league"], r["id"]))
    if len({r["id"] for r in accepted}) != len(accepted):
        raise ValueError("duplicate_internal_identity")
    seasons = []
    for league, season in sorted({(r["league"], r["season"]) for r in accepted + held + excluded}):
        a = [r for r in accepted if r["league"] == league and r["season"] == season]
        seasons.append({"league": league, "name": CONFIG["leagues"][league]["name"], "season": season, "accepted": len(a), "quarantined": sum(r["league"] == league and r["season"] == season for r in held), "excluded": sum(r["league"] == league and r["season"] == season for r in excluded), "cross_source_agreement": sum(r["cross_source_agreement"] for r in a)})
    report = {"version": CONFIG["version"], "window_start": CONFIG["window_start"], "asof_exclusive": CONFIG["asof_exclusive"], "dataset_version": digest(accepted), "policy_sha256": digest(CONFIG), "source_commit": CONFIG["source_commit"], "accepted": len(accepted), "quarantined": len(held), "excluded": len(excluded), "duplicate_evidence_merged": len(duplicates), "cross_source_agreement": sum(r["cross_source_agreement"] for r in accepted), "quarantine_reasons": dict(Counter(r["reason"] for r in held)), "per_league_season": seasons, "licenses": {"openfootball": "CC0-1.0", "openligadb": "ODbL-1.0; attribution and share-alike for adapted database"}, "attribution": "OpenFootball contributors; OpenLigaDB community https://www.openligadb.de/ (ODbL-1.0)", "limitations": ["Retrospective records, not first-seen snapshots; dates and provider identity remain unverified", "Agreement is corroboration, not proof of independent sources", "Incomplete closed seasons withheld; current season contains observed prefix with unverified completeness", "Only regular league rounds accepted; playoffs/awards/missing results not invented", "Legacy 66 EPL2019/20 anomalies remain untouched outside the new time window", "No target-match post-kickoff statistics or odds used as features"]}
    for name, values in [("accepted", accepted), ("quarantine", held), ("excluded", excluded), ("duplicates", duplicates)]:
        write_jsonl(output / f"{name}.jsonl", values)
    write_json(output / "quality-report.json", report)
    write_json(output / "source-manifest.json", manifest)
    write_json(output / "correction-log.json", {"corrections": [], "conflicts_quarantined": len(conflicts), "method": "No silent date/score replacements"})
    with (output / "quality-by-season.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(seasons[0]))
        writer.writeheader()
        writer.writerows(seasons)
    write_json(ROOT / "reports/recent-v2-quality.json", report)
    print(json.dumps({k: report[k] for k in ["accepted", "quarantined", "duplicate_evidence_merged", "cross_source_agreement", "quarantine_reasons"]}))
    return report


if __name__ == "__main__":
    run()
