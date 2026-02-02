import numpy as np
from src.Modele.irm import IRM
from src.Modele.mrsi import MRSI


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
            return self._traitement_irm()
        elif self.data_dico["type"] == "MRSI":
            return self._traitement_mrsi()
        else:
            return {"error": "Type de donnée inconnu pour FFT (ne traite que les IRM et MRSI)"}
        
    # -----------------------------
    # Traitement
    # -----------------------------
    def _traitement_irm(self):
        volume = np.array(self.data_dico["data"])  #get_all_slices renvoie des listes, on reconvertie en tableau numpy

        fft_vol = np.fft.fftn(volume) #Transformée de Fourier du volume 3D
        fft_abs = np.abs(np.fft.fftshift(fft_vol)) #Recentre les basses fréquences (apparemment très important pour visualiser correctement le spectre)

        fft_log = np.log1p(fft_abs) 
        # log scaling pour mieux visualiser les détails
        # sans ça le spectre FFT serait presque invisible aux basses fréquences
        
        # Normalisation pour affichage [0-255]
        vmin, vmax = np.nanmin(fft_log), np.nanmax(fft_log)
        if vmin == vmax:
            norm_vol = np.zeros_like(fft_log, dtype=np.uint8)
        else:
            norm_vol = ((fft_log - vmin) / (vmax - vmin) * 255).astype(np.uint8)

        X, Y, Z = norm_vol.shape

        return {
            "type": "IRM",
            "nom_fichier": self.data_dico["nom_fichier"] + "_FFT",
            "shape": [int(X), int(Y), int(Z)],
            "data": norm_vol.tolist()
        }
    
    def _traitement_mrsi(self):
        #MRSI non fait pour le moment
        return None
