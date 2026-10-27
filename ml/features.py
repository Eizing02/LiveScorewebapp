"""Rebuild features offline with the exact replay/snapshot functions used in backtests."""
from ml.models import LeagueState, replay


def build_features(asof_date, fixture, matches):
    if asof_date > fixture["date"]:
        raise ValueError("feature_cutoff_after_match_date")
    prior = [m for m in matches if m["league"] == fixture["league"] and m["date"] < asof_date]
    _, states = replay(prior)
    state = states.get(fixture["league"], LeagueState())
    state.start_season(fixture["season"])
    return state.snapshot(fixture)
