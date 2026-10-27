"""HMAC client for the single D1 provider quota ledger; no API key is transmitted."""
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from ml.pipeline import ROOT


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("broker_redirect_refused")


def local_settings():
    values = {}
    path = ROOT/".dev.vars"
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            key, separator, value = line.partition("=")
            if separator and not key.strip().startswith("#"):
                values[key.strip()] = value.strip().strip('"\'')
    return {**values, **os.environ}


class BrokerClient:
    def __init__(self, settings=None):
        self.settings = settings or local_settings()
        self.base = self.settings.get("PROVIDER_BROKER_URL", "http://127.0.0.1:8787").rstrip("/")
        parsed = urllib.parse.urlsplit(self.base)
        if parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}):
            raise ValueError("broker_requires_https_or_loopback")
        if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
            raise ValueError("invalid_broker_origin")
        self.secret = self.settings.get("INTERNAL_SYNC_SECRET", "")
        if len(self.secret) < 32:
            raise ValueError("provider_broker_secret_missing")
        self.opener = urllib.request.build_opener(NoRedirect)

    def request(self, action, payload):
        if action not in {"reserve", "settle", "live_import", "live_export", "program_import"}:
            raise ValueError("invalid_broker_action")
        path = "/internal/live/import" if action == "live_import" else "/internal/live/export" if action == "live_export" else "/internal/provider-quota/"+action
        if action == "program_import":
            path = "/internal/program/import"
        body = json.dumps(payload, separators=(",", ":"))
        stamp, nonce = str(int(time.time()*1000)), str(uuid.uuid4())
        signature = hmac.new(self.secret.encode(), "\n".join(["POST", path, stamp, nonce, body]).encode(), hashlib.sha256).hexdigest()
        request = urllib.request.Request(self.base+path, data=body.encode(), headers={"content-type": "application/json", "x-timestamp": stamp, "x-nonce": nonce, "x-signature": signature}, method="POST")
        try:
            with self.opener.open(request, timeout=10) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            raise ValueError("provider_broker_unavailable_or_budget_denied_no_retry") from None

    def reserve(self, route):
        return self.request("reserve", {"route": route, "priority": "normal"})

    def settle(self, ticket, status, headers, rate_error=False):
        return self.request("settle", {"ticket": {"id": ticket["id"], "window": ticket["window"]}, "status": status or 0, "headers": headers, "rate_error": rate_error})
