import numpy as np
from scipy.optimize import minimize
from src.logger import get_logger
from .forward_model import build_time_axis

logger = get_logger(__name__)


# ============================================================
# Voigt time-domain model
# ============================================================

def _build_model(basis_dict, t, theta, baseline_order=6):

    names = list(basis_dict.keys())
    M = len(names)

    c = theta[:M]
    gamma = theta[M]
    sigma = theta[M+1]
    phi0 = theta[M+2]
    phi1 = theta[M+3]
    beta = theta[M+4:]

    T = len(t)
    model = np.zeros(T, dtype=np.complex128)

    for i, name in enumerate(names):
        fid = basis_dict[name]

        lorentz = np.exp(-gamma * t)
        gauss = np.exp(-(sigma * t)**2)
        phase = np.exp(1j*(phi0 + phi1*t))

        model += c[i] * fid * lorentz * gauss * phase

    # Baseline (real polynomial in frequency domain style)
    f = np.linspace(-1, 1, T)
    baseline = np.zeros(T)

    for k, b in enumerate(beta):
        baseline += b * f**k

    return model + baseline


# ============================================================
# Negative log-likelihood
# ============================================================

def _neg_log_likelihood(theta, y, t, basis_dict, noise_sigma, baseline_order):
    y_hat = _build_model(basis_dict, t, theta, baseline_order)
    residual = y - y_hat
    return np.real(np.vdot(residual, residual)) / (2 * noise_sigma**2)


# ============================================================
# MH Optimizer (FSL-like)
# ============================================================

def run_mh(
    spectrum,
    dwell_time,
    basis_dict,
    n_samples=3000,
    burn_in=1000,
    baseline_order=6
):

    logger.info("[MH] Starting FSL-like MH")

    y = np.asarray(spectrum, dtype=np.complex128)

    # Normalisation comme FSL
    scale = np.max(np.abs(y))
    if scale == 0:
        raise ValueError("Zero spectrum")
    y = y / scale

    T = len(y)
    t = build_time_axis(T, dwell_time)

    names = list(basis_dict.keys())
    M = len(names)

    dim = M + 4 + (baseline_order + 1)

    # ========================================================
    # 1️⃣ MAP INITIALISATION (équivalent Newton FSL)
    # ========================================================

    theta0 = np.zeros(dim)
    theta0[:M] = 0.1
    theta0[M] = 5.0
    theta0[M+1] = 2.0

    bounds = [(0, None)]*M + \
             [(0, 20), (0, 20), (-np.pi, np.pi), (-50, 50)] + \
             [(-1,1)]*(baseline_order+1)

    res = minimize(
        _neg_log_likelihood,
        theta0,
        args=(y, t, basis_dict, 0.01, baseline_order),
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter":500}
    )

    theta_map = res.x
    logger.info("[MH] MAP initialised")

    # ========================================================
    # 2️⃣ MH Sampling autour du MAP
    # ========================================================

    theta = theta_map.copy()
    proposal_std = np.ones(dim) * 0.005
    proposal_std[:M] = 0.01

    samples = []
    accepted = 0

    current_ll = -_neg_log_likelihood(theta, y, t, basis_dict, 0.01, baseline_order)

    for i in range(n_samples):

        theta_prop = theta + np.random.normal(0, proposal_std)

        # contraintes amplitudes positives
        theta_prop[:M] = np.clip(theta_prop[:M], 0, None)

        prop_ll = -_neg_log_likelihood(theta_prop, y, t, basis_dict, 0.01, baseline_order)

        if np.log(np.random.rand()) < (prop_ll - current_ll):
            theta = theta_prop
            current_ll = prop_ll
            accepted += 1

        if i >= burn_in:
            samples.append(theta.copy())

    logger.info(f"[MH] Acceptance rate = {accepted/n_samples:.3f}")

    samples = np.array(samples)
    mean_theta = np.mean(samples, axis=0)

    concentrations = mean_theta[:M]

    logger.info("[MH] Finished")

    return dict(zip(names, concentrations))