# src/controller.py
from fastapi import File
from fastapi import UploadFile

from src.logger import get_logger
from src.Modele.irm import IRM
from src.Modele.mrsi import MRSI
from src.Modele.Traitement.test_Fourier import TEST_FOURIER
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
        if not self.last_mrsi:
            return {"error": "Aucune MRSI uploadée. Uploadez d'abord /upload-mrsi/."}
        try:
            # Get the most recently uploaded MRSI (last item in dict)
            last_mrsi_instance = list(self.last_mrsi.values())[-1]
            return last_mrsi_instance.spectrum(x, y, z)
        except (IndexError, KeyError):
            return {"error": "Aucune MRSI uploadée. Uploadez d'abord /upload-mrsi/."}
    
    # -----------------------------------------
    #   Méthodes pour le post-traitement
    # -----------------------------------------
    def test_fft(self, filenames: list):
        """
        filenames : liste des noms de fichiers IRM ou MRSI à traiter
        """
        logger.debug(f"controller.py : Début Post Traitement test_Fourier, fichiers : '{filenames}'")
        logger.debug(f"controller.py : test_fft, fichiers irm dispos : '{self.last_irm}'")
        logger.debug(f"controller.py : test_fft, fichiers mrsi dispos : '{self.last_mrsi}'")

        result = {}

        for name in filenames:
            instance = None
            instance = self.last_irm.get(name) or self.last_mrsi.get(name) #l'instance du fichier concerné
            
            if instance == None:
                logger.info(f"controller.py : test_fft : fichier non trouvé '{name}'")
                result[name] = {"error": "IRM/MRSI non trouvée. Vous essayez de faire un traitement sur un fichier jamais upload"}
                continue
            
            traitement_fft = TEST_FOURIER(instance)

            result[name] = traitement_fft.get_fft()

        logger.info("controller.py : Post Traitement test_Fourier terminé")
        return result
