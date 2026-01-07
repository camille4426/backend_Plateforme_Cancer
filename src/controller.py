# src/controller.py
from fastapi import FastAPI, UploadFile, File
import requests

from src.logger import get_logger
from src.Modele.irm import IRM
from src.Modele.mrsi import MRSI
from src.Modele.pds import PDS

logger = get_logger(__name__)  # logger spécifique au module controller.py

class Controller:
    """
        Contrôleur principal : interface entre frontEnd et Modèle.
    """
    def __init__(self, frontend_url: str, app):
            self.frontend_url = frontend_url
            self.app = app
            logger.info("controller.py : Controleur initialisé")
            self._setup_routes() #initialisation chemins avec front

    # ROUTES VERS LE FRONT
    def _setup_routes(self):
        # Route racine
        @self.app.get("/")
        def root():
            logger.debug("controller.py : Requête Setup route racine reçue")
            return {"message": "Backend FastAPI opérationnel via Controller !"}

        # Route pour IRM
        @self.app.post("/upload-irm/")
        async def upload_irm(fichier: UploadFile = File(...)): #async car l'upload de fichiers induit une attente, donc async pour pas bloquer
            #contenu = await fichier.read() # lecture fichier en bytes
            logger.info(f"controller.py : Requête fichier IRM reçue - fichier '{fichier.filename}'")
            return self.upload_irm(fichier)

    # -----------------------------------------

    # -----------------------------------------
    #   Méthodes pour modele
    # -----------------------------------------


    #@self.app.post("/upload-irm/")
    def upload_irm(self, fichier: UploadFile):
        logger.debug(f"controller.py (upload_irm) : Démarrage du traitement IRM - fichier '{fichier.filename}'")
        irm = IRM(fichier)
        #irm.charger()
        summary = irm.summary()
        logger.info(f"controller.py (upload_irm) : Traitement IRM terminé - Retoune : '{summary}'")
        return summary

