from ..modele import Modele
import nibabel as nib
import numpy as np

"""
    Classe pour les fichiers IRM
"""
class IRM(Modele):
    # Initialisation de la classe
    def __init__(self, nom: str, fichier_path: str):
        super().__init__(nom, fichier_path)

    #def affichage_front(self):
        # 

    # Retourne les informations de la classe
    def summary(self):
        #super().summary()
        #return écrit dans code 200 Response body 
        return {"type": "IRM", "nom": self.nom, "fichier": self.fichier_path}
