import numpy as np
import copy
from src.Modele.mrsi import MRSI
from src.logger import get_logger

logger = get_logger(__name__)

class TRAITEMENT_FFT_SPECTRALE:
    """
    Transformée de Fourier SPECTRALE pour MRSI.
    Transforme en spectres fréquentiels (ppm) -> indispensable pour traitement après.

    La FFT ne peut être appliquée qu'une seule fois, après ça ça bloque le run
    Note : une copie de l'instance originelle MRSI est créée
    """

    def __init__(self, instance: MRSI):
        if not isinstance(instance, MRSI):
            raise ValueError("TRAITEMENT_FFT_SPECTRAL ne s'applique que sur MRSI")

        # Crée une copie indépendante pour ne pas toucher à l'original
        self.mrsi_copy = copy.deepcopy(instance)
        self.mrsi_copy.nom = f"{self.mrsi_copy.nom}_fft_spectral"
        self.mrsi_copy.fichier = None  # inutile sur la copie, à voir si on en a besoin

        if self.mrsi_copy.data is None:
            self.mrsi_copy.load()

        # Indicateur local : FFT déjà appliquée sur cette copie
        self._fft_done = False

    def run(self):
        """
        Applique la FFT spectrale si et seulement si elle n'a pas déjà été appliquée.
        (renvoie comme un get_all_voxel_maps de MRSI, pour)
        """
        logger.info("Application FFT spectrale sur MRSI...")

        # Sécurité : empêcher double FFT
        if self._fft_done:
            logger.warning("FFT spectrale déjà appliquée — traitement ignoré")
            return { "error": "FFT spectrale déjà appliquée sur cette MRSI",}

        d = self.mrsi_copy.data  # shape (X,Y,Z,T)

        if d.ndim != 4:
            return {"error": "MRSI data invalide (doit être 4D X,Y,Z,T)"}

        X, Y, Z, T = d.shape

        # FFT spectrale sur l'axe T
        spectrum = np.fft.fft(d, axis=-1)
        spectrum = np.fft.fftshift(spectrum, axes=-1)

        # Mise à jour des données dans l'instance MRSI
        self.mrsi_copy.data = spectrum
        self._fft_done = True

        # On rajoute dans l'instance
        self.mrsi_copy.spectral_axis = {
            "T": T,
            "fft_shifted": True
        }

        logger.info("FFT spectrale terminée avec succès")

        return self.mrsi_copy.get_all_voxel_maps()
