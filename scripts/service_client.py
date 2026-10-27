"""Signed service requests. Dry-run by default; no secret values printed."""
import argparse
import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("route", choices=["/internal/features/export", "/internal/predictions/import", "/internal/sync/dry-run", "/internal/sync/execute"])
    parser.add_argument("--base", default="http://127.0.0.1:8787")
    parser.add_argument("--body-file", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports/service-response.json"))
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    base = urllib.parse.urlparse(args.base)
    if base.scheme != "https" and base.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("HTTPS required for non-local requests")
    method = "GET" if args.route.endswith("export") else "POST"
    if not args.execute:
        print(json.dumps({"dry_run": True, "method": method, "route": args.route, "requests": 1, "network_requests_used": 0}))
        return
    secret = os.environ.get("ML_IMPORT_SECRET" if args.route.endswith("/import") else "INTERNAL_SYNC_SECRET", "")
    if len(secret) < 32:
        raise ValueError("Required service secret is not configured")
    body = args.body_file.read_text(encoding="utf-8") if args.body_file else ""
    timestamp, nonce = str(int(time.time() * 1000)), str(uuid.uuid4())
    message = "\n".join([method, args.route, timestamp, nonce, body])
    signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    request = urllib.request.Request(args.base.rstrip("/") + args.route, data=body.encode() if method == "POST" else None, headers={"content-type": "application/json", "x-timestamp": timestamp, "x-nonce": nonce, "x-signature": signature}, method=method)
    with urllib.request.urlopen(request, timeout=15) as response:
        result = json.load(response)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result), encoding="utf-8")
    print("One signed request completed; response saved without logging credentials.")


if __name__ == "__main__":
    main()
