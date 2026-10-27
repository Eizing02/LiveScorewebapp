"""Opponent-adjusted, time-weighted penalized Dixon-Coles goal model."""
import math
from datetime import date

import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln

from ml.goal_markets import goal_markets


def dc_correction(h, a, home_rate, away_rate, rho):
    return np.where((h == 0) & (a == 0), 1-home_rate*away_rate*rho,
                    np.where((h == 0) & (a == 1), 1+home_rate*rho,
                             np.where((h == 1) & (a == 0), 1+away_rate*rho,
                                      np.where((h == 1) & (a == 1), 1-rho, 1.0))))


class DixonColes:
    def __init__(self, half_life_days=365, ridge=4):
        self.half_life_days = half_life_days
        self.ridge = ridge
        self.teams = []
        self.theta = None
        self.training_last_date = None
        self.cutoff = None
        self.n_training = 0

    def fit(self, matches, cutoff):
        if not matches or any(m["date"] >= cutoff for m in matches):
            raise ValueError("goal_training_future_or_empty")
        self.teams = sorted({m[side+"_id"] for m in matches for side in ["home", "away"]})
        lookup = {team: i for i, team in enumerate(self.teams)}
        n = len(self.teams)
        hi = np.array([lookup[m["home_id"]] for m in matches])
        ai = np.array([lookup[m["away_id"]] for m in matches])
        h = np.array([m["goals"][0] for m in matches], dtype=float)
        a = np.array([m["goals"][1] for m in matches], dtype=float)
        ages = np.array([(date.fromisoformat(cutoff)-date.fromisoformat(m["date"])).days for m in matches])
        weights = np.exp(-math.log(2)*ages/self.half_life_days)
        scale = weights.sum()
        factorial = gammaln(h+1)+gammaln(a+1)
        initial = np.zeros(3+2*n)
        initial[0] = math.log(max(.2, np.average(a, weights=weights)))
        initial[1] = math.log(max(.2, np.average(h, weights=weights)))-initial[0]
        initial[-1] = -.03
        lower, upper = math.log(.1), math.log(5)

        def objective(theta):
            mu, advantage, rho = theta[0], theta[1], theta[-1]
            attack, defence = theta[2:2+n], theta[2+n:2+2*n]
            eh = mu+advantage+attack[hi]+defence[ai]
            ea = mu+attack[ai]+defence[hi]
            lh, la = np.exp(np.clip(eh, lower, upper)), np.exp(np.clip(ea, lower, upper))
            tau = dc_correction(h, a, lh, la, rho)
            if np.any(tau <= 0):
                return 1e12, np.zeros_like(theta)
            losses = lh+la-h*np.log(lh)-a*np.log(la)+factorial-np.log(tau)
            z00, z01, z10, z11 = (h == 0) & (a == 0), (h == 0) & (a == 1), (h == 1) & (a == 0), (h == 1) & (a == 1)
            dh = np.where(z00, -lh*la*rho, np.where(z01, lh*rho, 0))
            da = np.where(z00, -lh*la*rho, np.where(z10, la*rho, 0))
            dr = np.where(z00, -lh*la, np.where(z01, lh, np.where(z10, la, np.where(z11, -1, 0))))
            gh = weights*(lh-h-dh/tau)*((eh > lower) & (eh < upper))/scale
            ga = weights*(la-a-da/tau)*((ea > lower) & (ea < upper))/scale
            gradient = np.zeros_like(theta)
            gradient[0], gradient[1] = (gh+ga).sum(), gh.sum()
            gradient[2:2+n] = np.bincount(hi, weights=gh, minlength=n)+np.bincount(ai, weights=ga, minlength=n)
            gradient[2+n:2+2*n] = np.bincount(ai, weights=gh, minlength=n)+np.bincount(hi, weights=ga, minlength=n)
            gradient[-1] = (-weights*dr/tau).sum()/scale
            # L2 identifies the attack/defence level and shrinks teams with few recent games.
            regularization = self.ridge/scale
            penalty = .5*regularization*(np.square(theta[2:-1]).sum()+.2*(mu-math.log(1.2))**2+.2*(advantage-math.log(1.25))**2)
            gradient[2:-1] += regularization*theta[2:-1]
            gradient[0] += regularization*.2*(mu-math.log(1.2))
            gradient[1] += regularization*.2*(advantage-math.log(1.25))
            return float(np.dot(weights, losses)/scale+penalty), gradient

        bounds = [(-2, 2), (-.6, .9)]+[(-2, 2)]*(2*n)+[(-.18, .03)]
        result = minimize(objective, initial, jac=True, method="L-BFGS-B", bounds=bounds, options={"maxiter": 400, "ftol": 1e-10, "gtol": 1e-6})
        if not result.success or not np.all(np.isfinite(result.x)):
            raise ValueError("dixon_coles_optimization_failed: "+str(result.message))
        self.theta = result.x
        self.index = lookup
        self.training_last_date = max(m["date"] for m in matches)
        self.cutoff, self.n_training = cutoff, len(matches)
        self.optimizer = {"success": True, "iterations": int(result.nit), "objective": float(result.fun)}
        return self

    def predict(self, home, away, target_date):
        if self.theta is None or self.training_last_date >= target_date or self.cutoff > target_date:
            raise ValueError("goal_model_unfitted_or_future")
        n = len(self.teams)
        theta = self.theta
        def strength(team, offset):
            return float(theta[offset+self.index[team]]) if team in self.index else 0.0
        lh = float(np.clip(np.exp(theta[0]+theta[1]+strength(home, 2)+strength(away, 2+n)), .1, 5))
        la = float(np.clip(np.exp(theta[0]+strength(away, 2)+strength(home, 2+n)), .1, 5))
        rho = float(theta[-1])
        ph, pa = np.exp(-lh)*lh**np.arange(21)/np.exp(gammaln(np.arange(21)+1)), np.exp(-la)*la**np.arange(21)/np.exp(gammaln(np.arange(21)+1))
        grid = np.outer(ph, pa)
        grid[0, 0] *= 1-lh*la*rho
        grid[0, 1] *= 1+lh*rho
        grid[1, 0] *= 1+la*rho
        grid[1, 1] *= 1-rho
        mass = float(grid.sum())
        p = [float(np.tril(grid, -1).sum()/mass), float(np.trace(grid)/mass), float(np.triu(grid, 1).sum()/mass)]
        markets = goal_markets(lh, la)
        adjustment = -rho*math.exp(-lh-la)*lh*la
        markets["over_1.5"] += adjustment
        markets["under_1.5"] = 1-markets["over_1.5"]
        markets["btts_yes"] += adjustment
        markets["btts_no"] = 1-markets["btts_yes"]
        return {"probabilities": p, "home_rate": lh, "away_rate": la, "rho": rho, "markets": markets, "tail_mass": max(0, 1-mass), "training_last_date": self.training_last_date, "training_cutoff": self.cutoff, "training_matches": self.n_training, "unseen_teams": int(home not in self.index)+int(away not in self.index)}

    def to_dict(self):
        return {"type": "penalized-time-weighted-dixon-coles-v3", "half_life_days": self.half_life_days, "ridge": self.ridge, "teams": self.teams, "theta": self.theta.tolist(), "training_last_date": self.training_last_date, "training_cutoff": self.cutoff, "training_matches": self.n_training, "optimizer": self.optimizer, "rates_clipped": [.1, 5], "rho_bounds": [-.18, .03]}

    @classmethod
    def from_dict(cls, value):
        model = cls(value["half_life_days"], value["ridge"])
        model.teams, model.theta = value["teams"], np.asarray(value["theta"], dtype=float)
        model.index = {team: i for i, team in enumerate(model.teams)}
        model.training_last_date, model.cutoff = value["training_last_date"], value["training_cutoff"]
        model.n_training, model.optimizer = value["training_matches"], value["optimizer"]
        return model
