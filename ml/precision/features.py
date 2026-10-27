"""Whole-date replay with richer pre-match features and two-month goal refits."""
import hashlib
import json
import platform
from collections import defaultdict, deque
from datetime import date
from itertools import groupby

import numpy as np
import scipy

from ml.expanded import CONFIG as DATA_CONFIG, OUTPUT
from ml.models import FEATURES as LEGACY_FEATURES, LeagueState
from ml.pipeline import ROOT, digest, write_json, write_jsonl
from ml.precision.goals import DixonColes

CONFIG = json.loads((ROOT / "ml/config/precision_v3.json").read_text(encoding="utf-8"))
LEAGUES = sorted(DATA_CONFIG["leagues"])
TEAM_FEATURES = ["ppg5", "ppg10", "ppg20", "gf5", "ga5", "gf20", "ga20", "opponent_elo10", "opponent_adjusted_points10", "last365_matches", "current_season_matches", "league_gap_days", "known_history"]
FEATURES = LEGACY_FEATURES+[side+"_"+feature for side in ["home", "away"] for feature in TEAM_FEATURES]+["dc_home_rate", "dc_away_rate", "dc_total", "dc_rate_difference", "dc_draw", "dc_cold_teams", "league_draw_frequency", "league_over25_frequency", "league_btts_frequency"]+["league_"+league for league in LEAGUES]
CACHE = ROOT / "data/processed/precision-v3"


def team_features(records, day, season, prior_goals, prior_points):
    values = list(records)
    def avg(key, window, prior):
        recent = values[-window:]
        return (sum(r[key] for r in recent)+3*prior)/(len(recent)+3)
    recent = values[-10:]
    gap = min(365, (date.fromisoformat(day)-date.fromisoformat(values[-1]["date"])).days) if values else 365
    last365 = sum((date.fromisoformat(day)-date.fromisoformat(r["date"])).days <= 365 for r in values)
    return [avg("points", w, prior_points) for w in [5, 10, 20]]+[avg("gf", 5, prior_goals), avg("ga", 5, prior_goals), avg("gf", 20, prior_goals), avg("ga", 20, prior_goals), avg("opponent_elo", 10, 1500), sum(r["points"]-r["expected_points"] for r in recent)/(len(recent)+3), last365, sum(r["season"] == season for r in values), gap, int(bool(values))]


def cache_signature():
    quality = json.loads((OUTPUT / "quality-report.json").read_text(encoding="utf-8"))
    files = ["ml/precision/features.py", "ml/precision/goals.py", "ml/config/precision_v3.json", "ml/models.py"]
    return digest([quality["dataset_version"], {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files}, {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__, "os": platform.system(), "machine": platform.machine()}])


