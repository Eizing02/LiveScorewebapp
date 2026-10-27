import json
import shutil

import numpy as np
import pytest

from ml.batch import predict_export
from ml.evaluate import LogisticModel
from ml.pipeline import ROOT, write_json
from ml.registry import change, verify


def latest():
    return json.loads((ROOT / "ml/models/registry.json").read_text())["latest_candidate"]


def test_registry_checksums_manual_gate_and_rollback(tmp_path):
    source = ROOT / "ml/models"
    version = latest()
    shutil.copytree(source / version, tmp_path / version)
    write_json(tmp_path / "registry.json", {"active": None, "previous": None, "candidates": [version]})
    verify(version, tmp_path)
    with pytest.raises(PermissionError):
        change("promote", version, root=tmp_path)
    result = change("promote", version, approved=True, root=tmp_path)
    assert result["active"] == version
    second_version = "v1-000000000001"
    shutil.copytree(tmp_path / version, tmp_path / second_version)
    metadata = json.loads((tmp_path / second_version / "metadata.json").read_text())
    metadata["version"] = second_version
    write_json(tmp_path / second_version / "metadata.json", metadata)
    write_json(tmp_path / "registry.json", {"active": version, "previous": None, "candidates": [version, second_version]})
    result = change("promote", second_version, approved=True, root=tmp_path)
    assert result["previous"] == version and result["active"] == second_version
    result = change("rollback", approved=True, root=tmp_path)
    assert result["active"] == version and result["previous"] == second_version
    (tmp_path / version / "logistic.json").write_text("{}")
    with pytest.raises(ValueError, match="checksum"):
        verify(version, tmp_path)


def test_json_logistic_reload_and_batch_offline(tmp_path):
    version = latest()
    data = json.loads((ROOT / "ml/models" / version / "logistic.json").read_text())
    model = LogisticModel.from_dict(data)
    restored = LogisticModel.from_dict(model.to_dict())
    assert np.array_equal(model.predict_proba(np.ones((3, 11))), restored.predict_proba(np.ones((3, 11))))
    predictions = predict_export(ROOT / "data/mock-feature-export.json", tmp_path / "predictions.json", version)
    assert len(predictions) == 3
    assert all(sum(r["probabilities"]) == pytest.approx(1) for r in predictions)
    assert json.loads((ROOT / "ml/models/registry.json").read_text())["active"] is None
