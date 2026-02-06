# src/controller.py
from fastapi import File
from fastapi import UploadFile

from src.logger import get_logger
from src.Modele.irm import IRM
from src.Modele.mrsi import MRSI
from src.Modele.Traitement.traitement_fft import TRAITEMENT_FFT
from src.Modele.Traitement.metabolite_extractor import METABOLITE_EXTRACTOR


from src.Patients.patient import organize_files_by_patient

logger = get_logger(__name__)  # logger spécifique au module controller.py

class Controller:
    def __init__(self, frontend_url: str, app):
        self.frontend_url = frontend_url
        self.app = app
        logger.info("controller.py : Controleur initialisé")
        
        self.last_irm = {} 
        self.last_mrsi = {}
        # = Dictionnaires de toutes les irms et mrsi utilisées pendant la session courante 
        # clé = nom du fichier, valeur = classe IRM ou MRSI correspondante
        
        

    # -----------------------------------------

    # -----------------------------------------
    #   Méthodes pour organisation fichiers par patient
    # -----------------------------------------
    def get_json_by_patient(self, json_data: dict):
        """
        Reçoit le JSON du front et renvoie le JSON ordonné par patient et par date.
        """
        logger.info("controller.py : Traitement JSON dataset patients")
        try:
            output_json = organize_files_by_patient(json_data)
            logger.info("controller.py : JSON dataset patients traité avec succès")
            return output_json
        except Exception as e:
            logger.error(f"controller.py : Erreur traitement JSON - {e}")
            raise e

    # -----------------------------------------
    #   Méthodes pour upload les fichiers (traitement données IRM / MRSI)
    # -----------------------------------------

    def upload_irm(self, fichier: UploadFile):
        logger.debug(f"controller.py (upload_irm) : Démarrage du traitement IRM - fichier '{fichier.filename}'")
        self.last_irm[fichier.filename] = IRM(fichier)
        
        # load() est appelé automatiquement par get_all_slices si data est None
        payload = self.last_irm[fichier.filename].get_all_slices()

        logger.info("controller.py (upload_irm) : Traitement IRM terminé")
        return payload


    def upload_mrsi(self, fichier: UploadFile):
        logger.debug("controller.py : Démarrage traitement MRSI")
        self.last_mrsi[fichier.filename] = MRSI(fichier.filename, fichier)
        # On renvoie toutes les coupes pour la navigation 3D
        payload = self.last_mrsi[fichier.filename].get_all_voxel_maps()
        logger.info("controller.py : Traitement MRSI terminé")
        return payload


    def get_mrsi_spectrum(self, x: int, y: int, z: int):
        logger.debug("controller.py : Démarrage traitement MRSI spectre")
        if self.last_mrsi is None:
            return {"error": "Aucune MRSI uploadée. Uploadez d'abord /upload-mrsi/."}
        return self.last_mrsi.spectrum(x, y, z)
    
    # -----------------------------------------
    #   Méthodes pour le post-traitement
    # -----------------------------------------
    def upload_traitements(self, catalog: dict):
        """
        catalog : dictionnaire
        {
            "MsrGB01_PUI_20110324_0000.nii.gz": {
                "type_traitement": "fft",
                "params": {"sigma": 20, "filtre": True}
            },
            "MsrGB01_PUI_20110324_0000.nii.gz": {
                "type_traitement": "metabolite_extractor",
                "params": {"metabolites": ["NAA","Cr"]}
            }
        }

        type_traitement actuellement disponibles (les valeurs des params sont celles par défaut si paramètre non fourni) :
            fft | params : sigma: int = 20, filtre: bool = True
            metabolite_extractor | params : 
        """
        logger.debug(f"controller.py : upload_traitements, fichiers irm dispos : '{self.last_irm}'")
        logger.debug(f"controller.py : upload_traitements, fichiers mrsi dispos : '{self.last_mrsi}'")

        TRAITEMENT_MAP = {
            "fft": TRAITEMENT_FFT,
            "metabolite_extractor": METABOLITE_EXTRACTOR
        }

        result = {}

        for name, contenu in catalog.items():
            instance = None
            instance = self.last_irm.get(name) or self.last_mrsi.get(name) #l'instance du fichier concerné
            
            if instance is None:
                result[name] = {"error": "IRM/MRSI non trouvée. Vous essayez de faire un traitement sur un fichier jamais upload"}
                continue
            
            type_traitement = contenu.get("type_traitement")
            if not type_traitement:
                result[name] = {"error": "type_traitement manquant"}
                continue

            classe = TRAITEMENT_MAP.get(type_traitement)
            if classe is None:
                result[name] = {"error": f"Type de traitement inconnu : {type_traitement}"}
                continue

            params = contenu.get("params", {})

            traitement = classe(instance)
            result[name] = traitement.run(**params)                   

        logger.info("controller.py : upload_traitements : traitement terminé")
        return result
