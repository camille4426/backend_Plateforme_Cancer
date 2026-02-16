import re
from collections import defaultdict

from src.logger import get_logger
logger = get_logger(__name__)  # logger spécifique au module controller.py

def organize_files_by_patient(input_json: dict) -> dict:
    """
    Transforme le JSON reçu du front en un JSON ordonné :
    - regroupé par patient
    - chaque patient contient ses analyses par date
    - chaque analyse contient la liste des fichiers correspondants
    """

    files = input_json.get("files", [])
    
    patients_dict = defaultdict(lambda: defaultdict(list))
    fichiers_non_reconnus = []

    regex = r"^(?P<type_analyse>MsrGB(_MRSI)?)_?(?P<id_patient>\d{2}_[A-Z]{3})_(?P<date>\d{8})_?(?P<modalites_IRM>\d{4})?([^\.]*)(?P<extension>.*)"

    for f in files:
        nom_fichier = f["name"]
        
        match = re.search(regex, nom_fichier)
        if not match:
            fichiers_non_reconnus.append(nom_fichier)
            continue
        
        patient_id = match.group("id_patient")
        date = match.group("date")
       
        modalites_IRM = match.group("modalites_IRM")
        #logger.info(f"patient.py : Mod : {modalites_IRM} nom : {nom_fichier}")
        if modalites_IRM == "0000":
            modalites_IRM = "T1"
        elif modalites_IRM == "0001":
            modalites_IRM = "T1C"
        elif modalites_IRM == "0002":
            modalites_IRM = "T2"
        elif modalites_IRM == "0003":
            modalites_IRM = "Flair"
        else:
            modalites_IRM = None

        ext = match.group("extension")
        if ext == ".nii":
            type = "MRSI"
        elif ext == ".nii.gz":
            if modalites_IRM == None:
                logger.info(f"patient.py : Mask trouvé : {match}")
                type = "Mask"
            else:
                #logger.info(f"patient.py : IRM trouvé : {match}")
                type = "IRM"
        else:
            type = "inconnu"
        
        file_info = {
            "relative_path": f["relativePath"],
            "type_analyse": type,
        }

        if modalites_IRM is not None:
            file_info["modalites_IRM"] = modalites_IRM

        # Ajout du fichier dans la structure temporaire
        patients_dict[patient_id][date].append(file_info)


    # Transformation en JSON final
    output_json = {
        "patients": [],
        "fichiers_non_reconnus": fichiers_non_reconnus  # pour informer l'utilisateur
    }

    for patient_id in sorted(patients_dict.keys()):
        patient_data = {
            "patientId": patient_id, 
            "analyses": []
        }

        for date in sorted(patients_dict[patient_id].keys()):
            analysis = {
                #"date": date, 
                "date": f"{date[0:4]}/{date[4:6]}/{date[6:8]}",
                "files": patients_dict[patient_id][date]  # liste de dicts file_info
            }
            patient_data["analyses"].append(analysis)
        
        output_json["patients"].append(patient_data)

    return output_json