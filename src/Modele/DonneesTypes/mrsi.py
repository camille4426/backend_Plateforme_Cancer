from ..modele import Modele
import nibabel as nib
import numpy as np

class MRSI:
    # Initialisation de la classe
    def __init__(self, nom: str, fichier: UploadFile):
        self.fichier = fichier #conservation du fichier

    #def affichage_front(self):
        # 

    # Retourne les informations de la classe
    def summary(self):
        #shape = self.data.shape if self.data is not None else None
        return {"type": "MRSI", "nom": self.nom, "shape": shape}
