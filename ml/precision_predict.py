"""Matching 58-feature forward engine. No target scores or synthetic labels."""
import json
import math
from collections import defaultdict, deque
from itertools import groupby

import numpy as np
import xgboost as xgb

from ml.evaluate import LogisticModel
from ml.models import LeagueState, elo_probabilities
from ml.pipeline import ROOT
from ml.precision.calibration import platt_transform, temperature_transform
from ml.precision.experiment import model_predictions
from ml.precision.features import FEATURES, LEAGUES, team_features
from ml.precision.goals import DixonColes
from ml.precision.selection import history_reasons


class PrecisionEngine:
    def __init__(self, version=None, matches=None):
        if version is None:
            version = json.loads((ROOT/"ml/models/precision-v3-registry.json").read_text(encoding="utf-8"))["candidate"]
        self.version = version
        self.directory = ROOT/"ml/models"/version
        self.meta = json.loads((self.directory/"metadata.json").read_text(encoding="utf-8"))
        import hashlib
        for name, expected in self.meta["checksums"].items():
            if hashlib.sha256((self.directory/name).read_bytes()).hexdigest() != expected:
                raise ValueError("precision_artifact_checksum_mismatch")
        self.selection = json.loads((self.directory/"selection.json").read_text(encoding="utf-8"))
        self.calibration = json.loads((self.directory/"forward-calibration.json").read_text(encoding="utf-8"))
        self.goal_models = {key: DixonColes.from_dict(value) for key, value in json.loads((self.directory/"goal-models.json").read_text(encoding="utf-8")).items()}
        self.models = {}
        for name in ["legacy-logistic", "enhanced-logistic"]:
            self.models[name] = LogisticModel.from_dict(json.loads((self.directory/(name+".json")).read_text(encoding="utf-8")))
        self.models["league-shrunk-logistic"] = {league: {"n": value["n"], "model": LogisticModel.from_dict(value["model"])} for league, value in json.loads((self.directory/"league-logistics.json").read_text(encoding="utf-8")).items()}
        for depth in [2, 3]:
            booster = xgb.Booster()
            booster.load_model(self.directory/f"enhanced-xgb-d{depth}.json")
            self.models[f"enhanced-xgb-d{depth}"] = booster
        self.matches = matches if matches is not None else [json.loads(line) for line in (ROOT/"data/processed/recent-v2/accepted.jsonl").read_text(encoding="utf-8").splitlines()]

    def snapshot(self, fixture, information_cutoff_exclusive=None):
        cutoff = information_cutoff_exclusive or self.meta["training_cutoff_exclusive"]
        day = fixture["date"]
        if cutoff > day:
            raise ValueError("prediction_cutoff_after_fixture_date")
        source = sorted((m for m in self.matches if m["date"] < cutoff), key=lambda m: (m["date"], m["id"]))
        states, teams = defaultdict(LeagueState), defaultdict(lambda: deque(maxlen=100))
        for history_day, items in groupby(source, key=lambda m: m["date"]):
            grouped = defaultdict(list)
            pending = []
            for match in items:
                grouped[match["league"]].append(match)
            for league, games in grouped.items():
                state = states[league]
                state.start_season(games[0]["season"])
                for match in games:
                    h_elo, a_elo = state.elo.get(match["home_id"], 1500), state.elo.get(match["away_id"], 1500)
                    p = elo_probabilities(h_elo-a_elo)
                    pending.append((match, p, h_elo, a_elo))
            for match, probabilities, home_elo, away_elo in pending:
                h, a = match["goals"]
                for side, gf, ga, opponent_elo, ep in [("home", h, a, away_elo, 3*probabilities[0]+probabilities[1]), ("away", a, h, home_elo, 3*probabilities[2]+probabilities[1])]:
                    teams[(match["league"], match[side+"_id"])].append({"date": history_day, "season": match["season"], "gf": gf, "ga": ga, "points": 3 if gf > ga else 1 if gf == ga else 0, "opponent_elo": opponent_elo, "expected_points": ep})
            for league, games in grouped.items():
                states[league].update_batch(games)
        league = fixture["league"]
        state = states[league]
        state.start_season(fixture["season"])
        legacy = state.snapshot(fixture)
        dc = {}
        for name in ["dc180-r4", "dc365-r4"]:
            model = self.goal_models.get(league+":"+name)
            if model is None or model.training_last_date >= cutoff:
                raise ValueError("goal_model_missing_or_not_available_at_cutoff")
            dc[name] = model.predict(fixture["home_id"], fixture["away_id"], day)
        main = dc["dc365-r4"]
        prior_goals = (legacy["features"][5]+legacy["features"][6])/2
        prior_points = (3-legacy["league_prior"][1])/2
        hf = team_features(teams[(league, fixture["home_id"])], day, fixture["season"], prior_goals, prior_points)
        af = team_features(teams[(league, fixture["away_id"])], day, fixture["season"], prior_goals, prior_points)
        league_rows = list(state.results)
        rates = [(sum(h == a for h, a in league_rows)+10*.25)/(len(league_rows)+10), (sum(h+a >= 3 for h, a in league_rows)+10*.5)/(len(league_rows)+10), (sum(h > 0 and a > 0 for h, a in league_rows)+10*.5)/(len(league_rows)+10)]
        vector = legacy["features"]+hf+af+[main["home_rate"], main["away_rate"], main["home_rate"]+main["away_rate"], main["home_rate"]-main["away_rate"], main["probabilities"][1], main["unseen_teams"]]+rates+[int(league == code) for code in LEAGUES]
        if len(vector) != len(FEATURES) or not np.all(np.isfinite(vector)):
            raise ValueError("precision_feature_schema_mismatch")
        row = {**fixture, "features": vector, "legacy_features": legacy["features"], "league_prior": legacy["league_prior"], "elo": legacy["elo"], "legacy_poisson": legacy["poisson"]["probabilities"], "dc": dc, "history_matches": state.count, "cutoff_date": state.last_date, "context": {"venue": legacy["features"][7:9], "last365": [hf[9], af[9]], "season_matches": [hf[10], af[10]], "gaps": [hf[11], af[11]]}}
        return row, state

    def predict(self, fixture, generated_at):
        if self.meta["training_cutoff_exclusive"] > generated_at[:10] or self.calibration["last_oof_date"] >= generated_at[:10]:
            raise ValueError("model_or_calibration_not_available_at_prediction_time")
        row, state = self.snapshot(fixture)
        head, method = self.selection["selected_model"].split(":")
        p = model_predictions(self.models, [row])[head]
        temperature = self.calibration["temperatures"][head] if method == "previous-oof-temperature" else 1.
        probabilities = temperature_transform(p, temperature)[0].tolist()
        policy = self.selection["selected_policy"]
        reasons = history_reasons(row, policy["layer"]) if policy else ["no_validation_policy_qualified"]
        if policy:
            if fixture["league"] not in policy["supported_leagues"]:
                reasons.append("league_not_supported_by_validation_sample")
            if max(probabilities) < policy["threshold"]:
                reasons.append("precision_probability_below_threshold")
        main = row["dc"]["dc365-r4"]
        scores = []
        for h in range(21):
            for a in range(21):
                ph = math.exp(-main["home_rate"])*main["home_rate"]**h/math.factorial(h)
                pa = math.exp(-main["away_rate"])*main["away_rate"]**a/math.factorial(a)
                from ml.precision.goals import dc_correction
                scores.append({"home": h, "away": a, "probability": float(ph*pa*dc_correction(h, a, main["home_rate"], main["away_rate"], main["rho"]))})
        market_probabilities = {}
        for market, chosen in self.selection["market_choices"].items():
            name, calibration_method = chosen.split(":")
            goal_name, weight_text = name.rsplit("-w", 1)
            weight = int(weight_text)/100
            prior = .5
            if market.startswith("over_"):
                line = float(market.split("_")[1])
                hits = sum(h+a > line for h, a in state.results)
                from ml.goal_markets import goal_markets
                prior = goal_markets(1.5, 1.2)[market]
            else:
                hits = sum(h > 0 and a > 0 for h, a in state.results)
                prior = (1-math.exp(-1.5))*(1-math.exp(-1.2))
            baseline = (hits+30*prior)/(len(state.results)+30)
            raw = weight*row["dc"][goal_name]["markets"][market]+(1-weight)*baseline
            parameters = self.calibration["markets"][market][name]
            value = float(platt_transform([raw], parameters)[0]) if calibration_method == "previous-oof-platt" else raw
            market_probabilities[market] = value
            market_probabilities[market.replace("over_", "under_") if market.startswith("over_") else "btts_no"] = 1-value
        if not (market_probabilities['over_1.5'] >= market_probabilities['over_2.5'] >= market_probabilities['over_3.5']) or market_probabilities['btts_yes'] > market_probabilities['over_1.5']+1e-8:
            raise ValueError("incoherent_calibrated_market_heads")
        last_dates = [teams[-1]["date"] if teams else "" for teams in [list_records(self.matches, fixture, "home", self.meta["training_cutoff_exclusive"]), list_records(self.matches, fixture, "away", self.meta["training_cutoff_exclusive"])]]
        return {"fixture_id": fixture["id"], "model_version": self.version+":"+self.selection["selected_model"], "model_name": head, "goal_model": "Dixon-Coles / ปรับตามคู่แข่ง", "generated_at": generated_at, "cutoff_date": row["cutoff_date"], "training_cutoff": self.meta["training_cutoff_exclusive"], "dataset_version": self.meta["dataset_version"], "probabilities": probabilities, "poisson_probabilities": main["probabilities"], "home_rate": main["home_rate"], "away_rate": main["away_rate"], "scorelines": sorted(scores, key=lambda s: -s["probability"])[:5], "markets": market_probabilities, "market_models": self.selection["market_choices"], "history_matches": row["history_matches"], "venue_matches": row["context"]["venue"], "last_result_dates": last_dates, "cold_start": min(row["context"]["venue"]) < 5, "mode": "mock_research", "locked": True, "feature_schema": "features-v3", "calibration_method": method, "selection_policy": None if policy is None else {"id": policy["id"], "threshold": policy["threshold"], "tier": policy["selected_tier"], "supported_leagues": policy["supported_leagues"]}, "research_eligible": not reasons, "research_rejection_reasons": reasons, "live_approved": False}


def list_records(matches, fixture, side, cutoff):
    return sorted((m for m in matches if m["league"] == fixture["league"] and m["date"] < min(fixture["date"], cutoff) and fixture[side+"_id"] in [m["home_id"], m["away_id"]]), key=lambda m: (m["date"], m["id"]))
