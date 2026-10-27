"""Repeat the full importer and training, compare data/artifact bytes on this runtime."""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from ml.expanded import OUTPUT, run
from ml.pipeline import ROOT, write_json


def current():
    registry = json.loads((ROOT / "ml/models/recent-v2-registry.json").read_text(encoding="utf-8"))
    meta = json.loads((ROOT / "ml/models" / registry["candidate"] / "metadata.json").read_text(encoding="utf-8"))
    return registry["candidate"], meta["checksums"]


def main():
    quality = json.loads((OUTPUT / "quality-report.json").read_text(encoding="utf-8"))
    before = current()
    with tempfile.TemporaryDirectory(prefix="repro-", dir=ROOT / "data/processed") as directory:
        if not Path(directory).resolve().is_relative_to(ROOT.resolve()):
            raise ValueError("unexpected_temporary_workspace")
        with contextlib.redirect_stdout(io.StringIO()):
            repeated = run(Path(directory))
        if repeated["dataset_version"] != quality["dataset_version"]:
            raise ValueError("dataset_not_reproducible")
    result = subprocess.run([sys.executable, "-m", "ml.recent_evaluate"], cwd=ROOT, capture_output=True, text=True, check=True)
    after = current()
    if before != after:
        raise ValueError("model_artifact_not_reproducible")
    report = {"dataset_identical": True, "candidate_version_identical": True, "model_file_checksums_identical": True, "version": after[0], "files_verified": list(after[1]), "scope": "Full importer and repeated model training on this same recorded runtime; no claim of byte equality across operating systems/BLAS builds", "subprocess_completed": result.returncode == 0}
    write_json(ROOT / "reports/recent-v2/reproducibility.json", report)
    print(json.dumps(report))


if __name__ == "__main__":
    main()
