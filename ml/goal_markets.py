"""Half-goal markets from the same independent Poisson goal model."""
import math


def goal_markets(home_rate, away_rate):
    if not all(math.isfinite(v) and 0 < v <= 5 for v in [home_rate, away_rate]):
        raise ValueError("invalid_goal_rate")
    total = home_rate + away_rate
    output = {}
    for line in [1.5, 2.5, 3.5]:
        under = sum(math.exp(-total) * total ** k / math.factorial(k) for k in range(int(line) + 1))
        output[f"over_{line}"] = max(0.0, min(1.0, 1 - under))
        output[f"under_{line}"] = 1 - output[f"over_{line}"]
    output["btts_yes"] = (1 - math.exp(-home_rate)) * (1 - math.exp(-away_rate))
    output["btts_no"] = 1 - output["btts_yes"]
    return output
