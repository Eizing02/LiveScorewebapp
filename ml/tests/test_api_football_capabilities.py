import pytest

from scripts.api_football_capabilities import CapabilityProbe, nonnegative_number, summarize
from scripts.api_football_probe import Probe, ProbeError


def test_enrichment_allowlist_does_not_expand_default_provider_routes():
    assert "/fixtures/statistics" in CapabilityProbe.allowed_routes
    assert "/fixtures/statistics" not in Probe.allowed_routes
    assert "/status" not in CapabilityProbe.allowed_routes


def test_xg_requires_finite_numeric_value_and_zero_is_valid():
    def payload(value):
        return {"response": [{"team": {"id": 1}, "statistics": [{"type": "expected_goals", "value": value}]}]}
    for value in [None, "N/A", "nan", "inf", -1, True]:
        assert not summarize("/fixtures/statistics", payload(value))["xg_value_verified"]
    assert summarize("/fixtures/statistics", payload("0.0"))["xg_value_verified"]
    assert nonnegative_number("2.37") == pytest.approx(2.37)


def test_empty_lineups_are_inconclusive_and_not_eleven_zero_strength_players():
    result = summarize("/fixtures/lineups", {"response": []})
    assert result["account_access"] == "empty_sample_inconclusive"
    assert result["teams"] == []
    with pytest.raises(ProbeError, match="shape"):
        summarize("/fixtures/lineups", {"response": None})


def test_provider_probability_percentages_need_all_three_valid_classes():
    value = {"response": [{"predictions": {"percent": {"home": "45%", "draw": "45%", "away": "10%"}}, "h2h": []}]}
    assert summarize("/predictions", value)["probabilities_valid"]
    value["response"][0]["predictions"]["percent"]["away"] = "40%"
    assert not summarize("/predictions", value)["probabilities_valid"]
    assert summarize("/predictions", value)["provider_forecast_not_our_model"]
