"""Create a local, checksummed integration bundle; never publish or include secrets."""
import hashlib
import json
import zipfile

from ml.pipeline import ROOT, write_json


def main():
    version = json.loads((ROOT/"ml/models/precision-v3-registry.json").read_text(encoding="utf-8"))["candidate"]
    paths = set()
    for directory, suffixes in [("apps", {".ts", ".tsx", ".css", ".html", ".png"}), ("packages", {".ts"}), ("ml", {".py"}), ("ml/config", {".json"}), ("scripts", {".py", ".mjs"}), ("tests", {".ts"}), ("db/migrations", {".sql"}), ("docs", {".md"}), (".github/workflows", {".yml", ".yaml"})]:
        paths.update(p for p in (ROOT/directory).rglob("*") if p.is_file() and p.suffix in suffixes and "__pycache__" not in p.parts)
    paths.update((ROOT/"ml/models"/version).glob("*.json"))
    paths.add(ROOT/"ml/models/precision-v3-registry.json")
    paths.add(ROOT/"data/snapshots/openligadb-20261025.zip")
    for name in ["README.md", "AGENTS.md", ".gitignore", ".gitattributes", ".env.example", "package.json", "package-lock.json", "requirements.lock", "tsconfig.json", "vite.config.ts", "vitest.config.ts", "playwright.config.ts", "eslint.config.js", "wrangler.jsonc", "data/ATTRIBUTION.md"]:
        paths.add(ROOT/name)
    for name in ["implementation.json", "latest-dataset.json", "prospective-evaluation.json", "challenger-training.json", "context-collection.json", "optional-batch-proof.json", "verification.json", "data-by-league-season.csv", "live-detail-desktop.png", "live-detail-mobile.png"]:
        paths.add(ROOT/"reports/live-research"/name)
    for name in ["PRECISION_REPORT_TH.md", "package.json", "reproducibility.json"]:
        paths.add(ROOT/"reports/precision-v3"/name)
    files = {}
    for path in sorted(paths):
        if not path.exists():
            raise ValueError("required_bundle_file_missing: "+path.relative_to(ROOT).as_posix())
        name = path.relative_to(ROOT).as_posix()
        if name.startswith("data/processed/") or path.name == ".dev.vars" or name.startswith("db/seed"):
            raise ValueError("private_bundle_path")
        files[name] = path.read_bytes()
    # Check against the actual local credentials in memory, without printing them.
    from ml.provider_broker import local_settings
    settings = local_settings()
    for key in ["API_FOOTBALL_KEY", "INTERNAL_SYNC_SECRET", "ML_IMPORT_SECRET"]:
        value = settings.get(key, "")
        if len(value) >= 20 and any(value.encode() in data for data in files.values()):
            raise ValueError("credential_found_bundle_refused")
    manifest = {name: hashlib.sha256(content).hexdigest() for name, content in sorted(files.items())}
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    release = "live-integration-"+hashlib.sha256(payload).hexdigest()[:16]
    destination = ROOT/"reports/live-research"/(release+".zip")
    files["BUNDLE-CHECKSUMS.json"] = payload
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 26, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content)
    with zipfile.ZipFile(destination) as archive:
        for name, digest in manifest.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise ValueError("bundle_verification_failed")
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(".zip.sha256").write_text(digest+"  "+destination.name+"\n", encoding="utf-8")
    result = {"version": release, "archive": destination.relative_to(ROOT).as_posix(), "sha256": digest, "files": len(files), "bytes": destination.stat().st_size, "weights_reference": version, "raw_provider_data_included": False, "secrets_included": False, "published": False, "active_model": None, "auto_promote": False}
    write_json(ROOT/"reports/live-research/package.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
