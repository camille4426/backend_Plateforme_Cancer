
from fastapi import UploadFile, File
from src.logger import get_logger

logger = get_logger(__name__)  # logger spécifique au module controller.py

class Modele:
    """
    Classe de base du Modèle
    """
    # Initialisation de la classe
    def __init__(self,fichier: UploadFile):
        self.fichier = fichier #conservation du fichier

    # Retourne les informations de la classe
    def summary(self, type: str):
        logger.info(f"modele.py (summary) : Retourne le sommaire")
        return {"type": type, "nom_fichier": self.fichier.filename}
        #return {"type": type, "nom_fichier": self.fichier.filename, "fichier": self.fichier}
        #return écrit dans code 200 Response body 


