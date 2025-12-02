from fastapi import FastAPI
import requests

import Modele
from Modele.DonneesTypes.irm import IRM
from Modele.DonneesTypes.mrsi import MRSI
from Modele.DonneesTypes.pds import PDS


class Controller:
    """
        Contrôleur principal : interface entre frontEnd et Modèle.
    """
    def __init__(self, frontend_url: str, app):
            self.frontend_url = frontend_url
            self.app = app
            self._setup_routes() #initialisation chemins avec front

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


    #@self.app.post("/upload-irm/{nom}")
    def upload_irm(self, nom: str, fichier: str):
        irm = IRM(nom, fichier)
        irm.charger()
        return irm.affichage_front()
        #return irm.summary()

