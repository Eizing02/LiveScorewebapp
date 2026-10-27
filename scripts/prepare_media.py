"""Cache authentic branding from already collected target-league fixtures.

No account API calls, keys, arbitrary proxy URLs or inference from team names.
"""
import argparse
import hashlib
import json
import re
import time
import urllib.request
from pathlib import Path

from ml.live.ledger import SOURCE
from ml.pipeline import ROOT

LEAGUES = {39, 140, 78, 135, 40}
PUBLIC = ROOT / "apps/web/public/media"


def candidates():
    values = set()
    for call in json.loads((SOURCE / "request-ledger.json").read_text(encoding="utf-8")):
        if call["route"].split("?")[0] != "/fixtures" or not call.get("response_sha256"):
            continue
        path = SOURCE / "responses" / (call["response_sha256"] + ".json")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != call["response_sha256"]:
            raise ValueError("source_hash_mismatch")
        for row in json.loads(raw).get("response", []):
            if row["league"]["id"] not in LEAGUES:
                continue
            values.add(("leagues", row["league"]["id"]))
            values.update(("teams", row["teams"][side]["id"]) for side in ("home", "away"))
    if len(values) > 150:
        raise ValueError("media_download_limit")
    return sorted(values)


def fetch(url):
    agent = "FootballPredictionAI-local-media/1.0"
    if url.startswith("https://fonts.googleapis.com/"):
        agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    request = urllib.request.Request(url, headers={"User-Agent": agent})
    with urllib.request.urlopen(request, timeout=25) as response:
        if response.geturl() != url:
            raise ValueError("asset_redirect_refused")
        raw = response.read(512_001)
        if len(raw) > 512_000:
            raise ValueError("asset_too_large")
        return raw


def prepare(execute=False):
    assets = candidates()
    if not execute:
        return {"mode": "dry_run", "branding_assets": len(assets), "account_api_requests": 0}
    manifest = []
    for kind, identity in assets:
        if not isinstance(identity, int) or identity <= 0:
            raise ValueError("invalid_brand_identity")
        path = PUBLIC / kind / f"{identity}.png"
        url = f"https://media.api-sports.io/football/{kind}/{identity}.png"
        raw = path.read_bytes() if path.exists() else fetch(url)
        if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("expected_png")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        manifest.append({"path": str(path.relative_to(ROOT)), "source": url, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
        time.sleep(.2)
    fonts = ROOT / "apps/web/public/fonts"
    fonts.mkdir(parents=True, exist_ok=True)
    css = fetch("https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;500;600&display=swap").decode()
    for url in sorted(set(re.findall(r"url\((https://fonts.gstatic.com/[^)]+)\)", css))):
        extension = url.rsplit(".", 1)[-1]
        if extension not in {"woff2", "woff", "ttf"}:
            raise ValueError("unexpected_font_format")
        name = hashlib.sha256(url.encode()).hexdigest()[:16] + "." + extension
        path = fonts / name
        raw = path.read_bytes() if path.exists() else fetch(url)
        path.write_bytes(raw)
        css = css.replace(url, "/fonts/" + name)
        manifest.append({"path": str(path.relative_to(ROOT)), "source": url, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
    (fonts / "ibm-plex-sans-thai.css").write_text(css, encoding="utf-8")
    (fonts / "OFL.txt").write_bytes(fetch("https://raw.githubusercontent.com/google/fonts/main/ofl/ibmplexsansthai/OFL.txt"))
    referenced = {Path(row["path"]).name for row in manifest if "fonts" in Path(row["path"]).parts}
    for path in fonts.iterdir():
        if path.suffix in {".ttf", ".woff", ".woff2"} and path.name not in referenced:
            if path.resolve().parent != fonts.resolve():
                raise ValueError("font_cleanup_outside_workspace")
            path.unlink()
    (PUBLIC / "sources.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    names = [f"{kind}/{identity}" for kind, identity in assets]
    (ROOT / "apps/web/src/media-index.json").write_text(json.dumps(names), encoding="utf-8")
    return {"branding_assets": len(assets), "total_asset_bytes": sum(r["bytes"] for r in manifest), "account_api_requests": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    print(json.dumps(prepare(parser.parse_args().execute)))
