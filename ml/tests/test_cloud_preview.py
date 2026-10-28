import copy
import hashlib
import json

import pytest

from ml.pipeline import ROOT
from scripts.cloud_preview import prepare_bootstrap, prepare_local, validate_config, workers_plan


def test_preview_configuration_cannot_publish_unprotected_assets_or_enable_jobs():
    config = json.loads((ROOT / "wrangler.preview.example.jsonc").read_text())
    assert validate_config(config) == config
    for field, value in [("PREVIEW_AUTH_ENABLED", "false"), ("PREVIEW_READ_ONLY", "false"), ("LIVE_API_ENABLED", "true"), ("SCHEDULER_ENABLED", "true"), ("MODEL_AUTO_PROMOTE", "true")]:
        bad = copy.deepcopy(config)
        bad["vars"][field] = value
        with pytest.raises(ValueError):
            validate_config(bad)
    bad = copy.deepcopy(config)
    bad["assets"]["run_worker_first"] = ["/api/*"]
    with pytest.raises(ValueError):
        validate_config(bad)


def test_local_preparation_keeps_credentials_separate_and_is_repeatable(tmp_path):
    config = json.loads((ROOT / "wrangler.preview.example.jsonc").read_text())
    folder = tmp_path / ".cloudflare"
    first = prepare_local(config, "a"*32, "unit-preview", folder)
    password = json.loads((folder / "preview.secrets.json").read_text())["PREVIEW_PASSWORD"]
    assert len(password) >= 32 and password not in (tmp_path / first["config"]).read_text()
    assert prepare_local(config, "a"*32, "unit-preview", folder) == first
    assert json.loads((folder / "preview.secrets.json").read_text())["PREVIEW_PASSWORD"] == password
    assert first["database_id_placeholder"]
    with pytest.raises(ValueError):
        prepare_local(config, "a"*32, "untrusted.example/path", folder)
    assert workers_plan([]) == "free_default_or_zero_price_workers"
    assert workers_plan([{"rate_plan": {"name": "Workers Paid"}, "price": 5, "state": "Paid"}]) == "paid_workers_subscription"
    assert workers_plan([{"rate_plan": {"name": "Workers"}}]) == "unverified"


def test_bootstrap_handles_migration_defaults_and_rejects_unapproved_or_oversized_sql():
    sql, report = prepare_bootstrap("INSERT INTO settings VALUES('MODEL_AUTO_PROMOTE','false');\n")
    assert "INSERT OR REPLACE" in sql and report["idempotent"]
    with pytest.raises(ValueError, match="unapproved"):
        prepare_bootstrap("INSERT INTO nonces VALUES('x',123);\n")
    with pytest.raises(ValueError, match="statement_limit"):
        prepare_bootstrap("INSERT INTO settings VALUES('large','"+"a"*100000+"');\n")
    with pytest.raises(ValueError, match="unexpected"):
        prepare_bootstrap("DELETE FROM settings;\n")


def report_sql(*, indexes=(0, 1), corrupt=False, parts=2):
    payload = json.dumps({"n": 19, "label": "ผลวิจัยฟุตบอล"}, ensure_ascii=False)
    key = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    cut = len(payload)//2
    chunks = [payload[:cut], payload[cut:]]
    if corrupt:
        chunks[0] += " "
    def quote(text):
        return "'"+text.replace("'", "''")+"'"
    sql = "".join("INSERT INTO research_report_chunks VALUES("+quote(key)+","+str(index)+","+quote(chunks[i])+");\n" for i, index in enumerate(indexes))
    manifest = json.dumps({"chunked": True, "key": key, "parts": parts, "checksum": key})
    return sql+"INSERT INTO performance VALUES('recent-backtest',"+quote(manifest)+");\n"


def test_bootstrap_preserves_complete_unicode_report_chunks_and_verifies_pointer():
    sql, report = prepare_bootstrap(report_sql())
    assert "INSERT OR IGNORE INTO research_report_chunks" in sql
    assert report["chunked_reports_verified"] == 1
    assert report["idempotent"]


@pytest.mark.parametrize("indexes,corrupt,parts,error", [
    ((0,), False, 2, "chunks_incomplete"),
    ((1, 2), False, 2, "chunks_incomplete"),
    ((0, 1), True, 2, "checksum_mismatch"),
    ((0, 1), False, 0, "manifest_invalid"),
    ((0, 1), False, True, "manifest_invalid"),
])
def test_bootstrap_rejects_broken_report_dependencies(indexes, corrupt, parts, error):
    with pytest.raises(ValueError, match=error):
        prepare_bootstrap(report_sql(indexes=indexes, corrupt=corrupt, parts=parts))
