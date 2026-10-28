import copy
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
