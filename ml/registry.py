"""Local registry verification and explicitly approved promotion/rollback. Never network."""
import argparse
import hashlib
import json
import re
from pathlib import Path

from ml.pipeline import ROOT, write_json


def verify(version, root=ROOT / "ml/models"):
    if not re.fullmatch(r"v\d+-[a-f0-9]{12}", version):
        raise ValueError("invalid_version")
    directory = Path(root) / version
    meta = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    if meta["version"] != version:
        raise ValueError("version_mismatch")
    for name, checksum in meta["checksums"].items():
        if Path(name).name != name or hashlib.sha256((directory / name).read_bytes()).hexdigest() != checksum:
            raise ValueError("artifact_checksum_mismatch")
    return meta


def change(action, version=None, approved=False, root=ROOT / "ml/models"):
    if not approved:
        raise PermissionError("manual_approval_required")
    root = Path(root)
    registry = json.loads((root / "registry.json").read_text(encoding="utf-8"))
    target = version if action == "promote" else registry["previous"]
    if not target or target not in registry["candidates"]:
        raise ValueError("unknown_candidate_or_no_rollback")
    verify(target, root)
    registry["previous"], registry["active"] = registry["active"], target
    write_json(root / "registry.json", registry)
    return registry


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["verify", "promote", "rollback"])
    parser.add_argument("--version")
    parser.add_argument("--approve", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.version) if args.action == "verify" else change(args.action, args.version, args.approve), indent=2))
