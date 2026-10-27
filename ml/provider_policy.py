import json
import re

from ml.pipeline import ROOT

POLICY = json.loads((ROOT/"ml/config/provider_access_policy.json").read_text(encoding="utf-8"))


def validate_query(route, query):
    rule = POLICY["queries"].get(route)
    query = query or {}
    if rule is None or not set(rule["required"]).issubset(query) or not set(query).issubset(rule["allowed"]):
        raise ValueError("known_unsupported_provider_query_no_request")
    for name in ["id", "fixture"]:
        if name in query and (not str(query[name]).isdigit() or int(query[name]) <= 0):
            raise ValueError("invalid_provider_identity_parameter")
    if "h2h" in query and not re.fullmatch(r"[1-9]\d*-[1-9]\d*", str(query["h2h"])):
        raise ValueError("invalid_provider_pair")
    if "date" in query:
        from datetime import date
        if date.fromisoformat(str(query["date"])).isoformat() != query["date"]:
            raise ValueError("invalid_provider_date")
    if "timezone" in query and query["timezone"] not in {"Asia/Bangkok", "UTC"}:
        raise ValueError("unsupported_timezone")
