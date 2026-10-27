"""Freeze/restore public OpenLigaDB bytes so CI never silently changes a dataset."""
import argparse
import hashlib
import json
import re
import zipfile

from ml.pipeline import ROOT, write_json

CONFIG = ROOT / "ml/config/source_snapshot_v2.json"
ARCHIVE = ROOT / "data/snapshots/openligadb-20261025.zip"
SOURCE = ROOT / "data/source/additional"


def main(freeze=False):
    if freeze:
        if CONFIG.exists():
            raise ValueError("source_snapshot_already_frozen")
        ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted((SOURCE / "openligadb").glob("*.json")):
                info = zipfile.ZipInfo("openligadb/" + path.name, (2026, 10, 25, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, path.read_bytes())
        write_json(CONFIG, {"archive": ARCHIVE.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(), "source": "OpenLigaDB community", "license": "ODbL-1.0", "attribution": "https://www.openligadb.de/", "notice": "See data/ATTRIBUTION.md; this is a historical research snapshot, not a current API feed."})
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    archive_path = ROOT / config["archive"]
    if hashlib.sha256(archive_path.read_bytes()).hexdigest() != config["sha256"]:
        raise ValueError("source_archive_checksum_mismatch")
    count = 0
    with zipfile.ZipFile(archive_path) as archive:
        for entry in archive.infolist():
            if not re.fullmatch(r"openligadb/bl[12]-202[1-6]\.json(?:\.meta\.json)?", entry.filename):
                raise ValueError("unsafe_snapshot_member")
            target = SOURCE / entry.filename
            if not target.resolve().is_relative_to(SOURCE.resolve()) or entry.file_size > 10_000_000:
                raise ValueError("unsafe_snapshot_target")
            content = archive.read(entry)
            if target.exists() and target.read_bytes() != content:
                raise ValueError("local_source_differs_from_frozen_snapshot")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            count += 1
    print(json.dumps({"frozen_files": count, "archive_sha256": config["sha256"], "network_requests": 0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    main(parser.parse_args().freeze)
