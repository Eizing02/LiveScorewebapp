"""Small, cached public historical downloads. Never calls API-Football."""
import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from ml.pipeline import ROOT, write_json

DIRECTORY = ROOT / "data/source/additional"
FJELSTUL_SHA = "ff3c37698065476e1852243685da6b756a580b9f"


def fetch(url, relative, license_name, purpose):
    path = DIRECTORY / relative
    meta_path = path.with_suffix(path.suffix + ".meta.json")
    if path.exists() and meta_path.exists():
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        if hashlib.sha256(path.read_bytes()).hexdigest() != metadata["sha256"]:
            raise ValueError("cached_source_checksum_mismatch")
        return metadata
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "FootballPredictionAI-local-research/0.2"})
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = response.read(64_000_001)
    if len(payload) > 64_000_000:
        raise ValueError("source_payload_too_large")
    if relative.endswith(".json"):
        json.loads(payload)
    metadata = {"url": url, "path": relative, "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload), "retrieved_at": datetime.now(timezone.utc).isoformat(), "license": license_name, "purpose": purpose}
    path.write_bytes(payload)
    write_json(meta_path, metadata)
    return metadata


def main():
    manifest, failures = [], []
    for league in ["bl1", "bl2"]:
        for season in range(2021, 2027):
            url = f"https://api.openligadb.de/getmatchdata/{league}/{season}"
            try:
                manifest.append(fetch(url, f"openligadb/{league}-{season}.json", "ODbL-1.0", "historical results; attributed derived dataset"))
            except (OSError, ValueError) as error:
                failures.append({"url": url, "error_type": type(error).__name__})
            time.sleep(0.25)
    # Keep this differently licensed database separate: corroboration only, no label union.
    for name in ["matches", "teams", "seasons"]:
        url = f"https://raw.githubusercontent.com/jfjelstul/englishfootball/{FJELSTUL_SHA}/data-csv/{name}.csv"
        try:
            manifest.append(fetch(url, f"fjelstul/{name}.csv", "CC-BY-SA-4.0", "separate cross-check only; not merged into training labels"))
        except (OSError, ValueError) as error:
            failures.append({"url": url, "error_type": type(error).__name__})
    write_json(DIRECTORY / "manifest.json", {"files": manifest, "failures": failures, "api_football_requests": 0})
    print(json.dumps({"downloaded_or_cached": len(manifest), "failures": failures, "api_football_requests": 0}))


if __name__ == "__main__":
    main()
