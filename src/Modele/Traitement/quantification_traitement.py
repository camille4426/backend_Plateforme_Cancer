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
                },
                "all_voxels": {
                    "label": "Quantification de tous les voxels",
                    "type": "bool",
                    "default": False
                }
            }
        }
    def run(self, x: int = 0, y: int = 0, z: int = 0,
        method: str = "newton",
        all_voxels: bool = False):

        logger.info(f"[QuantificationTraitement] Start voxel=({x},{y},{z}), method={method}, all_voxels={all_voxels}")

        if self.instance.data is None:
            self.instance.load()

        d = self.instance.data

        if d.ndim != 4:
            raise ValueError("Quantification nécessite une MRSI 4D")

        X, Y, Z, T = d.shape

        dwell_time = float(self.instance.img.header.get_zooms()[3]) \
            if len(self.instance.img.header.get_zooms()) > 3 else 1e-3

        logger.debug(f"[QuantificationTraitement] dwell_time={dwell_time}, T={T}")

        current_dir = os.path.dirname(os.path.abspath(__file__))
        basis_path = os.path.join(current_dir, "quantification", "basis")

        if not os.path.exists(basis_path):
            raise RuntimeError(f"Dossier basis introuvable: {basis_path}")

        quantifier = Quantifier(basis_path)

        # ---------------------------------------------------
        # CAS 1 : VOXEL UNIQUE (comportement actuel)
        # ---------------------------------------------------
        if not all_voxels:

            if not (0 <= x < X and 0 <= y < Y and 0 <= z < Z):
                raise ValueError("Indices voxel hors limites")

            spectrum = d[x, y, z, :]

            logger.info(f"Spectrum dtype: {spectrum.dtype}")
            logger.info(f"Spectrum sample: {spectrum[:5]}")

            max_val = np.max(np.abs(spectrum))
            if max_val > 0:
                spectrum = spectrum / max_val

            if np.iscomplexobj(spectrum):
                logger.info("Using complex fitting model")
            else:
                logger.warning("Spectrum is real — imaginary part unavailable")

            results = quantifier.quantify(
                spectrum=spectrum,
                dwell_time=dwell_time,
                method=method
            )

            self.params = {
                "x": x,
                "y": y,
                "z": z,
                "method": method,
                "all_voxels": False
            }

            logger.info("[QuantificationTraitement] Success (single voxel)")

            return {
                "type": "MRSI",
                "nom": self.instance.nom,
                "voxel": {"x": x, "y": y, "z": z},
                "method": method,
                "quantification": results
            }

        # ---------------------------------------------------
        # CAS 2 : TOUS LES VOXELS
        # ---------------------------------------------------
        else:

            
            logger.info("[QuantificationTraitement] Full volume quantification started")

            volume_results = {}
            total_voxels = X * Y * Z
            processed = 0

            for i in range(X):
                for j in range(Y):
                    for k in range(Z):

                        spectrum = d[i, j, k, :]

                        # Skip voxels presque vides
                        if np.mean(np.abs(spectrum)) < 1e-6:
                            continue

                        max_val = np.max(np.abs(spectrum))
                        if max_val > 0:
                            spectrum = spectrum / max_val

                        try:
                            res = quantifier.quantify(
                                spectrum=spectrum,
                                dwell_time=dwell_time,
                                method=method
                            )
                            volume_results[f"{i}_{j}_{k}"] = res

                        except Exception as e:
                            logger.warning(f"Voxel ({i},{j},{k}) failed: {str(e)}")

                        processed += 1

                        if processed % 10 == 0:
                            logger.info(f"[Quantification] Progress {processed}/{total_voxels}")

            self.params = {
                "method": method,
                "all_voxels": True
            }
            logger.info(f"[QuantificationTraitement] all_voxels={all_voxels}")
            logger.info("[QuantificationTraitement] Success (full volume)")

            return {
                "type": "MRSI_VOLUME",
                "nom": self.instance.nom,
                "method": method,
                "dimensions": {
                    "X": int(X),
                    "Y": int(Y),
                    "Z": int(Z)
                },
                "total_voxels": total_voxels,
                "processed_voxels": len(volume_results),
                "quantification": volume_results
            }
            """
            logger.info("[QuantificationTraitement] Full volume quantification started")

            volume_results = {}
            total_voxels = X * Y * Z
            processed = 0

            # -------------------------
            # DEBUG CONFIG
            # -------------------------
            DEBUG_LIMIT = 30        # <-- set small number for fast debugging (e.g. 10)
            DEBUG_LOG_FIRST = 5     # log first N voxel results for inspection

            heatmap_metabolites = ["NAA", "Cr", "PCh"]  # metabolites expected by frontend
            debug_logged = 0

            for i in range(X):
                for j in range(Y):
                    for k in range(Z):

                        # ---- DEBUG STOP ----
                        if DEBUG_LIMIT > 0 and processed >= DEBUG_LIMIT:
                            logger.info(f"[DEBUG] Early stop at {processed} voxels")
                            break

                        spectrum = d[i, j, k, :]

                        # Skip almost empty voxels
                        if np.mean(np.abs(spectrum)) < 1e-6:
                            continue

                        max_val = np.max(np.abs(spectrum))
                        if max_val > 0:
                            spectrum = spectrum / max_val

                        try:
                            res = quantifier.quantify(
                                spectrum=spectrum,
                                dwell_time=dwell_time,
                                method=method
                            )

                            # -------------------------
                            # SANITIZE RESULTS (important for heatmaps)
                            # -------------------------
                            clean_res = {}
                            for met, value in res.items():
                                try:
                                    val = float(value)
                                    if np.isnan(val) or np.isinf(val):
                                        val = 0.0
                                    clean_res[met] = val
                                except Exception:
                                    clean_res[met] = 0.0

                            volume_results[f"{i}_{j}_{k}"] = clean_res

                            # -------------------------
                            # DEBUG LOG FIRST VOXELS
                            # -------------------------
                            if debug_logged < DEBUG_LOG_FIRST:
                                logger.info(f"[DEBUG] Voxel ({i},{j},{k}) → {clean_res}")
                                debug_logged += 1

                        except Exception as e:
                            logger.warning(f"Voxel ({i},{j},{k}) failed: {str(e)}")

                        processed += 1

                        if processed % 10 == 0:
                            logger.info(f"[Quantification] Progress {processed}/{total_voxels}")

                    if DEBUG_LIMIT > 0 and processed >= DEBUG_LIMIT:
                        break
                if DEBUG_LIMIT > 0 and processed >= DEBUG_LIMIT:
                    break


            # -------------------------
            # POST LOOP DEBUG SUMMARY
            # -------------------------
            logger.info(f"[DEBUG] Total stored voxels: {len(volume_results)}")

            # Inspect one sample voxel for frontend debugging
            if len(volume_results) > 0:
                sample_key = next(iter(volume_results))
                logger.info(f"[DEBUG] Sample voxel key: {sample_key}")
                logger.info(f"[DEBUG] Sample voxel values: {volume_results[sample_key]}")
            else:
                logger.warning("[DEBUG] No voxel results stored!")

            self.params = {
                "method": method,
                "all_voxels": True
            }

            logger.info(f"[QuantificationTraitement] all_voxels={all_voxels}")
            logger.info("[QuantificationTraitement] Success (full volume)")

            return {
                "type": "MRSI_VOLUME",
                "nom": self.instance.nom,
                "method": method,
                "dimensions": {
                    "X": int(X),
                    "Y": int(Y),
                    "Z": int(Z)
                },
                "total_voxels": total_voxels,
                "processed_voxels": len(volume_results),
                "quantification": volume_results
            }
            """