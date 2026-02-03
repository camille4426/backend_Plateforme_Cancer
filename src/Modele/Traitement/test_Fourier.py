import numpy as np
from src.Modele.irm import IRM
from src.Modele.mrsi import MRSI
from src.logger import get_logger

logger = get_logger(__name__)

class TEST_FOURIER:
    """
    Post Traitement Test : Transformée de Fourier
    Applicable sur IRM et MRSI

    IRM : Affiche le spectre des fréquences au lieu des intensités spatiales de l'upload 
            * Hautes fréquences = détails fins et contours
            * Basses fréquences = structures larges/uniformes

    MRSI : Pas encore fait
    """

    def __init__(self, instance):
        self.instance = instance
        self.data_dico = None #get_all_slices si IRM et spectrum si MRSI

        if isinstance(self.instance, IRM):
            self.data_dico = self.instance.get_all_slices()
        elif isinstance(self.instance, MRSI):
            self.data_dico = self.instance.spectrum()
        else:
            raise ValueError(f"Instance inconnue pour FFT (ne traite que les IRM et MRSI)")

    def get_fft(self):
        """
        Retourne le résultat FFT selon le type de données.
        """
        if self.data_dico["type"] == "IRM":
            logger.debug(f"test_Fourier.py : get_fft() : le type est IRM")
            return self._traitement_irm()
        elif self.data_dico["type"] == "MRSI":
            logger.debug(f"test_Fourier.py : get_fft() : le type est MRSI")
            return self._traitement_mrsi()
        else:
            return {"error": "Type de donnée inconnu pour FFT (ne traite que les IRM et MRSI)"}
        
    def _traitement_irm(self, sigma: int = 20, filtre: bool = True):
        """
        FFT 3D de l'IRM 
        + filtre :
            * False: passe-bas pour visualiser les structures principales (résultat = IRM floutée)
            * True: passe-haut pour visualiser les détails (bords, contours).
        sigma : largeur de la gaussienne pour le filtrage basse fréquence (passe-haut = original - low-pass)
        """
        # Conversion en tableau numpy
        volume = np.array(self.data_dico["data"])

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
        mask = np.exp(-dist**2 / (2 * sigma**2)) # Filtre par gaussienne passe_bas
        nom_filtre = "_lowFFT"

        if filtre: #Si c'est un filtre passe haut on fait l'inverse d'un passe-bas
            # Passe-haut = original - basse fréquence
            mask = 1 - mask
            nom_filtre = "_highFFT"

        fft_filtered = fft_shifted * mask

        # Retour dans l'espace réel
        vol_high = np.fft.ifftn(np.fft.ifftshift(fft_filtered)).real

        # Normalisation pour affichage [0-255]
        vmin, vmax = np.nanmin(vol_high), np.nanmax(vol_high)
        if vmin == vmax:
            norm_vol = np.zeros_like(vol_high, dtype=np.uint8)
        else:
            norm_vol = ((vol_high - vmin) / (vmax - vmin) * 255).astype(np.uint8)

        return {
            "type": "IRM",
            "nom_fichier": self.data_dico["nom_fichier"] + nom_filtre,
            "shape": [int(X), int(Y), int(Z)],
            "data": norm_vol.tolist()
        }


    def _traitement_mrsi(self):
        #MRSI non fait pour le moment
        return None
