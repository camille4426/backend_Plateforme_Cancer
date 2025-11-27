from fastapi import FastAPI
import requests

from Modele.DonneesType.irm import IRM
from Modele.DonneesType.mrsi import MRSI
from Modele.DonneesType.pds import PDS


class Controller:
    """
        Contrôleur principal : interface entre frontEnd et Modèle.
    """
    def __init__(self, frontend_url: str):
            self.frontend_url = frontend_url
            self.setup_routes() #initialisation chemins avec front

    # ROUTES VERS LE FRONT
    def _setup_routes(self):
        # Route racine
        @self.app.get("/")
        def root():
            return {"message": "Backend FastAPI opérationnel via Controller !"}

        # Route pour IRM
        @self.app.post("/upload-irm/{nom}")
        def upload_irm(nom: str, fichier: str):
            return self.upload_irm(nom, fichier)

    # -----------------------------------------

    # -----------------------------------------
    #   Méthodes pour modele
    # -----------------------------------------


    @self.app.post("/upload-irm/{nom}")
    def upload_irm(self, nom: str, fichier: str):
        irm = IRM(nom, fichier)
        irm.charger()
        return irm.affichage_front()
        #return irm.summary()

