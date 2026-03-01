import numpy as np
from scipy.optimize import minimize
from src.logger import get_logger
from .forward_model import build_time_axis

logger = get_logger(__name__)


# ============================================================
# Forward Voigt model (identique MH)
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

    # Polynomial baseline
    f = np.linspace(-1, 1, T)
    baseline = np.zeros(T)

    for k, b in enumerate(beta):
        baseline += b * f**k

    return model + baseline


# ============================================================
# Log posterior
# ============================================================

def _log_posterior(theta, y, t, basis_dict, noise_sigma, baseline_order):

    y_hat = _build_model(basis_dict, t, theta, baseline_order)
    residual = y - y_hat

    # Gaussian likelihood
    ll = -np.real(np.vdot(residual, residual)) / (2 * noise_sigma**2)

    # Weak Gaussian priors for stability
    prior = -0.001 * np.sum(theta**2)

    return ll + prior


# ============================================================
# MCMC sampler
# ============================================================

def run_mcmc(
    spectrum,
    dwell_time,
    basis_dict,
    n_samples=5000,
    burn_in=1500,
    baseline_order=6
):

    logger.info("[MCMC] Starting MCMC")

    y = np.asarray(spectrum, dtype=np.complex128)

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
    # 1️⃣ MAP Initialisation (like FSL)
    # ========================================================

    theta0 = np.zeros(dim)
    theta0[:M] = 0.1
    theta0[M] = 5.0
    theta0[M+1] = 2.0

    bounds = [(0, None)]*M + \
             [(0, 20), (0, 20), (-np.pi, np.pi), (-50, 50)] + \
             [(-1,1)]*(baseline_order+1)

    def neg_ll(theta):
        return -_log_posterior(theta, y, t, basis_dict, 0.01, baseline_order)

    res = minimize(
        neg_ll,
        theta0,
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter":500}
    )

    theta = res.x
    logger.info("[MCMC] MAP initialised")

    # ========================================================
    # 2️⃣ Metropolis-Hastings chain
    # ========================================================

    proposal_std = np.ones(dim) * 0.003
    proposal_std[:M] = 0.008

    samples = []
    accepted = 0

    current_lp = _log_posterior(theta, y, t, basis_dict, 0.01, baseline_order)

    logger.info("[MCMC] Sampling started")
    logger.info(f"[MCMC] Total samples={n_samples}, burn_in={burn_in}")

    proposal_std = np.ones(dim) * 0.003
    proposal_std[:M] = 0.008

    samples = []
    accepted = 0

    current_lp = _log_posterior(theta, y, t, basis_dict, 0.01, baseline_order)

    report_every = max(1, n_samples // 20)  # 5% progress

    for i in range(n_samples):

        theta_prop = theta + np.random.normal(0, proposal_std)

        # enforce positivity on concentrations
        theta_prop[:M] = np.clip(theta_prop[:M], 0, None)

        prop_lp = _log_posterior(theta_prop, y, t, basis_dict, 0.01, baseline_order)

        if np.log(np.random.rand()) < (prop_lp - current_lp):
            theta = theta_prop
            current_lp = prop_lp
            accepted += 1

        if i >= burn_in:
            samples.append(theta.copy())

        # ===== Progress reporting =====
        if i % report_every == 0 and i > 0:
            acc_rate = accepted / (i + 1)

            logger.info(
                f"[MCMC] Iter {i}/{n_samples} "
                f"({100*i/n_samples:.1f}%) | "
                f"Accept={acc_rate:.3f} | "
                f"LogPost={current_lp:.4f}"
            )

            if len(samples) > 50:
                temp_mean = np.mean(samples[-50:], axis=0)
                top_idx = np.argsort(temp_mean[:M])[::-1][:3]
                top_metabs = [
                    f"{names[j]}={temp_mean[j]:.3f}"
                    for j in top_idx
                ]
                logger.info(f"[MCMC] Current top metabolites: {top_metabs}")

                
    logger.info(f"[MCMC] Acceptance rate = {accepted/n_samples:.3f}")

    samples = np.array(samples)

    # Posterior mean
    mean_theta = np.mean(samples, axis=0)
    std_theta = np.std(samples, axis=0)

    concentrations = mean_theta[:M]
    uncertainties = std_theta[:M]

    logger.info("[MCMC] Finished")

    return {
        name: {
            "mean": float(concentrations[i]),
            "std": float(uncertainties[i])
        }
        for i, name in enumerate(names)
    }