"""Explicit local collector execution; cloud writes/deployment are never implicit."""
import argparse
import json
import urllib.parse

from ml.live.pipeline import build
from ml.pipeline import ROOT
from ml.provider_broker import BrokerClient, local_settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--import-local", action="store_true")
    parser.add_argument("--import-results", action="store_true")
    parser.add_argument("--hydrate", action="store_true")
    parser.add_argument("--enrich", action="store_true")
    parser.add_argument("--archive-finished", action="store_true")
    parser.add_argument("--approved-remote", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({"mode": "dry_run", "maximum_provider_http_requests": (3 if args.refresh else 0)+(4 if args.enrich else 0), "maximum_billable_requests": (2 if args.refresh else 0)+(3 if args.enrich else 0), "local_import": args.import_local, "remote_import_requested": args.import_results, "model_promoted": False}))
        return
    settings = local_settings()
    parsed = urllib.parse.urlsplit(settings.get("PROVIDER_BROKER_URL", "http://127.0.0.1:8787"))
    remote = parsed.hostname not in {"127.0.0.1", "localhost"}
    approved_remote = args.approved_remote and settings.get("REMOTE_RESEARCH_IMPORT_APPROVED") == "true" and parsed.scheme == "https"
    if remote and (not approved_remote or args.import_local):
        raise ValueError("this_command_only_authorizes_local_broker_and_D1")
    broker = BrokerClient(settings) if args.hydrate or args.import_local or args.import_results else None
    if args.hydrate:
        from ml.live.ledger import DIRECTORY, write_once
        from ml.pipeline import write_json
        for kind in ["observations", "enrichments", "features", "predictions", "evaluations", "goal-components"]:
            cursor = ""
            for _ in range(10000):
                batch = broker.request("live_export", {"kind": kind, "cursor": cursor})
                for record in batch["records"]:
                    write_once(DIRECTORY, kind, record)
                write_json(DIRECTORY/"source-coverage.json", batch["source_coverage"])
                next_cursor = batch.get("next_cursor")
                if not next_cursor:
                    break
                if next_cursor <= cursor:
                    raise ValueError("live_archive_cursor_not_advancing")
                cursor = next_cursor
            else:
                raise ValueError("live_archive_page_limit")
    if args.refresh:
        from scripts.api_football_schedule import collect
        result = collect(execute=True)
        print(json.dumps({"provider_refresh": result["status"], "remaining": result.get("remaining_conservative")}))
    if args.enrich:
        from scripts.collect_live_context import collect
        collect(execute=True, archive_finished=args.archive_finished)
    summary = build()
    imported = 0
    if args.import_local or args.import_results:
        batches = json.loads((ROOT/"data/processed/live-research/import-batches.json").read_text(encoding="utf-8"))
        for batch in batches:
            broker.request("live_import", {"records": batch})
            imported += len(batch)
    from ml.program_catalog import build as build_program, OUTPUT as PROGRAM_OUTPUT
    program = build_program(asof=summary["generated_at"])
    if args.import_local or args.import_results:
        for batch in json.loads((PROGRAM_OUTPUT/"import-batches.json").read_text(encoding="utf-8")):
            broker.request("program_import", {"records": batch})
    print(json.dumps({"display_catalog_fixtures": program["unique_fixtures"], "display_only_labels_added": 0}))
    print(json.dumps({"live_fixtures": summary["latest_fixtures"], "new_predictions": summary["new_predictions_before_kickoff"], "imported_local_records": imported, "production_model_promoted": False}))


if __name__ == "__main__":
    main()
