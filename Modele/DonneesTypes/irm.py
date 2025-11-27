from ..modele import Modele
import nibabel as nib
import numpy as np

"""
    Classe pour les fichiers IRM
"""
class IRM(Modele):
    # Initialisation de la classe
    def __init__(self, nom: str, fichier_path: str):
        super().__init__(nom)
        self.fichier_path = fichier_path

    #def affichage_front(self):
        # 

    # Retourne les informations de la classe
    def summary(self):
        shape = self.data.shape if self.data is not None else None
        return {"type": "IRM", "nom": self.nom, "shape": shape}
