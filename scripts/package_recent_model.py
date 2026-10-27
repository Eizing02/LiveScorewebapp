"""Build a durable local versioned model bundle; no upload/promotion."""
import hashlib
import json
import zipfile

from ml.expanded import OUTPUT
from ml.pipeline import ROOT, write_json


def main():
    registry = json.loads((ROOT / "ml/models/recent-v2-registry.json").read_text(encoding="utf-8"))
    version = registry["candidate"]
    directory = ROOT / "ml/models" / version
    meta = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    for name, expected in meta["checksums"].items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
            raise ValueError("model_checksum_mismatch")
    destination = ROOT / "reports/recent-v2" / (version + ".zip")
    files = [(p, "model/" + p.name) for p in directory.iterdir() if p.is_file()]
    files.extend([(OUTPUT / "source-manifest.json", "data/source-manifest.json"), (ROOT / "data/ATTRIBUTION.md", "data/ATTRIBUTION.md"), (ROOT / "requirements.lock", "requirements.lock")])
    for name in ["market-baseline-diagnostics.json", "reproducibility.json"]:
        path = ROOT / "reports/recent-v2" / name
        if path.exists():
            files.append((path, "diagnostics/" + name))
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, name in sorted(files, key=lambda item: item[1]):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 25, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    checksum = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(".zip.sha256").write_text(checksum + "  " + destination.name + "\n", encoding="utf-8")
    write_json(ROOT / "reports/recent-v2/package.json", {"version": version, "archive": str(destination.relative_to(ROOT)), "sha256": checksum, "source_manifest_sha256": meta["source_manifest_sha256"], "status": "local_research_candidate", "permanent_storage_plan": "Keep versioned source/checksummed ZIP; publish reviewed ZIP to an immutable GitHub Release only after explicit authorization. Actions artifacts are review copies only.", "auto_promote": False})
    print(json.dumps({"version": version, "bytes": destination.stat().st_size, "sha256": checksum}))


if __name__ == "__main__":
    main()
