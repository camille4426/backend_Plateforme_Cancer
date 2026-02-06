import numpy as np
from src.Modele.mrsi import MRSI
from src.logger import get_logger

logger = get_logger(__name__)

class METABOLITE_EXTRACTOR:
    """
    Extraction de métabolites voxel par voxel à partir d'une MRSI.
    Retourne des cartes 3D normalisées pour affichage front.
    """
    METABOLITES_RANGES = {
            "NAA": (10, 20),
            "Cr": (25, 35),
            "Cho": (40, 50)
    }


    def __init__(self, mrsi_instance: MRSI):
        self.mrsi = mrsi_instance
        if self.mrsi.data is None:
            self.mrsi.load()


    def run(self, metabolites : list | None = None):
        """
        Extraction de métabolites choisis (entre NAA, Cr, Cho).
    
        metabolites:
        None      -> tous les métabolites connus
        ["NAA"]   -> seulement NAA
        ["NAA","Cr"] -> sélection multiple
        """


        # Par défaut : tous
        if metabolites is None:
            metabolites = list(self.METABOLITES_RANGES.keys())

        results = {}

        for name in metabolites:
            freq_range = self.METABOLITES_RANGES.get(name)

            if freq_range is None:
                results[name] = {"error": f"metabolite inconnu : {name}"}
                continue

            results[name] = self.extract_by_freq_range(freq_range)

        return results
    

    def extract_by_freq_range(self, freq_range: tuple):
        """
        Extrait la carte 3D pour une plage de fréquences donnée.
        freq_range : tuple (min_idx, max_idx) sur l'axe T de la MRSI
        """
        d = self.mrsi.data  # shape (X,Y,Z,T)
        X, Y, Z, T = d.shape
        min_idx, max_idx = freq_range

        # Bornes sûres
        min_idx = max(0, min_idx)
        max_idx = min(T, max_idx)

        # Somme des amplitudes sur la plage de fréquences
        voxel_map = np.sum(np.abs(d[:, :, :, min_idx:max_idx]), axis=-1)  # shape (X,Y,Z)

        # Normalisation [0-255]
        vmin, vmax = voxel_map.min(), voxel_map.max()
        if vmin == vmax:
            norm_voxel_map = np.zeros_like(voxel_map, dtype=np.uint8)
        else:
            norm_voxel_map = ((voxel_map - vmin) / (vmax - vmin) * 255).astype(np.uint8)

        # Découpage en slices pour le front
        slices = [norm_voxel_map[:, :, z].tolist() for z in range(Z)]

        return {
            "type": "MRSI",
            "nom": f"{self._basename_no_ext(self.mrsi.nom)}_metabolite_{min_idx}_{max_idx}",
            "voxel_map_all": slices,
            "shape": [int(X), int(Y), int(Z)],
            "method": f"metabolite_{min_idx}_{max_idx}"
        }
    

    def _basename_no_ext(self, filename: str) -> str:
        """
        Retourne le nom de fichier sans extension, même pour .nii.gz
        """
        if filename.endswith(".nii.gz"):
            return filename[:-7]  # supprime ".nii.gz"
        elif filename.endswith(".nii"):
            return filename[:-4]  # supprime ".nii"
        else:
            return filename
