import nibabel as nib
import numpy as np
from fastapi import UploadFile, File
from src.logger import get_logger

"""
    Classe pour les fichiers IRM
"""
class IRM:
    # Initialisation de la classe
    def __init__(self, fichier: UploadFile):
        self.fichier = fichier #conservation du fichier

    #def affichage_front(self):
        # 

    # Retourne les informations de la classe
    def summary(self):
        logger.info(f"modele.py (summary) : Retourne le sommaire")
        return {"type": "IRM", "nom_fichier": self.fichier.filename}
        #return {"type": type, "nom_fichier": self.fichier.filename, "fichier": self.fichier}
        #return écrit dans code 200 Response body 
        
    
