# src/controller.py
from fastapi import File
from fastapi import UploadFile

from src.logger import get_logger
from src.Modele.irm import IRM
from src.Modele.mrsi import MRSI
from src.Modele.Traitement.traitement_fft_spatiale import TRAITEMENT_FFT_SPATIALE
from src.Modele.Traitement.traitement_fft_spectrale import TRAITEMENT_FFT_SPECTRALE
from src.Modele.Traitement.metabolite_extractor import METABOLITE_EXTRACTOR


from src.Patients.patient import organize_files_by_patient

logger = get_logger(__name__)  # logger spécifique au module controller.py

class Controller:
    def __init__(self, frontend_url: str, app):
        self.frontend_url = frontend_url
        self.app = app
        logger.info("controller.py : Controleur initialisé")
        
        self.previous_irm = {} 
        self.previous_mrsi = {}
        self.last_irm = None
        self.last_mrsi = None
        # = Dictionnaires de toutes les irms et mrsi utilisées pendant la session courante 
        # clé = nom du fichier, valeur = classe IRM ou MRSI correspondante
        
        

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

    def upload_irm(self, fichier: UploadFile):
        logger.debug(f"controller.py (upload_irm) : Démarrage du traitement IRM - fichier '{fichier.filename}'")
        self.previous_irm[fichier.filename] = IRM(fichier)
        self.last_irm = self.previous_irm[fichier.filename]
        
        # load() est appelé automatiquement par get_all_slices si data est None
        payload = self.previous_irm[fichier.filename].get_all_slices()

        logger.info("controller.py (upload_irm) : Traitement IRM terminé")
        return payload


    def upload_mrsi(self, fichier: UploadFile):
        logger.debug("controller.py : Démarrage traitement MRSI")
        self.previous_mrsi[fichier.filename] = MRSI(fichier.filename, fichier)
        self.last_mrsi = self.previous_mrsi[fichier.filename]
        # On renvoie toutes les coupes pour la navigation 3D
        payload = self.previous_mrsi[fichier.filename].get_all_voxel_maps()
        logger.info("controller.py : Traitement MRSI terminé")
        return payload


    def get_mrsi_spectrum(self, x: int, y: int, z: int):
        logger.debug("controller.py : Démarrage traitement MRSI spectre")
        if not self.last_mrsi:
            return {"error": "Aucune MRSI uploadée. Uploadez d'abord /upload-mrsi/."}
        
        
        #filename = list(self.last_mrsi.keys())[-1]

        return self.last_mrsi.spectrum(x, y, z)

    
    # -----------------------------------------
    #   Méthodes pour le post-traitement
    # -----------------------------------------
    def upload_traitements(self, catalog: dict):
        """
        catalog : dictionnaire
        {
            "MsrGB01_PUI_20110324_0000.nii.gz": {
                "type_traitement": "fft_spatiale",
                "params": {"sigma": 20, "filtre": True}
            },
            "MsrGB01_PUI_20110324_0000.nii.gz": {
                "type_traitement": "metabolite_extractor",
                "params": {"metabolites": ["NAA","Cr"]}
            }
        }

        type_traitement actuellement disponibles (valeurs par défaut | valeurs possibles) :
            fft_spatiale : 
                    sigma: int = 20 | largeur de la gaussienne pour filtrage
                    filtre: bool = True | True → passe-haut, False → passe-bas
            fft_spectrale :
            metabolite_extractor : 

        Note : tous les traitements fonctionnement sans les params donnés, avec des valeurs par défaut pour tous les paramètres manquants
        """
        logger.debug(f"controller.py : upload_traitements, fichiers irm dispos : '{self.previous_irm}'")
        logger.debug(f"controller.py : upload_traitements, fichiers mrsi dispos : '{self.previous_mrsi}'")

        TRAITEMENT_MAP = {
            "fft_spatiale": TRAITEMENT_FFT_SPATIALE,
            "fft_spectrale": TRAITEMENT_FFT_SPECTRALE,
            "metabolite_extractor": METABOLITE_EXTRACTOR
        }

        result = {}

        for name, contenu in catalog.items():
            instance = None
            instance = self.previous_irm.get(name) or self.previous_mrsi.get(name) #l'instance du fichier concerné
            
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

            # Compatibilité type des données (pas d'IRM dans le metabolite extractor)
            if type_traitement == ("fft_spectrale" or "metabolite_extractor") and isinstance(instance, IRM):
                result[name] = {"error": f"Type de traitement non compatible : {type_traitement} se fait uniquement sur MRSI"}
                continue

            params = contenu.get("params", {})

            traitement = classe(instance) #traitement est de la classe associée dans TRAITEMENT_MAP

            result[name] = traitement.run(**params) #Exécution du traitement                  

        logger.info("controller.py : upload_traitements : traitement terminé")
        return result