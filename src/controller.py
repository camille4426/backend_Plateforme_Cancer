# src/controller.py
from fastapi import File
from fastapi import UploadFile

from src.logger import get_logger
from src.Modele.irm import IRM
from src.Modele.mrsi import MRSI

logger = get_logger(__name__)  # logger spécifique au module controller.py

class Controller:
    """
        Contrôleur principal : interface entre frontEnd et Modèle.
    """
class Controller:
    def __init__(self, frontend_url: str, app):
        self.frontend_url = frontend_url
        self.app = app
        logger.info("controller.py : Controleur initialisé")
        self._last_mrsi = None 
        self._setup_routes()

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

    def upload_irm(self, fichier: UploadFile):
        logger.debug(f"controller.py (upload_irm) : Démarrage du traitement IRM - fichier '{fichier.filename}'")
        irm = IRM(fichier)

        payload = irm.set_imgs_irm()

        logger.info("controller.py (upload_irm) : Traitement IRM terminé")
        return payload


    def upload_mrsi(self, fichier: UploadFile):
        logger.debug("controller.py : Démarrage traitement MRSI")
        mrsi = MRSI(fichier.filename, fichier)
        voxel_map = mrsi.voxel_map(z=4)   # coupe centrale par défaut
        self._last_mrsi = mrsi
        logger.info("controller.py : Traitement MRSI terminé")
        return voxel_map


    def get_mrsi_spectrum(self, x: int, y: int, z: int):
        if self._last_mrsi is None:
            return {"error": "Aucune MRSI uploadée. Uploadez d'abord /upload-mrsi/."}
        return self._last_mrsi.spectrum(x, y, z)