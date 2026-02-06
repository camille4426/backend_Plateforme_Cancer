import numpy as np
from src.Modele.irm import IRM
from src.Modele.mrsi import MRSI
from src.logger import get_logger

logger = get_logger(__name__)

class TRAITEMENT_FFT:
    """
    Post Traitement Test : Transformée de Fourier
    Applicable sur IRM et MRSI

    IRM : Affiche le spectre des fréquences au lieu des intensités spatiales de l'upload 
            * Hautes fréquences = détails fins et contours
            * Basses fréquences = structures larges/uniformes

    MRSI : Pas encore fait
    """

    def __init__(self, instance):
        self.data_dico = None #get_all_slices si IRM et get_all_voxel_maps si MRSI

        if isinstance(instance, IRM):
            self.data_dico = instance.get_all_slices()
        elif isinstance(instance, MRSI):
            self.data_dico = instance.get_all_voxel_maps()
        else:
            raise ValueError(f"Instance inconnue pour FFT (ne traite que les IRM et MRSI)")

    def run(self, sigma: int = 20, filtre: bool = True):
        """
        Retourne le résultat FFT selon le type de données.
        sigma : largeur de la gaussienne pour filtrage
        filtre : True → passe-haut, False → passe-bas
        """
        if self.data_dico["type"] == "IRM":
            logger.debug(f"traitement_fft.py : get_fft() : le type est IRM")
            
            # Conversion en tableau numpy
            volume = np.array(self.data_dico["data"])
            
            shape, data, nom_filtre = self._traitement(volume, sigma, filtre)
            base_name = self._basename_no_ext(self.data_dico["nom_fichier"])
            return {
            "type": "IRM",
            "type_traitement" : nom_filtre,
            "nom_fichier": base_name + nom_filtre,
            "shape": shape,
            "data": data
            }

        elif self.data_dico["type"] == "MRSI":
            logger.debug(f"traitement_fft.py : get_fft() : le type est MRSI")

            # voxel_map_all est une liste de slices 2D par Z 
            # Il faut reconstituer le volume 3D
            volume = np.array(self.data_dico["voxel_map_all"]) # shape = (Z, X, Y)
            volume = np.transpose(volume, (1, 2, 0))  # Z-axis à la fin pour cohérence
            
            shape, filtered_volume, nom_filtre = self._traitement(volume, sigma, filtre)
            base_name = self._basename_no_ext(self.data_dico["nom"])
            voxel_map_all = []
            for z in range(shape[2]):
                voxel_map_all.append(filtered_volume[:, :, z].tolist())
            return {
            "type": "MRSI",
            "type_traitement" : nom_filtre,
            "nom": base_name + nom_filtre,
            "voxel_map_all": voxel_map_all,
            "shape": shape,
            "method": self.data_dico["method"]
        }

        else:
            return {"error": "Type de donnée inconnu pour FFT (ne traite que les IRM et MRSI)"}
        
    
    def _traitement(self, volume: np.ndarray, sigma: int, filtre: bool):
        """
        FFT 3D de l'IRM 
        + filtre :
            * False: passe-bas pour visualiser les structures principales (résultat = IRM floutée)
            * True: passe-haut pour visualiser les détails (bords, contours).
        sigma : largeur de la gaussienne pour le filtrage basse fréquence (passe-haut = original - low-pass)
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
        mask = np.exp(-dist**2 / (2 * sigma**2)) # Filtre par gaussienne passe_bas
        nom_filtre = "_lowFFT"

        if filtre: #Si c'est un filtre passe haut on fait l'inverse d'un passe-bas
            # Passe-haut = original - basse fréquence
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


        return [int(X), int(Y), int(Z)], norm_vol.tolist(), nom_filtre
    
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