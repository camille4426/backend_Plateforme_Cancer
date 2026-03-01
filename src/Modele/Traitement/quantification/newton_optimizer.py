import numpy as np
from scipy.optimize import minimize
from src.logger import get_logger
from .forward_model import build_time_axis, build_design_matrix

logger = get_logger(__name__)

def run_newton(spectrum, dwell_time, basis_dict):
    #logger.debug("[Newton] Starting Newton optimization")
    
    y = np.asarray(spectrum, dtype=np.complex128)
    # Normalize spectrum
    scale = np.max(np.abs(y))
    if scale == 0:
        raise ValueError("Zero spectrum cannot be fitted.")
    y = y / scale

    T = len(y)
    
    t = build_time_axis(T, dwell_time)
    
    metabolites = list(basis_dict.keys())
    M = len(metabolites)
    
    # Normalize basis functions
    basis_norm = {}
    for name, base in basis_dict.items():
        b = np.asarray(base, dtype=np.complex128)
        b_scale = np.max(np.abs(b))
        if b_scale == 0:
            raise ValueError(f"Zero basis for {name}")
        basis_norm[name] = b / b_scale

        
    def objective(theta):
        c = theta[:M]
        gamma, phi0, phi1 = theta[M:]

        H, _ = build_design_matrix(basis_norm, t, gamma, phi0, phi1)
        y_hat = H @ c
        
        residual = y - y_hat
        loss = np.real(np.vdot(residual, residual))
        
        #logger.debug(f"[Newton] Loss={loss}")
        #logger.info(f"Normalized spectrum max: {np.max(np.abs(y))}")
        return loss
    
    theta0 = np.zeros(M + 3)
    theta0[:M] = 0.1  # initial concentration guess
    
    bounds = [(0, None)]*M + [(0,None), (-np.pi,np.pi), (-10,10)]
    
    result = minimize(
        objective,
        theta0,
        method="L-BFGS-B",
        bounds=bounds,
        options={
            "maxiter": 3000,
            "ftol": 1e-9,
            "gtol": 1e-6
        }
    )
    
    if not result.success:
        #logger.error(f"[Newton] Optimization failed: {result.message}")
        logger.warning(f"[Newton] Optimization did not fully converge: {result.message}")
    
    logger.info("[Newton] Optimization successful")
    
    concentrations = result.x[:M]
    
    return dict(zip(metabolites, concentrations))