"""Bounded, local-only API-Sports account/coverage/fixture preflight.

Never enables the Worker, writes D1, promotes a model, or saves account PII.
"""
import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from ml.pipeline import ROOT, write_json

BASE = "https://v3.football.api-sports.io"
PRIVATE = ROOT/"data/processed/api-football"
REPORT = ROOT/"reports/api-football/preflight.json"
LEAGUES = {39: "Premier League", 140: "La Liga", 78: "Bundesliga", 135: "Serie A", 40: "Championship"}
HEADER_NAMES = {"x-ratelimit-requests-limit", "x-ratelimit-requests-remaining", "x-ratelimit-limit", "x-ratelimit-remaining", "retry-after"}


class ProbeError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProbeError("provider_redirect_refused")


def load_key(path=None):
    value = os.environ.get("API_FOOTBALL_KEY", "").strip()
    path = path or ROOT/".dev.vars"
    if not value and path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            name, separator, raw = line.partition("=")
            if separator and name.strip() == "API_FOOTBALL_KEY":
                value = raw.strip().strip('"\'')
    if not value or any(c.isspace() for c in value) or value in {"YOUR_API_KEY", "REPLACE_LOCALLY"}:
        raise ProbeError("missing_api_key_save_it_in_ignored_dev_vars")
    return value


def rate_headers(headers):
    result = {}
    for name, raw in headers.items():
        if name.lower() in HEADER_NAMES and str(raw).isdigit():
            result[name.lower()] = int(raw)
    return result


def account_summary(payload):
    response = payload.get("response", {})
    subscription, requests = response.get("subscription", {}), response.get("requests", {})
    current, limit = requests.get("current"), requests.get("limit_day")
    if not isinstance(current, int) or not isinstance(limit, int) or not 0 <= current <= limit:
        raise ProbeError("unverified_account_quota")
    return {"plan": str(subscription.get("plan", "unknown")), "active": subscription.get("active") is True, "requests_used": current, "daily_limit": limit, "daily_remaining": limit-current}


def league_summary(payload, league_id, season):
    rows = payload.get("response", [])
    if not isinstance(rows, list) or len(rows) != 1 or rows[0].get("league", {}).get("id") != league_id:
        raise ProbeError("unexpected_league_identity")
    seasons = rows[0].get("seasons", [])
    selected = next((s for s in seasons if s.get("year") == season), None)
    return {"id": league_id, "name": rows[0]["league"].get("name"), "catalog_seasons": [s["year"] for s in seasons if isinstance(s.get("year"), int)], "requested_season": season, "requested_season_listed": selected is not None, "coverage": selected.get("coverage", {}) if selected else {}, "account_fixture_access": "unverified", "note": "Catalog availability and coverage flags do not prove account permission or complete per-match data."}


def round_bounds(day):
    start = datetime.fromisoformat(day+"T06:00:00").replace(tzinfo=ZoneInfo("Asia/Bangkok"))
    return start.astimezone(timezone.utc), (start+timedelta(days=1)).astimezone(timezone.utc)


def fixture_summary(payload, league_id, season, day):
    start, end = round_bounds(day)
    if payload.get("paging", {}).get("total") != 1 or not isinstance(payload.get("response"), list):
        raise ProbeError("unexpected_fixture_paging_or_schema")
    fixtures, held, seen = [], [], set()
    for row in payload["response"]:
        try:
            fixture, league, teams, goals = [row[k] for k in ["fixture", "league", "teams", "goals"]]
            if league["id"] != league_id or league["season"] != season:
                raise ValueError("fixture_league_or_season_mismatch")
            kickoff = datetime.fromisoformat(fixture["date"].replace("Z", "+00:00"))
            if kickoff.tzinfo is None:
                raise ValueError("missing_kickoff_timezone")
            if fixture["id"] in seen:
                raise ValueError("duplicate_provider_fixture")
            seen.add(fixture["id"])
            if teams["home"]["id"] == teams["away"]["id"]:
                raise ValueError("same_home_away_team")
            if any(v is not None and (not isinstance(v, int) or isinstance(v, bool) or v < 0) for v in [goals["home"], goals["away"]]):
                raise ValueError("invalid_score")
            if not start <= kickoff < end:
                continue
            fixtures.append({"provider_fixture_id": fixture["id"], "kickoff_utc": kickoff.astimezone(timezone.utc).isoformat(), "league_id": league_id, "season": season, "home": teams["home"]["name"], "away": teams["away"]["name"], "home_provider_id": teams["home"]["id"], "away_provider_id": teams["away"]["id"], "status": fixture["status"]["short"], "goals": [goals["home"], goals["away"]], "historical_team_mapping": "unverified", "prediction": None})
        except (ValueError, TypeError, KeyError) as error:
            held.append({"provider_fixture_id": row.get("fixture", {}).get("id"), "reason": str(error)})
    return {"response_rows": len(payload["response"]), "round_start_utc": start.isoformat(), "round_end_exclusive_utc": end.isoformat(), "fixtures": fixtures, "quarantined": held, "empty_is_not_proof_of_season_permission": not payload["response"]}


