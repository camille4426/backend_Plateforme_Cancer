# src/controller.py
from fastapi import File
from fastapi import UploadFile

from src.logger import get_logger
from src.Modele.irm import IRM
from src.Modele.mrsi import MRSI

logger = get_logger(__name__)  # logger spécifique au module controller.py

class Controller:
    def __init__(self, frontend_url: str, app):
        self.frontend_url = frontend_url
        self.app = app
        logger.info("controller.py : Controleur initialisé")
        self.last_irm = None 
        self.last_mrsi = None

    # -----------------------------------------

    # -----------------------------------------
    #   Méthodes pour modele
    # -----------------------------------------

    def upload_irm(self, fichier: UploadFile):
        logger.debug(f"controller.py (upload_irm) : Démarrage du traitement IRM - fichier '{fichier.filename}'")
        self.last_irm = IRM(fichier)
        # load() est appelé automatiquement par get_all_slices si data est None
        payload = self.last_irm.get_all_slices()
        logger.info("controller.py (upload_irm) : Traitement IRM terminé")
        return payload


    def upload_mrsi(self, fichier: UploadFile):
        logger.debug("controller.py : Démarrage traitement MRSI")
        self.last_mrsi = MRSI(fichier.filename, fichier)
        # On renvoie toutes les coupes pour la navigation 3D
        payload = self.last_mrsi.get_all_voxel_maps()
        logger.info("controller.py : Traitement MRSI terminé")
        return payload


    def get_mrsi_spectrum(self, x: int, y: int, z: int):
        logger.debug("controller.py : Démarrage traitement MRSI spectre")
        if self.last_mrsi is None:
            return {"error": "Aucune MRSI uploadée. Uploadez d'abord /upload-mrsi/."}
        return self.last_mrsi.spectrum(x, y, z)