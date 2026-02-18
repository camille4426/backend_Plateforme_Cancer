# src/controller.py
from fastapi import File
from fastapi import UploadFile

from src.logger import get_logger
from src.sessionStorage import SESSIONSTORAGE
from src.Modele.irm import IRM
from src.Modele.mrsi import MRSI
from src.Modele.Traitement.traitement_fft_spatiale import TRAITEMENT_FFT_SPATIALE
from src.Modele.Traitement.traitement_fft_spectrale import TRAITEMENT_FFT_SPECTRALE
import numpy as np
import base64

from src.Modele.Traitement.metabolite_extractor import METABOLITE_EXTRACTOR


from src.Patients.patient import organize_files_by_patient

logger = get_logger(__name__)  # logger spécifique au module controller.py

TRAITEMENT_MAP =  { #Liste des traitements disponibles, chaque classe associée doit avoir get_catalog_entry
    "fft_spatiale": TRAITEMENT_FFT_SPATIALE,
    "fft_spectrale": TRAITEMENT_FFT_SPECTRALE,
    "metabolite_extractor": METABOLITE_EXTRACTOR
}


class Controller:
    def __init__(self, frontend_url: str, app):
        self.frontend_url = frontend_url
        self.app = app
        logger.info("controller.py : Controleur initialisé")
        
        self.storage = SESSIONSTORAGE()

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
    #   Upload
    # -----------------------------------------

    def upload_irm(self, fichier: UploadFile):
        logger.debug(f"controller.py (upload_irm) : Démarrage du traitement IRM - fichier '{fichier.filename}'")
        if self.storage.original_exists(fichier.filename) :
            instance = self.storage.get_original(fichier.filename)
        else:
            instance = IRM(fichier)
            self.storage.add_original(fichier.filename, instance)
        
        # load() est appelé automatiquement par get_all_slices si data est None
        payload = instance.get_all_slices()

        logger.info(f"controller.py (upload_irm) : Traitement IRM terminé stockage : {self.storage.info()}")
        return payload

    def upload_mrsi(self, fichier: UploadFile):
        logger.debug("controller.py : Démarrage traitement MRSI")

        if self.storage.original_exists(fichier.filename) :
            instance = self.storage.get_original(fichier.filename)
        else:
            instance = MRSI(fichier.filename, fichier)
            self.storage.add_original(fichier.filename, instance)

        # On renvoie toutes les coupes pour la navigation 3D
        payload = instance.get_all_voxel_maps()
        logger.info(f"controller.py : Traitement MRSI terminé stockage : {self.storage.info()}")
        return payload


    def get_mrsi_spectrum(self, name : str, x: int, y: int, z: int):
        logger.debug("controller.py : Démarrage traitement MRSI spectre")
        if not self.storage.original_exists(name) :
            return {"error": "Aucune MRSI uploadée. Uploadez d'abord /upload-mrsi/."}

        return self.storage.get_original(name).spectrum(x, y, z)
    

    def get_previous(self, catalog : dict):
        """
        catalog : dictionnaire
        {
            "MsrGB01_PUI_20110324_0000.nii.gz": {
                {"type_traitement": "metabolite_extractor", "params": {"metabolites": ["NAA","Cr"]}}
            },
            "MsrGB01_PUI_20110325_0000.nii.gz": []
        }
        Récupère :
        - Si liste vide -> original
        - Sinon retourne le traitement correspondant
        """
        logger.debug(f"controller.py : get_previous, catalogue reçu : '{catalog}'")

        result = {}
        for ori_name, traitements in catalog.items():

            if not self.storage.original_exists(ori_name):
                result[ori_name] = {"error": f"Original inconnu : {ori_name}"}
                continue

            if not traitements: # Si pas de traitement donnés on retourne l'original
                instance_ori = self.storage.get_original(ori_name)

                if isinstance(instance_ori, IRM):
                    result[ori_name] = instance_ori.get_all_slices()
                elif isinstance(instance_ori, MRSI):
                    result[ori_name] = instance_ori.get_all_voxel_maps()
                else:
                    result[ori_name] = {"error": f"L'original n'est pas de type IRM ou MRSI"}
                continue
                
            result[ori_name] = []
            for t in traitements:
                type_traitement = t.get("type_traitement")
                params = t.get("params")

                if type_traitement is None:
                    result[ori_name].append({"error": "type_traitement manquant"})
                    continue

                result[ori_name].append(self.storage.get_traitement(ori_name, type_traitement, params))
        
        return result
    
    # -----------------------------------------
    #   Méthodes pour le post-traitement
    # -----------------------------------------
    @staticmethod
    def get_catalog():
        """
        Permet au front d'obtenir la liste des traitements avec les paramètres demandés pour l'affichage
        """
        logger.debug("controller.py : get_catalog début")
        catalog = {}
        for key, cls in TRAITEMENT_MAP.items():
            entry = getattr(cls, "get_catalog_entry", None)
            if callable(entry):
                catalog[key] = entry()
            else: # si la classe n'a pas de get_catalog_entry()
                catalog[key] = {
                    "label": key,
                    "type": [],  # inconnu
                    "params": {}
                }
        logger.info("controller.py : get_catalog fini")
        return catalog


    def upload_traitements(self, catalog: dict):
        """
        catalog : dictionnaire
        {
            "MsrGB01_PUI_20110324_0000.nii.gz": {
                "type_traitement": "fft_spatiale",
                "params": {"sigma": 20, "filtre": True}
            },
            "MsrGB01_PUI_20110324_0001.nii.gz": {
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

        """
        logger.debug(f"controller.py : upload_traitements, catalogue reçu : '{catalog}'")

        result = {}

        for name, contenu in catalog.items():
            instance = self.storage.get_original(name) # l'instance du fichier concerné
            
            if instance is None:
                result[name] = {"error": "IRM/MRSI non trouvée. Placez vous sur l'original ou la version que vous voulez modifier"}
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
            if type_traitement in ["fft_spectrale", "metabolite_extractor"] and isinstance(instance, IRM):
                result[name] = {"error": f"Type de traitement non compatible : {type_traitement} se fait uniquement sur MRSI"}
                continue

            params = contenu.get("params", {})
            logger.debug(f"controller.py : upload_traitements params envoyés : {params}")
            traitement = classe(instance) #traitement est de la classe associée dans TRAITEMENT_MAP

            try :
                res = traitement.run(**params) #Exécution du traitement
                res_stockage = { 
                    "params" : traitement.params, #bien faire après le run sinon ce sera faux
                    "data" : res 
                }
                self.storage.add_traitement(name, type_traitement, res_stockage)
                result[name] = res
            except Exception as e:
                result[name] = {"error": str(e)}
                logger.info(f"controller.py : upload_traitements : ERREUR : {str(e)}")    

        logger.info(f"controller.py : upload_traitements : traitement terminé stockage : {self.storage.info()}")
        return result


    def get_fusion(self, mri_name: str, mrsi_name: str, force_center: bool = False, mix_method: str = "sum_abs", channel: int = None):
        """
        Génère une carte de chaleur MRSI rééchantillonnée sur la géométrie de l'IRM.
        """
        logger.debug(f"controller.py (get_fusion) : mri={mri_name}, mrsi={mrsi_name}, force={force_center}, channel={channel}")
        
        if not self.storage.original_exists(mri_name):
            return {"error": f"IRM introuvable: {mri_name}"}
        if not self.storage.original_exists(mrsi_name):
            return {"error": f"MRSI introuvable: {mrsi_name}"}
            
        irm_instance = self.storage.get_original(mri_name)
        mrsi_instance = self.storage.get_original(mrsi_name)
        
        if not isinstance(irm_instance, IRM):
            return {"error": f"Le fichier {mri_name} n'est pas une IRM"}
        if not isinstance(mrsi_instance, MRSI):
            return {"error": f"Le fichier {mrsi_name} n'est pas une MRSI"}
            
        # Ensure data is loaded
        if irm_instance.data is None: irm_instance.load()
        if mrsi_instance.data is None: mrsi_instance.load()
        
        # Get MRI geometry
        if irm_instance.img is None:
             return {"error": "IRM image obj None"}
             
        mri_shape = irm_instance.data.shape
        # Handle 4D MRI (take first volume)
        if len(mri_shape) == 4:
            mri_shape = mri_shape[:3]
            
        mri_affine = irm_instance.img.affine
        
        # Perform Resampling
        try:
            resampled_data, transform_matrix = mrsi_instance.resample_to_mri(mri_shape, mri_affine, force_center=force_center, channel=channel)
        except Exception as e:
            logger.error(f"Fusion error: {e}")
            return {"error": str(e)}
            
        # Normalize to uint8 0-255 for transport/display
        vmin, vmax = np.nanmin(resampled_data), np.nanmax(resampled_data)
        if vmin == vmax:
             resampled_norm = np.zeros_like(resampled_data, dtype=np.uint8)
        else:
             resampled_norm = ((resampled_data - vmin) / (vmax - vmin) * 255).astype(np.uint8)
             
        # Encode
        return {
            "type": "FUSION",
            "mri": mri_name,
            "mrsi": mrsi_name,
            "shape": list(mri_shape),
            "data_b64": base64.b64encode(resampled_norm.tobytes()).decode('utf-8'),
            "affine": [ [float(v) for v in row] for row in mri_affine ],
            "info": f"Fused {mrsi_name} onto {mri_name}. ForceCenter={force_center}",
            "transform_matrix": [ [float(v) for v in row] for row in transform_matrix ]
        }