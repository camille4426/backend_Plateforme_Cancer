import numpy as np
import base64
from src.Modele.mrsi import MRSI
from src.logger import get_logger

logger = get_logger(__name__)

class TRAITEMENT_FFT_SPECTRALE:
    """
    Transformée de Fourier SPECTRALE pour MRSI.
    Transforme en spectres fréquentiels (ppm).
    """

    def __init__(self, instance: MRSI):
        if not isinstance(instance, MRSI):
            raise ValueError("TRAITEMENT_FFT_SPECTRAL ne s'applique que sur MRSI")

        self.instance = instance
        if self.instance.data is None:
            self.instance.load()

    def run(self):
        """
        Applique la FFT spectrale et renvoie la nouvelle voxel map.
        """
        logger.info("Application FFT spectrale sur MRSI...")

        d = self.instance.data  # shape (X,Y,Z,T)

        if d.ndim != 4:
            return {"error": "MRSI data invalide (doit être 4D X,Y,Z,T)"}

        # FFT spectrale sur l'axe T
        # On ne modifie pas l'original, on calcule juste la nouvelle voxel map
        spectrum = np.fft.fft(d, axis=-1)
        spectrum = np.fft.fftshift(spectrum, axes=-1)

        # Nouvelle voxel map à partir du spectre (somme des amplitudes)
        vm = np.sum(np.abs(spectrum), axis=-1)
        X, Y, Z = vm.shape

        logger.info("FFT spectrale terminée avec succès")

        return {
            "type": "MRSI",
            "nom": f"{self.instance.nom}_fft_spectral",
            "data_b64": base64.b64encode(vm.astype(np.uint8).tobytes()).decode('utf-8'),
            "shape": [int(X), int(Y), int(Z)],
            "method": "fft_spectral",
            "affine": [ [float(v) for v in row] for row in self.instance.img.affine ] if self.instance.img is not None else None,
            "spacing": [float(x) for x in self.instance.img.header.get_zooms()[:3]] if self.instance.img is not None else None
        }
