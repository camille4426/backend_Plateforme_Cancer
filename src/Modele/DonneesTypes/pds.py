import nibabel as nib
import numpy as np
from src.logger import get_logger

class PDS:
    # Initialisation de la classe
    def __init__(self, nom: str, fichier: UploadFile):
        self.fichier = fichier

    #def affichage_front(self):
        # 

    # Retourne les informations de la classe
    def summary(self):
        #shape = self.data.shape if self.data is not None else None
        return {"type": "PDS", "nom": self.nom, "shape": shape}
