import numpy as np
from src.logger import get_logger

logger = get_logger(__name__)

def build_time_axis(T, dwell_time):
    t = np.arange(T) * dwell_time
    #logger.debug(f"[ForwardModel] T={T}, dwell_time={dwell_time}")
    return t

def build_design_matrix(basis_dict, t, gamma, phi0, phi1):
    names = list(basis_dict.keys())
    M = len(names)
    T = len(t)

    H = np.zeros((T, M), dtype=np.complex128)

    distortion = np.exp(-gamma * t) * np.exp(1j*(phi0 + phi1*t))

    for i, name in enumerate(names):
        base = basis_dict[name]
        if len(base) != T:
            raise ValueError(f"Basis length mismatch for {name}")
        H[:, i] = base * distortion

    #logger.debug(f"[ForwardModel] Design matrix shape={H.shape}")
    return H, names