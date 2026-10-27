"""Pinned source -> quality ledger -> conservative accepted dataset. Standard library only."""
import argparse
import csv
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "ml/config/policy.json"
POLICY = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
ALIASES = json.loads((ROOT / "ml/config/aliases.json").read_text(encoding="utf-8"))


def canonical_json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_jsonl(path, rows):
    Path(path).write_text("".join(canonical_json(r) + "\n" for r in rows), encoding="utf-8")


def normalize_score(value):
    scores = value.get("ft") if isinstance(value, dict) else value
    if scores is None:
        return None, "missing"
    if not (isinstance(scores, list) and len(scores) == 2 and all(type(v) is int and v >= 0 for v in scores)):
        raise ValueError("invalid_score")
    return scores, "ft_object" if isinstance(value, dict) else "numeric_array"


def normalize_status(value):
    return {"canceled": "cancelled", "cancelled": "cancelled", "postponed": "postponed", "awarded": "awarded", "abandoned": "abandoned"}.get(value, "unverified" if value else "result_recorded")


def validate_time(day, time):
    date.fromisoformat(day)
    # Bare clock strings do not establish a timezone. Keep the original, no invented UTC.
    if not time:
        return {"kickoff_utc": None, "time_precision": "date", "timezone_status": "unverified"}
    parts = time.split(" UTC")
    try:
        datetime.strptime(parts[0], "%H:%M")
        if len(parts) == 2:
            offset = int(parts[1])
            if not -12 <= offset <= 14:
                raise ValueError("invalid_offset")
            from datetime import timedelta, timezone
            dt = datetime.strptime(day + " " + parts[0], "%Y-%m-%d %H:%M").replace(tzinfo=timezone(timedelta(hours=offset)))
            return {"kickoff_utc": dt.astimezone(timezone.utc).isoformat(), "time_precision": "minute", "timezone_status": "source_explicit_offset_unverified"}
    except (ValueError, TypeError) as exc:
        raise ValueError("invalid_time") from exc
    return {"kickoff_utc": None, "time_precision": "date", "timezone_status": "unverified"}


def team_identity(league, name):
    if not isinstance(name, str) or not name.strip() or name in {"N.N.", "TBD", "TBA"}:
        raise ValueError("unresolved_team")
    canonical = ALIASES.get(league, {}).get(name, name)
    country = POLICY["leagues"].get(league, {}).get("country", league.split(".")[0])
    return "team-" + digest([country, canonical])[:16], canonical


