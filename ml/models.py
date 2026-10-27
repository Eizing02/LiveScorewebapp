"""Point-in-time state shared by replay, training features and batch inference."""
import math
from collections import defaultdict, deque
from itertools import groupby

from ml.pipeline import POLICY

PARAMS = POLICY["parameters"]
FEATURES = ["elo_difference", "home_attack", "home_defence", "away_attack", "away_defence", "league_home_goals", "league_away_goals", "home_matches", "away_matches", "home_form", "away_form"]


def poisson_prediction(home_rate, away_rate, grid_max=20):
    if not all(math.isfinite(x) and x > 0 for x in [home_rate, away_rate]):
        raise ValueError("invalid_goal_rate")
    distributions = []
    for rate in [home_rate, away_rate]:
        p = [math.exp(-rate)]
        for k in range(1, grid_max + 1):
            p.append(p[-1] * rate / k)
        distributions.append(p)
    probs = [0.0, 0.0, 0.0]
    scores = []
    mass = 0.0
    for h, ph in enumerate(distributions[0]):
        for a, pa in enumerate(distributions[1]):
            p = ph * pa
            mass += p
            probs[0 if h > a else 1 if h == a else 2] += p
            scores.append({"home": h, "away": a, "probability": p})
    return {"probabilities": [p / mass for p in probs], "expected_home_goals": home_rate, "expected_away_goals": away_rate, "top_scorelines": sorted(scores, key=lambda s: -s["probability"])[:5], "tail_mass": max(0, 1 - mass), "normalization": "1X2 conditioned on grid 0..20; scoreline probabilities retain raw mass"}


def elo_probabilities(difference):
    q = 10 ** ((difference + PARAMS["home_advantage"]) / 400)
    tie = PARAMS["elo_draw_nu"] * math.sqrt(q)
    return [q / (q + tie + 1), tie / (q + tie + 1), 1 / (q + tie + 1)]


class LeagueState:
    def __init__(self):
        self.results = deque(maxlen=PARAMS["league_window"])
        self.venues = defaultdict(lambda: deque(maxlen=PARAMS["venue_window"]))
        self.forms = defaultdict(lambda: deque(maxlen=5))
        self.elo = {}
        self.last_date = None
        self.season = None
        self.count = 0

    def start_season(self, season):
        if self.season is not None and season != self.season:
            self.elo = {team: 1500 + (elo - 1500) * PARAMS["season_elo_retention"] for team, elo in self.elo.items()}
        self.season = season

    def snapshot(self, match):
        if self.last_date and self.last_date >= match["date"]:
            raise ValueError("future_or_same_day_leakage")
        k = PARAMS["league_prior_matches"]
        lh = (sum(s[0] for s in self.results) + k * PARAMS["prior_home_goals"]) / (len(self.results) + k)
        la = (sum(s[1] for s in self.results) + k * PARAMS["prior_away_goals"]) / (len(self.results) + k)
        home = self.venues.get((match["home_id"], "home"), [])
        away = self.venues.get((match["away_id"], "away"), [])
        k = PARAMS["team_prior_matches"]
        ha = (sum(s[0] for s in home) + k * lh) / (len(home) + k) / lh
        hd = (sum(s[1] for s in home) + k * la) / (len(home) + k) / la
        aa = (sum(s[0] for s in away) + k * la) / (len(away) + k) / la
        ad = (sum(s[1] for s in away) + k * lh) / (len(away) + k) / lh
        def form(team):
            return sum(self.forms.get(team, [])) / max(1, len(self.forms.get(team, [])))
        vector = [self.elo.get(match["home_id"], 1500) - self.elo.get(match["away_id"], 1500), ha, hd, aa, ad, lh, la, len(home), len(away), form(match["home_id"]), form(match["away_id"])]
        rates = [max(0.15, min(5, lh * ha * ad)), max(0.15, min(5, la * aa * hd))]
        prior = [4.5, 2.5, 3.0]
        for h, a in self.results:
            prior[0 if h > a else 1 if h == a else 2] += 1
        return {"features": vector, "feature_schema_version": "features-v1", "information_cutoff_date": self.last_date, "match_date": match["date"], "history_matches": self.count, "cold_start": min(len(home), len(away)) < 5, "league_prior": [p / sum(prior) for p in prior], "elo": elo_probabilities(vector[0]), "poisson": poisson_prediction(*rates), "home_rate": rates[0], "away_rate": rates[1]}

    def update_batch(self, matches):
        if not matches:
            return
        days = {m["date"] for m in matches}
        if len(days) != 1 or (self.last_date and next(iter(days)) <= self.last_date):
            raise ValueError("non_chronological_update")
        changes = defaultdict(float)
        for m in matches:
            h, a = m["goals"]
            home_elo, away_elo = self.elo.get(m["home_id"], 1500), self.elo.get(m["away_id"], 1500)
            expected = 1 / (1 + 10 ** ((away_elo - home_elo - PARAMS["home_advantage"]) / 400))
            delta = PARAMS["elo_k"] * ((1 if h > a else 0.5 if h == a else 0) - expected)
            changes[m["home_id"]] += delta
            changes[m["away_id"]] -= delta
            self.results.append([h, a])
            self.venues[(m["home_id"], "home")].append([h, a])
            self.venues[(m["away_id"], "away")].append([a, h])
            self.forms[m["home_id"]].append(3 if h > a else 1 if h == a else 0)
            self.forms[m["away_id"]].append(3 if a > h else 1 if h == a else 0)
            self.count += 1
        for team, delta in changes.items():
            self.elo[team] = self.elo.get(team, 1500) + delta
        self.last_date = next(iter(days))

    def to_dict(self):
        return {"results": list(self.results), "venues": [[team, venue, list(v)] for (team, venue), v in sorted(self.venues.items())], "forms": {k: list(v) for k, v in sorted(self.forms.items())}, "elo": dict(sorted(self.elo.items())), "last_date": self.last_date, "season": self.season, "count": self.count}

    @classmethod
    def from_dict(cls, value):
        state = cls()
        state.results.extend(value["results"])
        for team, venue, values in value["venues"]:
            state.venues[(team, venue)].extend(values)
        for team, values in value["forms"].items():
            state.forms[team].extend(values)
        for key in ["elo", "last_date", "season", "count"]:
            setattr(state, key, value[key])
        return state


def replay(matches):
    states = defaultdict(LeagueState)
    rows = []
    ordered = sorted(matches, key=lambda m: (m["date"], m["league"], m["id"]))
    for day, day_matches in groupby(ordered, key=lambda m: m["date"]):
        grouped = defaultdict(list)
        for match in day_matches:
            grouped[match["league"]].append(match)
        for league, batch in grouped.items():
            state = states[league]
            state.start_season(batch[0]["season"])
            for match in batch:
                s = state.snapshot(match)
                h, a = match["goals"]
                rows.append({"id": match["id"], "league": league, "season": match["season"], "date": day, "target": 0 if h > a else 1 if h == a else 2, **s})
            state.update_batch(batch)
    return sorted(rows, key=lambda r: (r["date"], r["id"])), states
