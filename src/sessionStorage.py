
class SESSIONSTORAGE:
    """
    Stockage temporaire en RAM des IRM/MRSI et de leurs traitements.
    Vie uniquement pendant la session backend (aucune sauvegarde disque).
    Data :
      {
         "original_file_name": {
              "original": instance,
              "versions": {
                "fft_spatiale": [
                    {"params": {...}, "data": ...},
                    {"params": {...}, "data": ...}
                ],
                "metabolite_extractor": [
                    {"params": {...}, "data": ...},
                    {"params": {...}, "data": ...}
                ],
            }
         }
     }
    """

    def __init__(self):
        self._data = {}

    # ===============================
    # Ajout
    # ===============================

    def add_original(self, name: str, instance):
        """Ajoute une donnée originale IRM/MRSI si non présente."""
        if name not in self._data :
            self._data[name] = {
                "original": instance,
                "versions": {}
            }

    def add_traitement(self, original_name: str, traitement_type: str, traitement_res : dict):
        """Ajoute un résultat de traitement.
        traitement_res = {"params": {...}, "data": ...}
        => Permet de garder plusieurs même type de traitement si params différents.
        """
        if original_name not in self._data:
            raise KeyError(f"{original_name} non présent dans le stockage session")
        
        if traitement_type not in self._data[original_name]["versions"]:
            self._data[original_name]["versions"][traitement_type] = [] #on crée le type de traitement s'il est absent

        existing = self._data[original_name]["versions"][traitement_type]
        if not any(e["params"] == traitement_res["params"] for e in existing): # Vérification si ce traitement avec ces params existe déjà
            existing.append(traitement_res) #ajout

    # ===============================
    # Récupération
    # ===============================

    # Récupération des instances :

    def get_original(self, original_name: str):
        """Retourne l'instance IRM/MRSI originale"""
        return self._data.get(original_name, {}).get("original")

    def get_traitement(self, original_name: str, traitement_type: str, params : dict = None):
        """Retourne le traitement choisi (résultat comme data affichable par le front directement)"""
        traitements = self._data.get(original_name, {}).get("versions", {}).get(traitement_type, [])

        if not traitements:
            return {"error": f"type_traitement non trouvé : {traitement_type}"}
        
        # Cherche un traitement correspondant exactement aux params
        match = next((t for t in traitements if t["params"] == params), None)
        if not match:
            return {"error": f"aucune correspondance avec ce type de traitement et ces paramètres : {traitement_type} : {params}"}
        else:
            return match["data"]

    def get_all_traitements(self, original_name: str):
        """Retourne tous les traitements faits sur un IRM/MRSI choisi"""
        return dict(self._data.get(original_name, {}).get("versions", {}))
    
    def get_latest_traitement(self, original_name: str, traitement_type_name: str):
        """Retourne le dernier traitement de ce type fait"""
        traitements = self._data.get(original_name, {}).get("versions", {}).get(traitement_type_name, [])
        return traitements[-1] if traitements else None


    # Récupération des noms

    def get_all_original_names(self):
        """Retourne les noms de tous les IRM/MRSI qui ont été upload"""
        return list(self._data.keys())
    
    def get_all_traitement_names(self, original_name: str):
        """Retourne les noms de tous les types de traitements faits sur un IRM/MRSI choisi"""
        return list(self._data.get(original_name, {}).get("versions", {}).keys())

    # Vérification si un upload a été fait

    def original_exists(self, original_name: str):
        """Retourne True si l'upload de l'IRM/MRSI a été fait"""
        return original_name in self._data
    
    def traitement_exists(self, original_name: str, traitement_type_name : str):
        """Retourne True si le traitement choisi pour ce IRM/MRSI a été fait"""
        return traitement_type_name in self._data.get(original_name, {}).get("versions", {})

    # ===============================
    # Suppression
    # ===============================

    def remove(self, original_name: str):
        """Supprime un IRM/MRSI avec tous ses traitements"""
        self._data.pop(original_name, None)

    def clear(self):
        """Réinitialisation de la mémoire"""
        self._data.clear()

    # ===============================
    # Debug / utilitaire
    # ===============================

    def info(self):
        """Résumé lisible pour debug."""
        summary = {}
        for k, v in self._data.items():
            summary[k] = {
                "has_original": v["original"] is not None,
                "versions": {t: len(l) for t, l in v["versions"].items()}
            }
        return summary

"""
A faire pour utiliser la classe :

storage = SessionStorage()

storage.add_original(name, irm_obj)
storage.add_result(name, "fft_spatiale", fft_obj)

obj = storage.get_result(name, "fft_spatiale")



"""