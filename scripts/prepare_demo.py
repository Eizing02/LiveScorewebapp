"""Prepare an explicitly mocked fixture UI backed by real retrospective reports."""
import json
import shutil

from ml.models import LeagueState
from ml.pipeline import ROOT, digest, team_identity, write_json
from ml.registry import verify


def main():
    registry = json.loads((ROOT / "ml/models/registry.json").read_text())
    version = registry.get("latest_candidate", registry["candidates"][-1])
    meta = verify(version)
    states = json.loads((ROOT / "ml/models" / version / "baseline-state.json").read_text(encoding="utf-8"))
    report = json.loads((ROOT / "reports/backtest.json").read_text(encoding="utf-8"))
    quality = json.loads((ROOT / "data/processed/quality-report.json").read_text(encoding="utf-8"))
    public_report = {"mode": "historical_backtest", "dataset_version": report["dataset_version"], "source_commit": report["source_commit"], "final_holdout": {"start": report["final_holdout"]["start"], "end_exclusive": report["final_holdout"]["end_exclusive"], "metrics": report["final_holdout"]["metrics"]}, "selection": report["selection"], "quality": {k: quality[k] for k in ["accepted", "quarantined", "excluded", "quarantine_reasons", "per_league_season"]}, "limitations": report["limitations"]}
    statements = ["DELETE FROM predictions WHERE locked=0;", "INSERT OR IGNORE INTO leagues(id,source_code,name) VALUES('eng-premier','en.1','Premier League'),('esp-laliga','es.1','La Liga'),('de-bundesliga','de.1','Bundesliga');"]
    def quote(value):
        return "NULL" if value is None else "'" + str(value).replace("'", "''") + "'"
    def insert(table, values, mode="INSERT OR IGNORE"):
        statements.append(mode + " INTO " + table + " VALUES(" + ",".join(quote(v) for v in values) + ");")
    demos = [(1001, "en.1", "eng-premier", "Liverpool FC", "Arsenal FC", 40, 42), (1002, "es.1", "esp-laliga", "Real Madrid", "FC Barcelona", 9001, 9002), (1003, "de.1", "de-bundesliga", "FC Bayern München", "Borussia Dortmund", 9003, 9004)]
    feature_exports = []
    for provider_id, league, league_id, home, away, hid, aid in demos:
        match = {"home_id": team_identity(league, home)[0], "away_id": team_identity(league, away)[0], "date": "2026-10-26"}
        state = LeagueState.from_dict(states[league])
        state.start_season("2026-27")
        snapshot = state.snapshot(match)
        fixture_id = f"mock-{provider_id}"
        feature_hash = digest(snapshot)
        for pid, name in [(hid, home), (aid, away)]:
            insert("teams", [f"provider-{pid}", name, str(pid)])
        insert("fixtures", [fixture_id, None, league_id, "2026", f"provider-{hid}", f"provider-{aid}", "2026-10-26", "2026-10-26T19:00:00.000Z", "scheduled", None, None, "mock", None, "2026-10-25T00:00:00.000Z", "mock_fixture_with_stale_historical_features"])
        insert("features", [fixture_id, "features-v1", snapshot["information_cutoff_date"], json.dumps(snapshot), feature_hash], "INSERT OR REPLACE")
        p = snapshot["poisson"]
        insert("predictions", [f"{fixture_id}:poisson-v1:initial", fixture_id, "poisson-v1", "2026-10-25T00:00:00.000Z", snapshot["information_cutoff_date"], "initial", json.dumps(p["probabilities"]), p["expected_home_goals"], p["expected_away_goals"], json.dumps(p["top_scorelines"]), feature_hash, 0, "baseline_fallback"])
        feature_exports.append({"fixture_id": fixture_id, "payload": snapshot, "snapshot_hash": feature_hash, "kickoff_utc": "2026-10-26T19:00:00Z"})
    insert("performance", ["backtest", json.dumps(public_report)], "INSERT OR REPLACE")
    insert("model_versions", [version, meta["algorithm_selected"], meta["training_cutoff_exclusive"], meta["source_commit"], meta["training_dataset_version"], digest(meta), json.dumps(meta), "candidate"])
    (ROOT / "db/seed.sql").write_text("\n".join(statements) + "\n", encoding="utf-8")
    write_json(ROOT / "data/mock-feature-export.json", {"items": feature_exports})
    (ROOT / "apps/web/public").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "reports/calibration.png", ROOT / "apps/web/public/calibration.png")
    shutil.copyfile(ROOT / "data/processed/quality-report.json", ROOT / "reports/quality-report.json")
    shutil.copyfile(ROOT / "data/processed/quality-by-season.csv", ROOT / "reports/quality-by-season.csv")
    print(f"Prepared three MOCK fixtures, real holdout metrics, candidate {version}; no active model promoted.")


if __name__ == "__main__":
    main()
