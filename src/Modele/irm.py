import os
import tempfile
import numpy as np
import nibabel as nib
from fastapi import UploadFile
from src.logger import get_logger

logger = get_logger(__name__)

class IRM:
    """
    Classe pour les fichiers IRM (.nii / .nii.gz).
    Objectif: charger le NIfTI et renvoyer quelques coupes prêtes à afficher côté front.
    """

    def __init__(self, fichier: UploadFile):
        self.fichier = fichier
        self.img = None
        self.data = None  # numpy array (float)

    def _save_upload_to_temp(self) -> str:
        """
        Sauvegarde le UploadFile dans un fichier temporaire (robuste pour nibabel.load()).
        Retourne le chemin du fichier.
        """
        suffix = ""
        if self.fichier.filename:
            lower = self.fichier.filename.lower()
            if lower.endswith(".nii.gz"):
                suffix = ".nii.gz"
            elif lower.endswith(".nii"):
                suffix = ".nii"
        if suffix == "":
            suffix = ".nii.gz"  # fallback

        # Important: on remet le pointeur au début si besoin
        try:
            self.fichier.file.seek(0)
        except Exception:
            pass

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(self.fichier.file.read())
            tmp_path = tmp.name

        return tmp_path

    def load(self):
        """
        Charge l'image NIfTI dans self.img + self.data.
        """
        tmp_path = self._save_upload_to_temp()
        try:
            self.img = nib.load(tmp_path)  # nibabel déduit le format depuis l'extension :contentReference[oaicite:4]{index=4}
            self.data = self.img.get_fdata()  # float avec scaling :contentReference[oaicite:5]{index=5}
            logger.info(f"IRM chargée: shape={self.data.shape}, dtype={self.data.dtype}")
        finally:
            # Nettoyage du fichier temporaire
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    @staticmethod
    def _to_uint8_slice(sl: np.ndarray) -> np.ndarray:
        """
        Normalise une coupe 2D en uint8 [0..255] (robuste aux images constantes).
        """
        sl = np.asarray(sl, dtype=np.float32)
        vmin = float(np.nanmin(sl))
        vmax = float(np.nanmax(sl))
        if not np.isfinite(vmin) or not np.isfinite(vmax) or vmax <= vmin:
            return np.zeros_like(sl, dtype=np.uint8)
        out = (sl - vmin) / (vmax - vmin)
        out = (255.0 * out).clip(0, 255).astype(np.uint8)
        return out

    def set_imgs_irm(self):
        """
        Renvoie 3 coupes centrales (sagittale/coronale/axiale) prêtes à afficher.
        Retour JSON-friendly: listes python.
        """
        if self.data is None:
            self.load()

        if self.data is None:
            return {"error": "Impossible de charger l'IRM"}

        # Si 4D (ex: time), on prend le premier volume
        vol = self.data
        if vol.ndim == 4 and vol.shape[-1] > 1:
            vol = vol[..., 0]

        if vol.ndim != 3:
            return {
                "error": f"IRM attendue en 3D (ou 4D), reçu ndim={vol.ndim}",
                "shape": list(self.data.shape),
            }

        X, Y, Z = vol.shape
        cx, cy, cz = X // 2, Y // 2, Z // 2

        # Couche sagittale: x=cx => (Y,Z)
        sag = self._to_uint8_slice(vol[cx, :, :])
        # Couche coronale: y=cy => (X,Z)
        cor = self._to_uint8_slice(vol[:, cy, :])
        # Couche axiale: z=cz => (X,Y)
        axi = self._to_uint8_slice(vol[:, :, cz])

        # Optionnel: transposer pour que l'affichage soit plus "naturel" côté front
        # (ça dépend du front; je laisse simple)
        return {
            "type": "IRM",
            "nom_fichier": self.fichier.filename,
            "shape": [int(X), int(Y), int(Z)],
            "slices": {
                "sagittal": sag.tolist(),
                "coronal": cor.tolist(),
                "axial": axi.tolist(),
            },
            "center": {"x": int(cx), "y": int(cy), "z": int(cz)},
        }

    def get_all_slices(self):
        """
        Renvoie TOUTES les coupes (sagittales, coronales, axiales) normalisées en uint8.
        """
        if self.data is None:
            self.load()

        if self.data is None:
            return {"error": "Impossible de charger l'IRM"}

        vol = self.data
        if vol.ndim == 4 and vol.shape[-1] > 1:
            vol = vol[..., 0]

        X, Y, Z = vol.shape

        # On normalise le volume complet pour garder une cohérence de contraste entre les coupes
        vmin, vmax = np.nanmin(vol), np.nanmax(vol)
        if vmin == vmax:
            norm_vol = np.zeros_like(vol, dtype=np.uint8)
        else:
            norm_vol = (vol - vmin) / (vmax - vmin)
            norm_vol = (norm_vol * 255).astype(np.uint8)

        # On prépare les listes pour le JSON
        # Sagittal: X stacks of (Y, Z)
        # Coronal: Y stacks of (X, Z)
        # Axial: Z stacks of (X, Y)
        
        slices_sag = [norm_vol[i, :, :].tolist() for i in range(X)]
        slices_cor = [norm_vol[:, i, :].tolist() for i in range(Y)]
        slices_axi = [norm_vol[:, :, i].tolist() for i in range(Z)]

        return {
            "type": "IRM",
            "nom_fichier": self.fichier.filename,
            "shape": [int(X), int(Y), int(Z)],
            "volumes": {
                "sagittal": slices_sag,
                "coronal": slices_cor,
                "axial": slices_axi,
            }
        }

    def summary(self):
        logger.info("irm.py (summary) : Retourne le sommaire")
        return {"type": "IRM", "nom_fichier": self.fichier.filename}

    
