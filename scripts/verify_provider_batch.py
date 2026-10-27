"""Bounded optional batch/date-window proof; uses the same signed quota broker."""
import argparse
import json
from datetime import datetime, timezone

from ml.pipeline import ROOT, write_json
from scripts.api_football_probe import Probe, ProbeError, load_key


class BatchProbe(Probe):
    allowed_routes = frozenset({"/fixtures", "/injuries"})


def run(execute=False):
    if not execute:
        print(json.dumps({"mode": "dry_run", "maximum_requests": 3, "automatic_activation": False}))
        return
    probe = BatchProbe(load_key())
    previous = [r for r in probe.ledger if "x-ratelimit-requests-remaining" in r.get("rate_headers", {})]
    if not previous or probe.clock()-previous[-1]["attempted_at"] > 1800:
        raise ValueError("fresh_quota_observation_required")
    probe.remaining = previous[-1]["rate_headers"]["x-ratelimit-requests-remaining"]
    tasks = [("fixture_ids", "/fixtures", {"ids": "1557441-1570426"}), ("injury_ids", "/injuries", {"ids": "1570426"}), ("next_date", "/fixtures", {"date": "2026-10-27", "timezone": "Asia/Bangkok"})]
    results = []
    for name, route, query in tasks:
        item = {"name": name, "route": route, "query": query}
        try:
            payload = probe.get(route, query)
            rows = payload.get("response", [])
            item.update({"status": "verified_nonempty" if rows else "empty_inconclusive", "response_rows": len(rows), "available_at": probe.calls[-1].get("first_seen_at"), "response_sha256": probe.calls[-1].get("response_sha256")})
            if name == "fixture_ids":
                item["embedded_fields"] = sorted(set().union(*(set(r) & {"events", "lineups", "statistics", "players"} for r in rows)))
        except ProbeError as error:
            item.update({"status": "unavailable", "reason": str(error).replace(probe.key, "[REDACTED]")})
        results.append(item)
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "samples": results, "requests_actual": len(probe.calls), "calls": probe.calls, "remaining_conservative": probe.remaining, "batch_enabled_automatically": False, "model_promoted": False}
    write_json(ROOT/"reports/live-research/optional-batch-proof.json", report)
    print(json.dumps({"results": [{k: r.get(k) for k in ["name", "status", "response_rows", "reason"]} for r in results], "actual_requests": len(probe.calls), "remaining_conservative": probe.remaining}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    run(parser.parse_args().execute)
