"""Read-only Cloudflare inspection and local preview preparation. Never deploys."""
import argparse
import hashlib
import json
import os
import re
import secrets
import sqlite3
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from ml.pipeline import ROOT

NAME = "football-ai-preview"
TABLES = ["program_sources", "program_observations", "provider_team_mappings", "provider_fixture_observations", "provider_enrichment_observations", "provider_dataset_versions", "provider_goal_components", "live_match_details", "live_daily_reports", "research_report_chunks", "performance", "settings"]


def cli(*args):
    result = subprocess.run(["node", "scripts/wrangler.mjs", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=90, env={**os.environ, "WRANGLER_SEND_METRICS": "false", "CI": "true"})
    if result.returncode:
        raise ValueError("wrangler_command_failed_no_credentials_logged")
    return result.stdout


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("cloudflare_redirect_rejected")


def api_get(account, token, path):
    if path not in {"subscriptions", "workers/subdomain", "workers/scripts"} or not re.fullmatch(r"[a-f0-9]{32}", account):
        raise ValueError("unapproved_read_endpoint")
    request = urllib.request.Request("https://api.cloudflare.com/client/v4/accounts/"+account+"/"+path, headers={"Authorization": "Bearer "+token}, method="GET")
    with urllib.request.build_opener(NoRedirect).open(request, timeout=20) as response:
        value = json.load(response)
    if not value.get("success"):
        raise ValueError("cloudflare_read_failed")
    return value["result"]


def workers_plan(subscriptions):
    if not isinstance(subscriptions, list):
        return "unverified"
    active = [s for s in subscriptions if str(s.get("state", "")).lower() not in {"cancelled", "expired", "failed"} and "worker" in json.dumps(s).lower()]
    if any(float(s.get("price") or 0) > 0 for s in active):
        return "paid_workers_subscription"
    if any(s.get("price") is None and "free" not in json.dumps(s).lower() for s in active):
        return "unverified"
    return "free_default_or_zero_price_workers"


def validate_config(config):
    v = config["vars"]
    required = {"APP_ENV": "preview", "PREVIEW_AUTH_ENABLED": "true", "PREVIEW_READ_ONLY": "true", "ZERO_COST_MODE": "true", "LIVE_API_ENABLED": "false", "SCHEDULER_ENABLED": "false", "MODEL_AUTO_PROMOTE": "false", "PROVIDER_BROKER_ENABLED": "false", "INTEGRATION_APPROVED": "false"}
    if any(v.get(k) != expected for k, expected in required.items()) or config["assets"].get("run_worker_first") is not True or config.get("triggers"):
        raise ValueError("unsafe_preview_configuration")
    if config.get("name") != NAME or len(config.get("d1_databases", [])) != 1 or config["d1_databases"][0].get("database_name") != NAME:
        raise ValueError("preview_must_use_separate_resources")
    if any(k in v for k in ["PREVIEW_PASSWORD", "API_FOOTBALL_KEY", "INTERNAL_SYNC_SECRET", "ML_IMPORT_SECRET"]):
        raise ValueError("secret_in_plaintext_config")
    return config


def prepare_local(config, account, subdomain, directory):
    validate_config(config)
    if not re.fullmatch(r"[a-z0-9-]+", subdomain or ""):
        raise ValueError("workers_subdomain_unverified")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    secret_path = directory / "preview.secrets.json"
    if not secret_path.exists():
        secret_path.write_text(json.dumps({"PREVIEW_USERNAME": "owner", "PREVIEW_PASSWORD": secrets.token_urlsafe(32)})+"\n", encoding="utf-8")
    values = json.loads(secret_path.read_text(encoding="utf-8"))
    if len(values.get("PREVIEW_PASSWORD", "")) < 32:
        raise ValueError("preview_password_too_short")
    url = "https://"+NAME+"."+subdomain+".workers.dev"
    config = json.loads(json.dumps(config))
    config["account_id"] = account
    config["vars"]["ALLOWED_ORIGIN"] = url
    path = directory.parent / "wrangler.preview.local.jsonc"
    path.write_text(json.dumps(config, indent=2)+"\n", encoding="utf-8")
    return {"worker_url": url, "config": path.name, "secret_file": str(secret_path), "database_id_placeholder": config["d1_databases"][0]["database_id"] == "00000000-0000-0000-0000-000000000000"}


def verify_report_chunks(connection):
    """JSON report pointers have dependencies that foreign_key_check cannot see."""
    verified = 0
    for (raw,) in connection.execute("SELECT payload FROM performance"):
        manifest = json.loads(raw)
        if not isinstance(manifest, dict) or not manifest.get("chunked"):
            continue
        key, checksum, parts = manifest.get("key"), manifest.get("checksum"), manifest.get("parts")
        if manifest["chunked"] is not True or not isinstance(key, str) or not re.fullmatch(r"[a-f0-9]{64}", key) or not isinstance(checksum, str) or not re.fullmatch(r"[a-f0-9]{64}", checksum) or type(parts) is not int or parts < 1:
            raise ValueError("bootstrap_report_manifest_invalid")
        chunks = connection.execute("SELECT part,payload FROM research_report_chunks WHERE report_key=? ORDER BY part", (key,)).fetchall()
        if len(chunks) != parts or any(index != row[0] for index, row in enumerate(chunks)):
            raise ValueError("bootstrap_report_chunks_incomplete")
        payload = "".join(row[1] for row in chunks)
        if hashlib.sha256(payload.encode("utf-8")).hexdigest() != checksum:
            raise ValueError("bootstrap_report_checksum_mismatch")
        json.loads(payload)
        verified += 1
    return verified


def prepare_bootstrap(sql):
    statements, pending = [], ""
    for line in sql.splitlines(keepends=True):
        pending += line
        if not sqlite3.complete_statement(pending):
            continue
        statement = pending.strip()
        match = re.match(r'INSERT INTO ["`]?([a-z_]+)["`]?\b', statement)
        if match:
            table = match[1]
            if table not in TABLES:
                raise ValueError("unapproved_bootstrap_table")
            verb = "INSERT OR REPLACE INTO " if table in {"settings", "performance"} else "INSERT OR IGNORE INTO "
            statement = statement.replace("INSERT INTO ", verb, 1)
        elif not statement.startswith(("PRAGMA ", "BEGIN ", "BEGIN;", "COMMIT;")):
            raise ValueError("unexpected_bootstrap_statement")
        if len(statement.encode("utf-8")) > 100000:
            raise ValueError("bootstrap_exceeds_d1_statement_limit")
        statements.append(statement)
        pending = ""
    if pending.strip():
        raise ValueError("incomplete_bootstrap_sql")
    result = "\n".join(statements)+"\n"
    with sqlite3.connect(":memory:") as connection:
        for migration in sorted((ROOT / "db/migrations").glob("*.sql")):
            connection.executescript(migration.read_text(encoding="utf-8"))
        connection.executescript(result)
        connection.executescript(result)  # Import is repeatable; evidence stays immutable.
        if list(connection.execute("PRAGMA foreign_key_check")):
            raise ValueError("bootstrap_foreign_key_failure")
        reports = verify_report_chunks(connection)
        heads = connection.execute("SELECT COUNT(*) FROM program_heads").fetchone()[0]
    return result, {"statements": len(statements), "largest_statement_bytes": max(map(lambda s: len(s.encode("utf-8")), statements), default=0), "roundtrip_heads": heads, "chunked_reports_verified": reports, "idempotent": True, "foreign_key_violations": 0}


def run(prepare=False):
    who = json.loads(cli("whoami", "--json"))
    if not who.get("loggedIn") or len(who.get("accounts", [])) != 1:
        raise ValueError("login_and_select_one_cloudflare_account")
    account = who["accounts"][0]["id"]
    token = json.loads(cli("auth", "token", "--json"))["token"]
    try:
        plan = workers_plan(api_get(account, token, "subscriptions"))
    except (urllib.error.HTTPError, ValueError):
        plan = "unverified"
    scripts = api_get(account, token, "workers/scripts")
    subdomain = api_get(account, token, "workers/subdomain").get("subdomain")
    databases = json.loads(cli("d1", "list", "--json"))
    report = {"mode": "read_only_preflight", "authenticated": True, "workers_plan": plan, "worker_name": NAME, "database_name": NAME, "worker_name_in_use": any(s.get("id") == NAME for s in scripts), "database_name_in_use": any(d.get("name") == NAME for d in databases), "existing_workers_untouched": len(scripts), "remote_writes": 0, "provider_calls": 0, "deployed": False, "approval_required": True}
    if prepare:
        if report["worker_name_in_use"] or report["database_name_in_use"]:
            raise ValueError("proposed_preview_resources_already_exist_review_before_update")
        local = ROOT / ".cloudflare"
        config = json.loads((ROOT / "wrangler.preview.example.jsonc").read_text(encoding="utf-8"))
        details = prepare_local(config, account, subdomain, local)
        export = local / "preview.bootstrap.sql"
        cli("d1", "export", "football-ai", "--local", "--no-schema", "--table", *TABLES, "--output", str(export))
        sql, validation = prepare_bootstrap(export.read_text(encoding="utf-8"))
        export.write_text(sql, encoding="utf-8", newline="\n")
        raw = export.read_bytes()
        report["bootstrap"] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "tables": TABLES, **validation}
        (local / "preview-plan.json").write_text(json.dumps({**report, **details}, indent=2)+"\n", encoding="utf-8")
        report["local_config_prepared"] = True
        report["database_creation_still_required"] = details["database_id_placeholder"]
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true", help="Write ignored local config, credentials and a local D1 export; no cloud writes")
    args = parser.parse_args()
    print(json.dumps(run(args.prepare), ensure_ascii=False))
