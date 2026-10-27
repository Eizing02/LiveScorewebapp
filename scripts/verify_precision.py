"""Re-run training unchanged and verify the full research artifact, not a toy fit."""
import json
import subprocess
import sys
from datetime import datetime, timezone

from ml.pipeline import ROOT, write_json


def snapshot():
    pointer = json.loads((ROOT/"reports/precision-v3/latest.json").read_text(encoding="utf-8"))
    report = json.loads((ROOT/pointer["report"]).read_text(encoding="utf-8"))
    return {"version": pointer["version"], "checksums": report["metadata"]["checksums"], "evaluations": report["evaluations"], "selection": report["selection"]}


def main():
    before = snapshot()
    result = subprocess.run([sys.executable, "-m", "ml.precision.experiment"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(result.stderr[-4000:])
    after = snapshot()
    if before != after:
        raise ValueError("full_training_reproducibility_failed")
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "version": after["version"], "same_version": True, "identical_model_checksums": True, "identical_evaluation_metrics": True, "identical_selection": True, "artifact_files": len(after["checksums"]), "runtime_scope": "same pinned environment; different runtime receives a separate run ID"}
    write_json(ROOT/"reports/precision-v3/reproducibility.json", report)
    print(json.dumps(report))


if __name__ == "__main__":
    main()
