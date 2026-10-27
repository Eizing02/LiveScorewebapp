"""Versioned local evidence/model bundle, with no upload or active-model change."""
import hashlib
import json
import zipfile

from ml.expanded import OUTPUT
from ml.pipeline import ROOT, write_json


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    pointer = json.loads((ROOT/"reports/precision-v3/latest.json").read_text(encoding="utf-8"))
    version = pointer["version"]
    directory = ROOT/"ml/models"/version
    metadata = json.loads((directory/"metadata.json").read_text(encoding="utf-8"))
    reproduced = json.loads((ROOT/"reports/precision-v3/reproducibility.json").read_text(encoding="utf-8"))
    if reproduced["version"] != version or not reproduced["identical_model_checksums"]:
        raise ValueError("matching_full_training_reproducibility_required")
    for name, expected in metadata["checksums"].items():
        if sha(directory/name) != expected:
            raise ValueError("model_checksum_mismatch")
    for name, expected in metadata["training_code_sha256"].items():
        if sha(ROOT/name) != expected:
            raise ValueError("training_code_changed_since_evaluation")
    files = [(p, "model/"+p.name) for p in directory.glob("*.json")]
    evidence = (ROOT/pointer["report"]).parent
    files += [(p, "evidence/"+p.name) for p in evidence.iterdir() if p.suffix in {".json", ".jsonl"}]
    files += [(p, "source/"+str(p.relative_to(ROOT)).replace("\\", "/")) for p in (ROOT/"ml").rglob("*.py") if "models" not in p.relative_to(ROOT/"ml").parts]
    files += [(p, "source/ml/config/"+p.name) for p in (ROOT/"ml/config").glob("*.json")]
    files += [(ROOT/"requirements.lock", "requirements.lock"), (OUTPUT/"source-manifest.json", "data/source-manifest.json"), (ROOT/"data/ATTRIBUTION.md", "data/ATTRIBUTION.md"), (ROOT/"reports/precision-v3/reproducibility.json", "evidence/reproducibility.json")]
    for name in ["README.md", "docs/PRECISION_V3_OPERATIONS_TH.md", "reports/precision-v3/PRECISION_REPORT_TH.md", "reports/precision-v3/verification.json"]:
        path = ROOT/name
        if path.exists():
            files.append((path, "documentation/"+path.name))
    destination = ROOT/"reports/precision-v3"/(version+".zip")
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, name in sorted(files, key=lambda item: item[1]):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 26, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    checksum = sha(destination)
    destination.with_suffix(".zip.sha256").write_text(checksum+"  "+destination.name+"\n", encoding="utf-8")
    result = {"version": version, "archive": str(destination.relative_to(ROOT)), "bytes": destination.stat().st_size, "sha256": checksum, "permanent_storage_plan": "Local versioned JSON/source/checksummed ZIP. After explicit publication authorization, keep the reviewed bundle in an immutable GitHub Release. Actions artifacts remain temporary review copies only.", "active_version": None, "auto_promote": False, "published": False}
    write_json(ROOT/"reports/precision-v3/package.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