def deduplicate(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[(r["league"], r["season"], r["home_id"], r["away_id"], r["date"])].append(r)
    accepted, removed = [], []
    for group in groups.values():
        if len(group) == 1:
            accepted.extend(group)
            continue
        results = {tuple(r["goals"]) for r in group if r["goals"] is not None}
        statuses = {r["status"] for r in group}
        if len(results) > 1 or len(statuses) > 1:
            removed.extend({**r, "reason": "conflicting_duplicate"} for r in group)
        else:
            ordered = sorted(group, key=lambda r: (r["goals"] is None, r["source_index"]))
            accepted.append(ordered[0])
            removed.extend({**r, "reason": "duplicate_merged", "retained_id": ordered[0]["source_record_id"]} for r in ordered[1:])
    return accepted, removed


def import_dataset(source, output):
    source, output = Path(source), Path(output)
    commit = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if commit != POLICY["source_commit"]:
        raise ValueError("source_commit_mismatch")
    if subprocess.check_output(["git", "-C", str(source), "status", "--porcelain", "--untracked-files=all"], text=True).strip():
        raise ValueError("source_worktree_modified")
    output.mkdir(parents=True, exist_ok=True)
    normalized, quarantine, exclusions, manifest, identities = [], [], [], [], {}
    total = 0
    for file in sorted(source.glob("*/*.json")):
        relative = file.relative_to(source).as_posix()
        raw = file.read_bytes()
        manifest.append({"path": relative, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
        data = json.loads(raw)
        season, filename = relative.split("/")
        league = filename.removesuffix(".json").removesuffix("-full")
        for index, m in enumerate(data["matches"]):
            total += 1
            record = {"source_file": relative, "source_index": index, "source_commit": commit, "source_record_id": digest([commit, relative, index]), "league": league, "season": season}
            if filename.endswith("-full.json"):
                exclusions.append({**record, "reason": "full_enrichment_excluded"})
                continue
            try:
                day = m.get("date", "")
                time = validate_time(day, m.get("time"))
                goals, score_schema = normalize_score(m.get("score"))
                home_id, home = team_identity(league, m.get("team1"))
                away_id, away = team_identity(league, m.get("team2"))
                if home_id == away_id:
                    raise ValueError("same_team")
                if league == "en.1" and season == "2019-20" and day < "2019-08-09":
                    raise ValueError("epl_2019_20_misdated_66")
                for raw_name, team_id, canonical in [(m["team1"], home_id, home), (m["team2"], away_id, away)]:
                    identities[(league, raw_name)] = {"league": league, "source_name": raw_name, "canonical_id": team_id, "canonical_name": canonical, "method": "explicit_alias" if raw_name in ALIASES.get(league, {}) else "exact_source_name", "cross_provider_status": "unverified"}
                normalized.append({**record, "id": "match-" + digest([league, season, home_id, away_id, m.get("round"), m.get("stage")])[:24], "home_id": home_id, "away_id": away_id, "home": home, "away": away, "date": day, "source_time": m.get("time"), **time, "date_status": "source_recorded_unverified", "goals": goals, "score_schema": score_schema, "status": normalize_status(m.get("status")), "round": m.get("round"), "quality": "unverified_source_result"})
            except (ValueError, TypeError, KeyError) as exc:
                quarantine.append({**record, "reason": str(exc), "raw": m})
    normalized, duplicates = deduplicate(normalized)
    quarantine.extend(duplicates)
    # A same ordered pair on multiple dates is ambiguous (reschedule, replay, or format).
    pair_groups = defaultdict(list)
    for r in normalized:
        if r["league"] in POLICY["leagues"]:
            pair_groups[(r["league"], r["season"], r["home_id"], r["away_id"])].append(r)
    ambiguous = {r["source_record_id"] for g in pair_groups.values() if len(g) > 1 for r in g}
    candidates = []
    for r in normalized:
        key = f'{r["league"]}/{r["season"]}'
        reason = None
        if r["source_record_id"] in ambiguous:
            reason = "rescheduled_pair_unresolved"
        elif r["status"] != "result_recorded":
            reason = "status_" + r["status"]
        elif r["goals"] is None:
            reason = "missing_score"
        elif r["date"] >= POLICY["asof_date_exclusive"]:
            reason = "future_or_asof_date"
        elif key in POLICY["exclude_seasons"]:
            reason = "season_chronology_hold"
        elif r["league"] not in POLICY["leagues"]:
            exclusions.append({**r, "reason": "outside_mvp_leagues"})
            continue
        if reason:
            quarantine.append({**r, "reason": reason})
        else:
            candidates.append(r)
    counts = Counter((r["league"], r["season"]) for r in candidates)
    accepted = []
    for r in candidates:
        expected = POLICY["leagues"][r["league"]]["expected_matches"]
        if counts[(r["league"], r["season"])] / expected < POLICY["minimum_season_completeness"]:
            quarantine.append({**r, "reason": "incomplete_season"})
        else:
            r["league_id"] = POLICY["leagues"][r["league"]]["id"]
            r["training_accepted"] = True
            accepted.append(r)
    accepted.sort(key=lambda r: (r["date"], r["league"], r["id"]))
    assert len({r["id"] for r in accepted}) == len(accepted), "duplicate internal fixture id"
    assert len(accepted) + len(quarantine) + len(exclusions) == total
    dataset_version = digest(accepted)
    per_season = []
    for league, season in sorted({(r["league"], r["season"]) for r in accepted + quarantine + exclusions}):
        per_season.append({"league": league, "season": season, "accepted": sum(r["league"] == league and r["season"] == season for r in accepted), "quarantined": sum(r["league"] == league and r["season"] == season for r in quarantine), "excluded": sum(r["league"] == league and r["season"] == season for r in exclusions)})
    report = {"source_commit": commit, "source_license": "CC0-1.0", "dataset_version": dataset_version, "policy_sha256": digest(POLICY), "aliases_sha256": digest(ALIASES), "total_source_rows": total, "accepted": len(accepted), "quarantined": len(quarantine), "excluded": len(exclusions), "quarantine_reasons": dict(Counter(r["reason"] for r in quarantine)), "exclusion_reasons": dict(Counter(r["reason"] for r in exclusions)), "per_league_season": per_season, "quality_scope": "Accepted for date-batched experimental training, NOT externally verified results/timezones or production provider identity. Source dates may contain undetected errors.", "corrections_applied": 0}
    write_jsonl(output / "accepted.jsonl", accepted)
    write_jsonl(output / "quarantine.jsonl", quarantine)
    write_jsonl(output / "excluded.jsonl", exclusions)
    write_json(output / "quality-report.json", report)
    write_json(output / "source-manifest.json", manifest)
    write_json(output / "identity-mapping.json", list(identities.values()))
    write_json(output / "correction-log.json", {"version": 1, "corrections": [], "pending": [{"issue": "EPL2019-20 dates", "quarantined_anomalies": 66, "entire_season_withheld": True, "evidence": "https://www.premierleague.com/en/news/1702418", "action": "No dates changed. Require match-specific corroboration before correction."}]})
    with (output / "quality-by-season.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["league", "season", "accepted", "quarantined", "excluded"])
        writer.writeheader()
        writer.writerows(per_season)
    return report


def load_accepted(directory=None):
    file = Path(directory or ROOT / "data/processed") / "accepted.jsonl"
    return [json.loads(line) for line in file.read_text(encoding="utf-8").splitlines()]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=ROOT / "data/source/openfootball")
    parser.add_argument("--output", type=Path, default=ROOT / "data/processed")
    args = parser.parse_args()
    result = import_dataset(args.source, args.output)
    print(canonical_json({k: result[k] for k in ["dataset_version", "accepted", "quarantined", "excluded", "quarantine_reasons"]}))
