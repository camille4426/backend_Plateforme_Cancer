import numpy as np
from src.logger import get_logger
from src.Modele.Traitement.quantification.quantifier import Quantifier
import os

logger = get_logger(__name__)

class QuantificationTraitement:

    def __init__(self, instance):
        """
        instance = objet MRSI
        """
        self.instance = instance
        self.params = {}

    @staticmethod
    def get_catalog_entry():
        return {
            "label": "Quantification",
            "type": ["MRSI"],
            "params": {
                "x": {
                    "label": "Coordonnée X",
                    "type": "int",
                    "range": [0, 64],
                    "default": 0
                },
                "y": {
                    "label": "Coordonnée Y",
                    "type": "int",
                    "range": [0, 64],
                    "default": 0
                },
                "z": {
                    "label": "Coordonnée Z",
                    "type": "int",
                    "range": [0, 32],
                    "default": 0
                },
                "method": {
                    "label": "Méthode",
                    "type_param": "choix",
                    "select": ["newton", "mh", "mcmc"],
                    "default": "newton"
                }
            }
        }
    def run(self, x: int, y: int, z: int, method: str = "newton"):

        logger.info(f"[QuantificationTraitement] Start voxel=({x},{y},{z}), method={method}")

        if self.instance.data is None:
            self.instance.load()

        d = self.instance.data

        if d.ndim != 4:
            raise ValueError("Quantification nécessite une MRSI 4D")

        X, Y, Z, T = d.shape

        if not (0 <= x < X and 0 <= y < Y and 0 <= z < Z):
            raise ValueError("Indices voxel hors limites")

        spectrum = d[x, y, z, :]

        

        logger.info(f"Spectrum dtype: {spectrum.dtype}")
        logger.info(f"Spectrum sample: {spectrum[:5]}")

        # Normalize spectrum (important for stable fitting)
        max_val = np.max(np.abs(spectrum))
        if max_val > 0:
            spectrum = spectrum / max_val

            
        dwell_time = float(self.instance.img.header.get_zooms()[3]) \
            if len(self.instance.img.header.get_zooms()) > 3 else 1e-3

        logger.debug(f"[QuantificationTraitement] dwell_time={dwell_time}, T={T}")

        if np.iscomplexobj(spectrum):
            logger.info("Using complex fitting model")
        else:
            logger.warning("Spectrum is real — imaginary part unavailable")

        current_dir = os.path.dirname(os.path.abspath(__file__))
        basis_path = os.path.join(current_dir, "quantification", "basis")

        if not os.path.exists(basis_path):
            raise RuntimeError(f"Dossier basis introuvable: {basis_path}")

        quantifier = Quantifier(basis_path)


        #quantifier = Quantifier(r"C:\Users\souma\Documents\backend_Plateforme_Cancer-main\src\Modele\Traitement\quantification\basis")

        results = quantifier.quantify(
            spectrum=spectrum,
            dwell_time=dwell_time,
            method=method
        )

        self.params = {
            "x": x,
            "y": y,
            "z": z,
            "method": method
        }

        logger.info("[QuantificationTraitement] Success")

        return {
            "type": "MRSI",
            "nom": self.instance.nom,   # important pour le frontend
            "voxel": {"x": x, "y": y, "z": z},
            "method": method,
            "quantification": results
        }