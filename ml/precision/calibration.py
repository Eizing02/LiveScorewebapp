"""Calibration uses genuinely out-of-time predictions from earlier seasons only."""
import numpy as np
from scipy.optimize import minimize, minimize_scalar
from scipy.special import expit, logit


def validate_probabilities(values):
    p = np.asarray(values, dtype=float)
    if p.ndim != 2 or p.shape[1] != 3 or not np.all(np.isfinite(p)) or np.any(p < 0) or np.any(p > 1) or not np.allclose(p.sum(axis=1), 1, atol=1e-7):
        raise ValueError("invalid_probabilities")
    return p


def temperature_transform(values, temperature):
    if not .5 <= temperature <= 3:
        raise ValueError("invalid_temperature")
    p = validate_probabilities(values)
    z = np.log(np.clip(p, 1e-15, 1))/temperature
    e = np.exp(z-z.max(axis=1, keepdims=True))
    return e/e.sum(axis=1, keepdims=True)


def fit_temperature(values, labels, dates, cutoff):
    p = validate_probabilities(values)
    y = np.asarray(labels, dtype=int)
    if len(y) != len(p) or len(dates) != len(p) or any(day >= cutoff for day in dates):
        raise ValueError("calibration_temporal_leakage")
    if len(y) < 300:
        return 1.0
    def objective(t):
        q = temperature_transform(p, t)
        return -np.log(np.clip(q[np.arange(len(y)), y], 1e-15, 1)).mean()
    result = minimize_scalar(objective, bounds=(.5, 3), method="bounded", options={"xatol": 1e-8})
    if not result.success:
        raise ValueError("temperature_fit_failed")
    return float(result.x)


def platt_transform(probabilities, parameters):
    p = np.asarray(probabilities, dtype=float)
    if np.any(~np.isfinite(p)) or np.any(p < 0) or np.any(p > 1):
        raise ValueError("invalid_binary_probability")
    return expit(parameters[0]*logit(np.clip(p, 1e-9, 1-1e-9))+parameters[1])


def fit_platt(probabilities, labels, dates, cutoff):
    p, y = np.asarray(probabilities, dtype=float), np.asarray(labels, dtype=float)
    if len(p) != len(y) or len(dates) != len(y) or any(d >= cutoff for d in dates) or np.any((y != 0) & (y != 1)):
        raise ValueError("binary_calibration_temporal_or_label_error")
    if len(p) < 300 or len(np.unique(y)) < 2:
        return [1.0, 0.0]
    x = logit(np.clip(p, 1e-9, 1-1e-9))
    def objective(theta):
        z = theta[0]*x+theta[1]
        delta = theta-np.array([1., 0.])
        loss = np.mean(np.logaddexp(0, z)-y*z)+np.dot(delta, delta)/(2*len(y))
        residual = expit(z)-y
        gradient = np.array([np.mean(residual*x), residual.mean()])+delta/len(y)
        return float(loss), gradient
    result = minimize(objective, [1., 0.], jac=True, method="L-BFGS-B", bounds=[(.1, 3), (-3, 3)])
    if not result.success:
        raise ValueError("binary_calibration_failed")
    return result.x.tolist()