class Probe:
    allowed_routes = frozenset({"/status", "/leagues", "/fixtures"})
    development_billable_limit = 20

    def __init__(self, key, directory=PRIVATE, opener=None, sleeper=time.sleep, clock=time.time):
        self.key, self.directory = key, Path(directory)
        self.opener = opener or urllib.request.build_opener(NoRedirect)
        self.sleeper, self.clock = sleeper, clock
        self.calls, self.rates, self.next_at = [], {}, 0.
        self.remaining = None
        self.path = self.directory/"request-ledger.json"
        self.ledger = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else []
        self.broker = None
        if Path(directory) == PRIVATE and opener is None:
            from ml.provider_broker import BrokerClient, local_settings
            settings = local_settings()
            if settings.get("PROVIDER_BROKER_ENABLED") == "true":
                self.broker = BrokerClient(settings)

    def get(self, route, query=None):
        if route not in self.allowed_routes:
            raise ProbeError("endpoint_not_in_preflight_allowlist")
        if len(self.calls) >= 7:
            raise ProbeError("session_request_budget_exhausted")
        if self.broker:
            from ml.provider_policy import validate_query
            try:
                validate_query(route, query)
            except ValueError as error:
                raise ProbeError(str(error)) from None
        billable = route != "/status"
        if billable and (self.remaining is None or self.remaining <= 10):
            raise ProbeError("quota_unverified_or_reserve_reached")
        recent = [r for r in self.ledger if r["attempted_at"] > self.clock()-86400]
        if billable and sum(r["budgeted_billable"] for r in recent) >= self.development_billable_limit:
            raise ProbeError("local_rolling24h_preflight_budget_exhausted")
        last = max((r["attempted_at"] for r in recent), default=0.)
        wait = max(self.next_at, last+13)-self.clock()
        while wait > 0:
            self.sleeper(min(wait, 1.))
            wait = max(self.next_at, last+13)-self.clock()
        key = route+("?"+urllib.parse.urlencode(query) if query else "")
        try:
            ticket = self.broker.reserve(route) if self.broker else None
        except ValueError as error:
            raise ProbeError(str(error)) from None
        entry = {"route": key, "attempted_at": self.clock(), "budgeted_billable": billable, "status": None}
        if ticket:
            entry["broker_ticket"] = ticket["id"]
        self.ledger.append(entry)
        write_json(self.path, self.ledger)
        self.calls.append(entry)
        if billable:
            self.remaining -= 1
        request = urllib.request.Request(BASE+key, headers={"x-apisports-key": self.key}, method="GET")
        try:
            with self.opener.open(request, timeout=15) as response:
                entry["status"] = response.status
                self.rates = rate_headers(response.headers)
                entry["rate_headers"] = self.rates
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ProbeError("provider_payload_too_large")
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ProbeError("invalid_provider_payload")
            if payload.get("errors"):
                errors = json.dumps(payload["errors"], ensure_ascii=True).replace(self.key, "[REDACTED]")[:1500]
                entry["provider_errors"] = errors
                raise ProbeError("provider_reported_error: "+errors)
            if route == "/status":
                account = account_summary(payload)
                self.rates.setdefault("x-ratelimit-requests-remaining", account["daily_remaining"])
            minute_limit = self.rates.get("x-ratelimit-limit", 5)
            self.next_at = self.clock()+max(13., 60/max(1, minute_limit)+1)
            if self.rates.get("x-ratelimit-remaining") == 0:
                self.next_at = self.clock()+61
            remaining = self.rates.get("x-ratelimit-requests-remaining")
            if remaining is not None:
                self.remaining = min(self.remaining, remaining) if self.remaining is not None else remaining
            # Account status contains name/email: never persist its raw bytes.
            if route != "/status":
                digest = hashlib.sha256(raw).hexdigest()
                path = self.directory/"responses"/(digest+".json")
                path.parent.mkdir(parents=True, exist_ok=True)
                if not path.exists():
                    path.write_bytes(raw)
                entry["response_sha256"] = digest
                entry["first_seen_at"] = datetime.now(timezone.utc).isoformat()
            return payload
        except urllib.error.HTTPError as error:
            entry["status"] = error.code
            raise ProbeError("provider_http_"+str(error.code)) from None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            raise ProbeError("provider_connection_timeout_or_invalid_json_no_retry") from None
        finally:
            write_json(self.path, self.ledger)
            if ticket:
                rate_error = "ratelimit" in entry.get("provider_errors", "").lower()
                self.broker.settle(ticket, entry.get("status"), entry.get("rate_headers", {}), rate_error)


