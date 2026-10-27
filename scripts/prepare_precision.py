"""Import a research report and score the existing fictitious schedule, never promote."""
import argparse
import hashlib
import json
from datetime import datetime, timezone

from ml.pipeline import ROOT, canonical_json, write_json
from ml.precision_predict import PrecisionEngine


def main(mock_clock=None):
    engine = PrecisionEngine()
    pointer = json.loads((ROOT/"reports/precision-v3/latest.json").read_text(encoding="utf-8"))
    report = json.loads((ROOT/pointer["report"]).read_text(encoding="utf-8"))
    from scripts.precision_diagnostics import build_diagnostics
    report["diagnostics"] = build_diagnostics()
    fixtures = json.loads((ROOT/"data/mock-centre-fixtures.json").read_text(encoding="utf-8"))
    recorded = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    generated = mock_clock or recorded
    if mock_clock:
        parsed = datetime.fromisoformat(mock_clock.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("mock_clock_requires_timezone")
        generated = parsed.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    statements, snapshots = [], []
    def quote(value):
        return "'"+str(value).replace("'", "''")+"'"
    def insert(table, values, replace=False):
        statements.append(("INSERT OR REPLACE" if replace else "INSERT OR IGNORE")+" INTO "+table+" VALUES("+",".join(quote(v) for v in values)+");")
    for fixture in fixtures:
        if generated >= fixture["kickoff_utc"]:
            continue
        snapshot = engine.predict(fixture, generated)
        snapshot["record_created_at"] = recorded
        snapshot["timestamp_basis"] = "simulated_mock_clock" if mock_clock else "actual_generation_clock"
        snapshot["snapshot_id"] = fixture["id"]+":"+engine.version+":"+hashlib.sha256(generated.encode()).hexdigest()[:8]
        payload = canonical_json(snapshot)
        insert("analysis_snapshots", [snapshot["snapshot_id"], fixture["id"], generated, snapshot["cutoff_date"], engine.version, payload, hashlib.sha256(payload.encode()).hexdigest(), "mock_research"])
        snapshots.append(snapshot)
    payload = canonical_json(report)
    key = hashlib.sha256(payload.encode()).hexdigest()
    parts = [payload[i:i+8000] for i in range(0, len(payload), 8000)]
    for i, part in enumerate(parts):
        insert("research_report_chunks", [key, i, part])
    insert("performance", ["precision-v3", canonical_json({"chunked": True, "key": key, "parts": len(parts), "checksum": key})], replace=True)
    if snapshots:
        insert("settings", ["RECENT_RESEARCH_CANDIDATE", engine.version], replace=True)
    destination = ROOT/"db/seed-precision.sql"
    destination.write_text("\n".join(statements)+"\n", encoding="utf-8")
    write_json(ROOT/"data/mock-precision-snapshots.json", {"generated_at": generated, "model": engine.version, "snapshots": snapshots, "mode": "mock_research", "production_model_promoted": False})
    print(json.dumps({"version": engine.version, "snapshots": len(snapshots), "research_eligible": sum(s["research_eligible"] for s in snapshots), "generated_at": generated, "production_model_promoted": False}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock-clock", help="Explicit simulated clock for fictitious demo fixtures only; never a prospective record")
    args = parser.parse_args()
    main(args.mock_clock)
