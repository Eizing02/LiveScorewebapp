"""Point-in-time contract for future licensed API stats/lineups/injuries. No network."""
from datetime import datetime


def moment(value):
    if not value:
        raise ValueError("missing_availability_timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("unverified_timezone")
    return parsed


def eligible_snapshot(snapshot, target_fixture_id, prediction_at, kickoff_at):
    prediction, kickoff = moment(prediction_at), moment(kickoff_at)
    if prediction >= kickoff:
        return False, ["prediction_not_before_kickoff"]
    reasons = []
    if not snapshot.get("license_permits_use"):
        reasons.append("data_rights_not_verified")
    if not snapshot.get("coverage_verified"):
        reasons.append("coverage_not_verified")
    first_seen = moment(snapshot.get("first_seen_at"))
    published = moment(snapshot.get("available_at"))
    if first_seen > prediction or published > prediction:
        reasons.append("future_or_retrospectively_retrieved_information")
    if snapshot.get("kind") in {"xg", "shots", "match_statistics", "player_match_statistics"}:
        if snapshot.get("fixture_id") == target_fixture_id:
            reasons.append("target_match_post_kickoff_statistics")
        end = moment(snapshot.get("match_ended_at"))
        if end >= prediction:
            reasons.append("previous_match_not_finished_at_cutoff")
    # Missing fields deliberately remain None/unknown; never treat unknown injuries as no injuries.
    return not reasons, reasons


def injury_summary(payload, coverage_verified=False):
    if payload is None or not coverage_verified:
        return {"known": False, "count": None, "missing": True}
    if not isinstance(payload, list):
        raise ValueError("invalid_injury_payload")
    return {"known": True, "count": len(payload), "missing": False}
