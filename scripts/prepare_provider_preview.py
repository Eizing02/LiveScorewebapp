"""Prepare a local read-only schedule cache from the recorded successful probe."""
import hashlib
import json

from ml.pipeline import ROOT, canonical_json, write_json


def main():
    source = json.loads((ROOT/"reports/api-football/date-smoke-test.json").read_text(encoding="utf-8"))
    if source["status"] != "date_endpoint_connected_not_live_activated" or len(source["days"]) != 2:
        raise ValueError("complete_two_date_probe_required")
    groups, identities = {}, set()
    for day in source["days"]:
        for group in day["leagues"]:
            target = groups.setdefault(group["league_id"], {"id": group["league_id"], "name": group["name"], "fixtures": []})
            for fixture in group["fixtures"]:
                identity = fixture["provider_fixture_id"]
                if identity in identities:
                    raise ValueError("duplicate_provider_fixture_preview")
                identities.add(identity)
                target["fixtures"].append(fixture)
    value = {"mode": "provider_recorded_preview", "source": "API-Football v3 / API-Sports", "captured_at": source["checked_at"], "business_date": source["business_date"], "timezone": "Asia/Bangkok", "day_start_hour": 6, "total": len(identities), "leagues": list(groups.values()), "automatic_refresh": False, "predictions_approved": False, "note": "Recorded real API response, not a live score stream. No key/account payload. Team mapping and current feature updates must pass before model analysis."}
    payload = canonical_json(value)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    parts = [payload[i:i+8000] for i in range(0, len(payload), 8000)]
    def quote(value):
        return "'"+str(value).replace("'", "''")+"'"
    statements = ["INSERT OR IGNORE INTO research_report_chunks VALUES("+",".join(map(quote, [digest, i, part]))+");" for i, part in enumerate(parts)]
    manifest = canonical_json({"chunked": True, "key": digest, "parts": len(parts), "checksum": digest})
    statements.append("INSERT OR REPLACE INTO performance VALUES('api-football-preview',"+quote(manifest)+");")
    (ROOT/"db/seed-provider-preview.sql").write_text("\n".join(statements)+"\n", encoding="utf-8")
    write_json(ROOT/"data/processed/api-football/provider-preview.json", value)
    print(json.dumps({"local_preview_fixtures": len(identities), "leagues": len(groups), "provider_requests": 0, "model_promoted": False}))


if __name__ == "__main__":
    main()
