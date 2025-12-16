from ..modele import Modele
import nibabel as nib
import numpy as np
from fastapi import UploadFile, File


"""
    Classe pour les fichiers IRM
"""
class IRM(Modele):
    # Initialisation de la classe
    def __init__(self, fichier: UploadFile):
        super().__init__(fichier)

    #def affichage_front(self):
        # 

    # Retourne les informations de la classe
    def summary(self):
        return super().summary("IRM")
        
    
