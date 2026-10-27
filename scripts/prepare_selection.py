"""Import immutable, already evaluated research evidence into LOCAL demo D1 seed SQL."""
import json
import shutil

from ml.pipeline import ROOT, digest, load_accepted


def main():
    directory = ROOT / "reports/selection-v1"
    policy = json.loads((directory / "frozen-policy.json").read_text(encoding="utf-8"))
    selection = json.loads((directory / "selection-before-test.json").read_text(encoding="utf-8"))
    test = json.loads((directory / "new-test.json").read_text(encoding="utf-8"))
    accepted = load_accepted()
    if digest(accepted) != policy["dataset_version"] or digest(selection) != test["selection_sha256"] or digest(policy) != test["policy_sha256"]:
        raise ValueError("immutable_research_evidence_mismatch")
    matches = {r["id"]: r for r in accepted}
    features = {r["id"]: r for r in [json.loads(line) for line in (ROOT / "data/processed/features.jsonl").read_text(encoding="utf-8").splitlines()]}
    rows = [json.loads(line) for line in (directory / "new-test-predictions.jsonl").read_text(encoding="utf-8").splitlines()]
    if len(rows) != test["n_all"] or sum(r["decision"]["selected"] for r in rows) != test["selected_result"]["n"]:
        raise ValueError("research_row_counts_mismatch")
    run_id = policy["version"] + ":" + digest([digest(policy), test["selection_sha256"]])[:12]
    payload = {"run_id": run_id, "policy": policy, "selection": selection, "test": test, "publication_state": "research_only", "live_blockers": ["filter_confirmation_sample_too_small", "source_dates_and_timezones_unverified", "no_verified_fresh_live_provider_data", "no_approved_active_model"], "candidate_metrics_are_validation_only": True}
    statements = []

    def quote(value):
        return "'" + str(value).replace("'", "''") + "'"

    def insert(table, values):
        statements.append("INSERT OR IGNORE INTO " + table + " VALUES(" + ",".join(quote(v) for v in values) + ");")

    insert("filter_research_runs", [run_id, digest(policy), test["selection_sha256"], policy["dataset_version"], *test["period"], json.dumps(payload, ensure_ascii=False), 1])
    for row in rows:
        match = matches[row["id"]]
        feature = features[row["id"]]
        if feature["information_cutoff_date"] != row["information_cutoff_date"] or row["information_cutoff_date"] >= row["date"]:
            raise ValueError("research_feature_cutoff_mismatch")
        choice = row["decision"].get("choice")
        if choice is None:
            choice = max(range(3), key=lambda c: row["probabilities_calibrated"][c])
        detail = {**row, "home": match["home"], "away": match["away"], "goals": match["goals"], "venue_matches": {"home": feature["features"][7], "away": feature["features"][8]}, "publication_state": "research_only", "source_quality": "unverified_source_result", "kickoff_utc": None, "date_precision": "date_only", "stress_state": "not_used_by_selected_rule", "live_blockers": payload["live_blockers"]}
        insert("filter_research_decisions", [run_id, row["id"], row["league"], row["date"], match["home"], match["away"], choice, row["target"], int(row["decision"]["selected"]), json.dumps(detail, ensure_ascii=False)])
    (ROOT / "db/seed-selection.sql").write_text("\n".join(statements) + "\n", encoding="utf-8")
    public = ROOT / "apps/web/public"
    public.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(directory / "filter-tradeoff.png", public / "filter-tradeoff.png")
    print(f"Prepared immutable research run {run_id}: {len(rows)} historical decisions. No model promotion or network.")


if __name__ == "__main__":
    main()