class ManagedProbe(Probe):
    development_billable_limit = 85

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.broker:
            raise ProbeError("managed_collection_requires_shared_D1_broker")


def run(execute=False, day=None, season=None):
    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    day = day or (now-timedelta(hours=6)).date().isoformat()
    season = season or (now.year if now.month >= 7 else now.year-1)
    start, end = round_bounds(day)
    report = {"mode": "live_preflight" if execute else "dry_run", "created_at": now.isoformat(), "transport": "direct_api_sports", "season": season, "round_date": day, "round_start_utc": start.isoformat(), "round_end_exclusive_utc": end.isoformat(), "maximum_http_requests": 7, "maximum_budgeted_billable_requests": 6, "minimum_daily_reserve": 10, "automatic_retries": 0, "worker_live_enabled": False, "model_promoted": False, "production_deployed": False, "reset_timezone": "unverified_keep_worker_disabled", "calls": [], "leagues": [], "fixtures": None, "account": None, "status": "ready_for_key"}
    if not execute:
        write_json(REPORT.with_name("plan.json"), report)
        return report
    probe = None
    try:
        probe = Probe(load_key())
        report["account"] = account_summary(probe.get("/status"))
        account = report["account"]
        if not account["active"]:
            raise ProbeError("subscription_not_active")
        if account["plan"].lower() != "free":
            raise ProbeError("free_plan_required_for_initial_zero_cost_probe")
        probe.remaining = min(probe.remaining, account["daily_remaining"]) if probe.remaining is not None else account["daily_remaining"]
        if probe.remaining < 16:
            raise ProbeError("not_enough_remaining_for_six_calls_and_ten_reserve")
        for league_id in LEAGUES:
            league = league_summary(probe.get("/leagues", {"id": league_id}), league_id, season)
            report["leagues"].append(league)
            write_json(REPORT, report)
            print(json.dumps({"checked_league": league["name"], "requested_season_listed": league["requested_season_listed"]}), flush=True)
        if report["leagues"][0]["requested_season_listed"]:
            payload = probe.get("/fixtures", {"league": 39, "season": season, "from": day, "to": (datetime.fromisoformat(day)+timedelta(days=1)).date().isoformat(), "timezone": "Asia/Bangkok"})
            report["fixtures"] = fixture_summary(payload, 39, season, day)
            report["leagues"][0]["account_fixture_access"] = "verified_for_sample_response" if payload["response"] else "empty_response_inconclusive"
        report["status"] = "completed_preflight_not_live_activation"
    except (ProbeError, ValueError) as error:
        report["status"] = "blocked"
        report["reason"] = str(error).replace(probe.key, "[REDACTED]") if probe else str(error)
    finally:
        if probe:
            report["calls"] = probe.calls
            report["rate_headers"] = probe.rates
            report["remaining_conservative"] = probe.remaining
        report["actual_http_requests"] = len(report["calls"])
        report["budgeted_billable_requests"] = sum(c["budgeted_billable"] for c in report["calls"])
        write_json(REPORT, report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--date")
    parser.add_argument("--season", type=int)
    args = parser.parse_args()
    result = run(args.execute, args.date, args.season)
    print(json.dumps({k: result.get(k) for k in ["status", "reason", "actual_http_requests", "budgeted_billable_requests", "remaining_conservative"]}))
