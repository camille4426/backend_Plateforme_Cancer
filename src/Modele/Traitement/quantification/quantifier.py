import numpy as np
from src.logger import get_logger
from .basis_loader import load_basis
from .newton_optimizer import run_newton
from .mh_optimizer import run_mh
from .mcmc_optimizer import run_mcmc

logger = get_logger(__name__)

class Quantifier:
    
    def __init__(self, basis_folder):
        logger.debug("[Quantifier] Initializing")
        self.basis = load_basis(basis_folder)
    
    def quantify(self, spectrum, dwell_time, method="newton"):
        
        logger.debug(f"[Quantifier] Method={method}")
        
        if spectrum is None:
            raise ValueError("Spectrum is None")
        
        """
        print("Spectrum length:", len(spectrum))
        for k, v in self.basis.items():
            print(f"{k} basis length:", len(v))
        """
        
        spectrum = np.asarray(spectrum)
        
        if spectrum.dtype != np.complex128:
            spectrum = spectrum.astype(np.complex128)
        

        
        if method == "newton":
            return run_newton(spectrum, dwell_time, self.basis)
        
        elif method == "mh":
            return run_mh(spectrum, dwell_time, self.basis)
        
        elif method == "mcmc":
            return run_mcmc(spectrum, dwell_time, self.basis)
        
        else:
            raise ValueError(f"Unknown method {method}")