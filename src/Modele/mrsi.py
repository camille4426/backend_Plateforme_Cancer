import os
import tempfile
import numpy as np
import nibabel as nib
from fastapi import UploadFile
from src.logger import get_logger

logger = get_logger(__name__)

class MRSI:
    """
    Classe pour fichiers MRSI (.nii).
    Objectif:
      - renvoyer une "carte voxels" (résumé d'intensité)
      - renvoyer un spectre pour un voxel donné
    """

    def __init__(self, nom: str, fichier: UploadFile):
        self.nom = nom
        self.fichier = fichier
        self.img = None
        self.data = None  # numpy array

    def _save_upload_to_temp(self) -> str:
        suffix = ".nii"
        if self.fichier.filename and self.fichier.filename.lower().endswith(".nii.gz"):
            suffix = ".nii.gz"

        try:
            self.fichier.file.seek(0)
        except Exception:
            pass

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(self.fichier.file.read())
            return tmp.name

    def load(self):
        tmp_path = self._save_upload_to_temp()
        try:
            self.img = nib.load(tmp_path)  # :contentReference[oaicite:6]{index=6}
            self.data = self.img.get_fdata()  # :contentReference[oaicite:7]{index=7}
            logger.info(f"MRSI chargée: shape={self.data.shape}, dtype={self.data.dtype}")
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    def _to_uint8_slice(self, sl: np.ndarray) -> np.ndarray:
        """
        Normalise une coupe 2D en uint8 [0..255].
        """
        sl = np.asarray(sl, dtype=np.float32)
        vmin, vmax = np.nanmin(sl), np.nanmax(sl)
        if vmin == vmax:
            return np.zeros_like(sl, dtype=np.uint8)
        out = (sl - vmin) / (vmax - vmin)
        return (out * 255).astype(np.uint8)

    def voxel_map(self, z=None, method="sum_abs"):
        """
        Construit une carte MRSI à partir des spectres.

        - data shape attendue: (16,16,8,512)
        - z optionnel: renvoie une coupe 2D (16x16)
        """

        if self.data is None:
            self.load()

        d = self.data

        if d.ndim != 4:
            return {
                "error": f"MRSI attendue en 4D (X,Y,Z,T). Reçu ndim={d.ndim}",
                "shape": list(d.shape),
            }

        # ---- Calcul voxel map 3D ----
        if method == "max_abs":
            vm = np.max(np.abs(d), axis=-1)   # (16,16,8)
        elif method == "sum":
            vm = np.sum(d, axis=-1)
        else:  # sum_abs par défaut
            vm = np.sum(np.abs(d), axis=-1)

        # ---- Si on veut une coupe 2D ----
        if z is not None:
            z = int(z)
            vm2d = vm[:, :, z]   # (16,16)
            vm2d_norm = self._to_uint8_slice(vm2d)
            return {
                "type": "MRSI",
                "nom": self.nom,
                "z": z,
                "voxel_map_2d": vm2d_norm.tolist(),
                "shape": list(vm2d.shape),
                "method": method
            }

        # ---- Sinon on renvoie toutes les coupes pour la slider navigation ----
    def get_all_voxel_maps(self, method="sum_abs"):
        """
        Renvoie TOUTES les coupes de la voxel map.
        """
        if self.data is None:
            self.load()
        
        d = self.data
        if d.ndim != 4:
            return {"error": "MRSI non 4D"}

        if method == "max_abs":
            vm = np.max(np.abs(d), axis=-1)
        elif method == "sum":
            vm = np.sum(d, axis=-1)
        else:
            vm = np.sum(np.abs(d), axis=-1)

        X, Y, Z = vm.shape
        slices = []
        for i in range(Z):
            slices.append(self._to_uint8_slice(vm[:, :, i]).tolist())

        return {
            "type": "MRSI",
            "nom": self.nom,
            "voxel_map_all": slices,
            "shape": [int(X), int(Y), int(Z)],
            "method": method
        }


    def get_spectrum(self, x: int, y: int, z: int):
        """
        Renvoie le spectre 1D du voxel (x,y,z).
        Alias de spectrum() pour correspondre à la demande.
        """
        return self.spectrum(x, y, z)

    def spectrum(self, x: int, y: int, z: int):
        """
        Renvoie le spectre 1D du voxel (x,y,z) si data est 4D (X,Y,Z,T).
        """
        if self.data is None:
            self.load()
        if self.data is None:
            return {"error": "Impossible de charger la MRSI"}

        d = self.data
        if d.ndim != 4:
            return {"error": f"Spectre voxel nécessite une MRSI 4D (X,Y,Z,T). Reçu ndim={d.ndim}", "shape": list(d.shape)}

        X, Y, Z, T = d.shape
        if not (0 <= x < X and 0 <= y < Y and 0 <= z < Z):
            return {"error": "Indices voxel hors limites", "shape": [int(X), int(Y), int(Z), int(T)]}

        sp = d[int(x), int(y), int(z), :]
        # JSON-friendly
        return {
            "type": "MRSI",
            "nom": self.nom,
            "voxel": {"x": int(x), "y": int(y), "z": int(z)},
            "T": int(T),
            "spectrum": sp.tolist(),
        }
        

    def summary(self):
        shape = self.data.shape if self.data is not None else None
        return {"type": "MRSI", "nom": self.nom, "shape": shape}