def build(matches=None, use_cache=True):
    signature = cache_signature()
    manifest_path = CACHE / "manifest.json"
    if matches is None and use_cache and manifest_path.exists() and json.loads(manifest_path.read_text(encoding="utf-8"))["signature"] == signature:
        return [json.loads(line) for line in (CACHE / "features.jsonl").read_text(encoding="utf-8").splitlines()]
    source = matches if matches is not None else [json.loads(line) for line in (OUTPUT / "accepted.jsonl").read_text(encoding="utf-8").splitlines()]
    source = sorted(source, key=lambda r: (r["date"], r["league"], r["id"]))
    states, histories, teams, goal_cache = defaultdict(LeagueState), defaultdict(list), defaultdict(lambda: deque(maxlen=100)), {}
    rows, fit_log = [], []
    for day, day_matches in groupby(source, key=lambda r: r["date"]):
        batch = list(day_matches)
        grouped = defaultdict(list)
        for match in batch:
            grouped[match["league"]].append(match)
        pending = []
        for league, games in grouped.items():
            state = states[league]
            state.start_season(games[0]["season"])
            history = histories[league]
            bucket = day[:4]+"-"+str((int(day[5:7])-1)//2)
            for model_config in CONFIG["goal_models"]:
                key = (league, model_config["id"])
                if len(history) >= CONFIG["goal_min_history"] and (key not in goal_cache or goal_cache[key][0] != bucket):
                    model = DixonColes(model_config["half_life_days"], model_config["ridge"]).fit(history, day)
                    goal_cache[key] = (bucket, model)
                    fit_log.append({"league": league, "model": model_config["id"], "asof": day, "last_training_date": model.training_last_date, "n": len(history), "rho": float(model.theta[-1])})
            for match in games:
                legacy = state.snapshot(match)
                dc = {}
                for model_config in CONFIG["goal_models"]:
                    key = (league, model_config["id"])
                    if key in goal_cache:
                        dc[model_config["id"]] = goal_cache[key][1].predict(match["home_id"], match["away_id"], day)
                    else:
                        from ml.goal_markets import goal_markets
                        dc[model_config["id"]] = {"probabilities": legacy["poisson"]["probabilities"], "home_rate": legacy["home_rate"], "away_rate": legacy["away_rate"], "markets": goal_markets(legacy["home_rate"], legacy["away_rate"]), "training_last_date": state.last_date, "training_cutoff": day, "training_matches": state.count, "unseen_teams": 2, "rho": 0.0, "fallback": True}
                main = dc["dc365-r4"]
                prior_goals = (legacy["features"][5]+legacy["features"][6])/2
                prior_points = (3-legacy["league_prior"][1])/2
                hf = team_features(teams[(league, match["home_id"])], day, match["season"], prior_goals, prior_points)
                af = team_features(teams[(league, match["away_id"])], day, match["season"], prior_goals, prior_points)
                league_rows = list(state.results)
                league_rates = [(sum(h == a for h, a in league_rows)+10*.25)/(len(league_rows)+10), (sum(h+a >= 3 for h, a in league_rows)+10*.5)/(len(league_rows)+10), (sum(h > 0 and a > 0 for h, a in league_rows)+10*.5)/(len(league_rows)+10)]
                vector = legacy["features"]+hf+af+[main["home_rate"], main["away_rate"], main["home_rate"]+main["away_rate"], main["home_rate"]-main["away_rate"], main["probabilities"][1], main["unseen_teams"]]+league_rates+[int(league == code) for code in LEAGUES]
                h, a = match["goals"]
                row = {"id": match["id"], "league": league, "season": match["season"], "date": day, "home_id": match["home_id"], "away_id": match["away_id"], "home": match["home"], "away": match["away"], "goals": match["goals"], "target": 0 if h > a else 1 if h == a else 2, "legacy_features": legacy["features"], "features": vector, "league_prior": legacy["league_prior"], "elo": legacy["elo"], "legacy_poisson": legacy["poisson"]["probabilities"], "dc": dc, "history_matches": state.count, "cutoff_date": state.last_date, "context": {"venue": legacy["features"][7:9], "last365": [hf[9], af[9]], "season_matches": [hf[10], af[10]], "gaps": [hf[11], af[11]]}}
                if state.count >= 40:
                    rows.append(row)
                pending.append((match, legacy["elo"], state.elo.get(match["home_id"], 1500), state.elo.get(match["away_id"], 1500)))
        # Neither the richer history nor the old state sees any same-date target before all predictions.
        for match, probabilities, home_elo, away_elo in pending:
            h, a = match["goals"]
            for side, gf, ga, opponent_elo, ep in [("home", h, a, away_elo, 3*probabilities[0]+probabilities[1]), ("away", a, h, home_elo, 3*probabilities[2]+probabilities[1])]:
                teams[(match["league"], match[side+"_id"])].append({"date": day, "season": match["season"], "gf": gf, "ga": ga, "points": 3 if gf > ga else 1 if gf == ga else 0, "opponent_elo": opponent_elo, "expected_points": ep})
        for league, games in grouped.items():
            states[league].update_batch(games)
            histories[league].extend(games)
    if matches is None:
        CACHE.mkdir(parents=True, exist_ok=True)
        write_jsonl(CACHE / "features.jsonl", rows)
        write_json(CACHE / "manifest.json", {"signature": signature, "rows": len(rows), "features": FEATURES, "feature_schema": "features-v3", "fit_log": fit_log, "temporal_invariant": "every history date and fitted goal model training date is strictly before target match date"})
        write_json(CACHE / "goal_models.json", {league+":"+model_id: model.to_dict() for (league, model_id), (_, model) in sorted(goal_cache.items())})
    return rows


if __name__ == "__main__":
    result = build()
    print(json.dumps({"rows": len(result), "features": len(FEATURES), "future_or_same_day_leakage": sum(bool(r["cutoff_date"] and r["cutoff_date"] >= r["date"]) for r in result)}))
