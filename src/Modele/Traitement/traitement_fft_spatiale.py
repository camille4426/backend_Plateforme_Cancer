import numpy as np
import base64
from src.Modele.irm import IRM
from src.Modele.mrsi import MRSI
from src.logger import get_logger

logger = get_logger(__name__)

class TRAITEMENT_FFT_SPATIALE:
    """
    Post Traitement Test : Transformée de Fourier
    Applicable sur IRM et MRSI
    """

    def __init__(self, instance):
        self.instance = instance
        if hasattr(self.instance, "data") and self.instance.data is None:
            self.instance.load()

    @staticmethod #Permet l'appel sans instance créée (car pas besoin de self)
    def get_catalog_entry():
        """
        Retourne la description JSON de ce traitement pour le front.
        """
        return {
            "label": "FFT Spatiale",
            "type": ["IRM", "MRSI"],
            "params": {
                "filtre": {
                    "type_param": "choix",
                    "label": "Filtre",
                    "select": ["Passe-haut", "Passe-bas"],
                    "default": "Passe-haut"
                },
                "sigma": {
                    "type": "int",
                    "label": "Largeur gaussienne (sigma)",
                    "range": [1,100],
                    "default": 20
                }
            }
        }

    def run(self, sigma: int = 20, filtre: str = "Passe-haut"):
        """
        Retourne le résultat FFT selon le type de données.
        sigma : largeur de la gaussienne pour filtrage
        filtre : True → passe-haut, False → passe-bas
        """
        if filtre == "Passe-haut" :
            boo_filtre = True
        elif filtre == "Passe-bas":
            boo_filtre = False
        
        if isinstance(self.instance, IRM):
            logger.debug(f"traitement_fft_spatiale.py : run() : le type est IRM")
            volume = self.instance.data
            X, Y, Z = volume.shape
            
            norm_vol, nom_filtre = self._traitement(volume, sigma, boo_filtre)
            base_name = self._basename_no_ext(self.instance.fichier.filename)
            
            return {
                "type": "IRM",
                "type_traitement" : nom_filtre,
                "nom_fichier": base_name + nom_filtre,
                "shape": [int(X), int(Y), int(Z)],
                "data_b64": base64.b64encode(norm_vol.tobytes()).decode('utf-8')
            }

        elif isinstance(self.instance, MRSI):
            logger.debug(f"traitement_fft_spatiale.py : run() : le type est MRSI")
            
            d = self.instance.data
            if d.ndim == 4:
                volume = np.sum(np.abs(d), axis=-1)
            else:
                volume = d
            
            X, Y, Z = volume.shape
            norm_vol, nom_filtre = self._traitement(volume, sigma, boo_filtre)
            base_name = self._basename_no_ext(self.instance.nom)
            
            return {
                "type": "MRSI",
                "type_traitement" : nom_filtre,
                "nom": base_name + nom_filtre,
                "shape": [int(X), int(Y), int(Z)],
                "data_b64": base64.b64encode(norm_vol.tobytes()).decode('utf-8'),
                "method": f"fft_spatiale_{nom_filtre}"
            }

        else:
            return {"error": "Type de donnée inconnu pour FFT (ne traite que les IRM et MRSI)"}
        
    
    def _traitement(self, volume: np.ndarray, sigma: int, filtre: bool):
        """
        FFT 3D + filtrage gaussien.
        """
        # FFT 3D et centrage
        fft_vol = np.fft.fftn(volume)
        fft_shifted = np.fft.fftshift(fft_vol)

        X, Y, Z = volume.shape
        cx, cy, cz = X // 2, Y // 2, Z // 2

        # Coordonnées pour construire le masque gaussien
        x = np.arange(X)[:, None, None]
        y = np.arange(Y)[None, :, None]
        z = np.arange(Z)[None, None, :]

        dist = np.sqrt((x - cx)**2 + (y - cy)**2 + (z - cz)**2)

        # Masque passe-bas gaussien
        mask = np.exp(-dist**2 / (2 * sigma**2))
        nom_filtre = "_lowFFT"

        if filtre: 
            mask = 1 - mask
            nom_filtre = "_highFFT"

        fft_filtered = fft_shifted * mask

        # Retour dans l'espace réel
        vol_filtered = np.fft.ifftn(np.fft.ifftshift(fft_filtered)).real

        # Normalisation pour affichage [0-255]
        vmin, vmax = np.nanmin(vol_filtered), np.nanmax(vol_filtered)
        if vmin == vmax:
            norm_vol = np.zeros_like(vol_filtered, dtype=np.uint8)
        else:
            norm_vol = ((vol_filtered - vmin) / (vmax - vmin) * 255).astype(np.uint8)

        return norm_vol, nom_filtre
    
    def _basename_no_ext(self, filename: str) -> str:
        if filename.endswith(".nii.gz"):
            return filename[:-7]
        elif filename.endswith(".nii"):
            return filename[:-4]
        else:
            return filename
