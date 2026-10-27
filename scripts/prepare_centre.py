"""Seed fictitious schedules, genuine recent history and research model outputs."""
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from ml.evaluate import LogisticModel
from ml.expanded import CONFIG, OUTPUT
from ml.goal_markets import goal_markets
from ml.models import LeagueState
from ml.pipeline import ROOT, canonical_json, write_json
from ml.recent_evaluate import hashlib_file


def main():
    registry = json.loads((ROOT / "ml/models/recent-v2-registry.json").read_text(encoding="utf-8"))
    version = registry["candidate"]
    directory = ROOT / "ml/models" / version
    meta = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    for name, checksum in meta["checksums"].items():
        if hashlib_file(directory / name) != checksum:
            raise ValueError("candidate_artifact_checksum_mismatch")
    states = json.loads((directory / "baseline-state.json").read_text(encoding="utf-8"))
    logistic = LogisticModel.from_dict(json.loads((directory / "logistic.json").read_text(encoding="utf-8")))
    report = json.loads((ROOT / "reports/recent-v2/backtest.json").read_text(encoding="utf-8"))
    quality = report["quality"]
    benchmarks = ROOT / "reports/recent-v2/market-baseline-diagnostics.json"
    if benchmarks.exists():
        report["goal_market_baselines"] = json.loads(benchmarks.read_text(encoding="utf-8"))["metrics"]
    rows = [json.loads(line) for line in (OUTPUT / "accepted.jsonl").read_text(encoding="utf-8").splitlines()]
    statements = []

    def quote(value):
        return "NULL" if value is None else "'" + str(value).replace("'", "''") + "'"

    def insert(table, values, columns=None, replace=False):
        statement = ("INSERT OR REPLACE" if replace else "INSERT OR IGNORE") + " INTO " + table
        if columns:
            statement += "(" + ",".join(columns) + ")"
        statements.append(statement + " VALUES(" + ",".join(quote(v) for v in values) + ");")

    names, teams, team_dates, by_league = {}, {}, {}, defaultdict(list)
    for league, info in CONFIG["leagues"].items():
        insert("leagues", [info["id"], league, info["name"]], ["id", "source_code", "name"])
    for row in rows:
        by_league[row["league"]].append(row)
        for side in ["home", "away"]:
            team_id = row[side + "_id"]
            names[team_id] = row[side]
            teams[team_id] = row[side]
            team_dates[(row["league"], team_id)] = row["date"]
    for team_id, name in sorted(teams.items()):
        insert("teams", [team_id, name], ["id", "name"])
    for row in rows:
        insert("recent_results", [row["id"], quality["dataset_version"], row["league_id"], row["season"], row["date"], row["home_id"], row["away_id"], *row["goals"], row["quality"], canonical_json(row["provenance"])])
    generated = "2026-10-25T00:00:00.000Z"
    demo_start = datetime(2026, 10, 26, 11, tzinfo=timezone.utc)
    demos = []
    for index, (league, state_dict) in enumerate(sorted(states.items())):
        state = LeagueState.from_dict(state_dict)
        info = CONFIG["leagues"][league]
        latest_season = max(r["season"] for r in by_league[league])
        active = {r[side + "_id"] for r in by_league[league] if r["season"] == latest_season for side in ["home", "away"]}
        ordered = sorted(active, key=lambda team: (-state.elo.get(team, 1500), team))
        if len(ordered) < 2:
            continue
        home, away = ordered[0], ordered[-1]
        state.start_season("2026-27")
        kickoff = demo_start + timedelta(minutes=index * 45)
        fixture_id = "centre-" + league.replace(".", "-")
        demos.append((fixture_id, league, info, state, home, away, kickoff, "scheduled"))
    # Explicit clock-boundary examples, plus a postponed fixture.
    first = demos[0]
    for fixture_id, kickoff, status in [("centre-boundary-before", datetime(2026, 10, 26, 22, 59, tzinfo=timezone.utc), "scheduled"), ("centre-boundary-at", datetime(2026, 10, 26, 23, 0, tzinfo=timezone.utc), "scheduled"), ("centre-postponed", datetime(2026, 10, 26, 16, 0, tzinfo=timezone.utc), "postponed")]:
        demos.append((fixture_id, *first[1:6], kickoff, status))
    snapshots, fixture_exports = [], []
    for fixture_id, league, info, state, home, away, kickoff, status in demos:
        match_date = (kickoff + timedelta(hours=7)).date().isoformat()
        fixture_exports.append({"id": fixture_id, "league": league, "league_id": info["id"], "league_name": info["name"], "home_id": home, "away_id": away, "home": names[home], "away": names[away], "date": match_date, "season": "2026-27", "kickoff_utc": kickoff.isoformat(timespec="milliseconds").replace("+00:00", "Z"), "status": status, "quality": "clock_boundary_example" if fixture_id.startswith("centre-boundary") else "fictitious_fixture_unverified_historical_inputs"})
        features = state.snapshot({"home_id": home, "away_id": away, "date": match_date})
        poisson = features["poisson"]
        winner = report["selection"]["selected"]
        if winner == "logistic":
            probabilities = logistic.predict_proba([features["features"]])[0].tolist()
        elif winner in {"league", "elo", "poisson"}:
            probabilities = features["league_prior"] if winner == "league" else poisson["probabilities"] if winner == "poisson" else features["elo"]
        else:
            import xgboost as xgb
            from ml.evaluate import XGBoostModel
            booster = xgb.Booster()
            booster.load_model(directory / "xgboost.json")
            probabilities = XGBoostModel(booster).predict_proba([features["features"]])[0].tolist()
        insert("fixtures", [fixture_id, None, info["id"], "2026-27", home, away, match_date, kickoff.isoformat(timespec="milliseconds").replace("+00:00", "Z"), status, None, None, "mock_centre", None, generated, "fictitious_fixture_unverified_historical_inputs"])
        snapshot = {"fixture_id": fixture_id, "model_version": version + ":" + winner, "goal_model": "independent-poisson-v1", "generated_at": generated, "cutoff_date": features["information_cutoff_date"], "training_cutoff": CONFIG["asof_exclusive"], "dataset_version": quality["dataset_version"], "probabilities": probabilities, "poisson_probabilities": poisson["probabilities"], "home_rate": features["home_rate"], "away_rate": features["away_rate"], "scorelines": poisson["top_scorelines"], "markets": goal_markets(features["home_rate"], features["away_rate"]), "history_matches": features["history_matches"], "venue_matches": features["features"][7:9], "last_result_dates": [team_dates[(league, home)], team_dates[(league, away)]], "cold_start": features["cold_start"], "mode": "mock_research", "locked": True}
        snapshot["snapshot_id"] = fixture_id + ":" + version
        payload = canonical_json(snapshot)
        import hashlib
        insert("analysis_snapshots", [fixture_id + ":" + version, fixture_id, generated, features["information_cutoff_date"], version, payload, hashlib.sha256(payload.encode()).hexdigest(), "mock_research"])
        snapshots.append(snapshot)
    insert("settings", ["RECENT_RESEARCH_CANDIDATE", version], replace=True)
    statements.append("UPDATE fixtures SET quality='clock_boundary_example' WHERE source='mock_centre' AND id IN('centre-boundary-before','centre-boundary-at');")
    insert("performance", ["recent-quality", canonical_json(quality)], replace=True)
    payload = canonical_json(report)
    import hashlib
    report_key = hashlib.sha256(payload.encode()).hexdigest()
    parts = [payload[i:i+8000] for i in range(0, len(payload), 8000)]
    for index, part in enumerate(parts):
        insert("research_report_chunks", [report_key, index, part])
    insert("performance", ["recent-backtest", canonical_json({"chunked": True, "key": report_key, "parts": len(parts), "checksum": report_key})], replace=True)
    (ROOT / "db/seed-centre.sql").write_text("\n".join(statements) + "\n", encoding="utf-8")
    write_json(ROOT / "data/mock-centre-snapshots.json", {"fixtures": len(demos), "snapshots": snapshots, "mode": "mock_research", "all_schedules_fictitious": True})
    write_json(ROOT / "data/mock-centre-fixtures.json", fixture_exports)
    print(json.dumps({"history_rows": len(rows), "fictitious_fixtures": len(demos), "candidate": version, "live_api_requests": 0}))


if __name__ == "__main__":
    main()
