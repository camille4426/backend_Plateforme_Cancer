
class Modele:
    """
    Classe de base du Modèle
    """
    # Initialisation de la classe
    def __init__(self, nom: str,fichier_path: str):
        self.nom = nom
        self.fichier_path = fichier_path

    # Retourne les informations de la classe
    def summary(self):
        return {"type": "Modele générique", "nom": self.nom, "fichier": self.fichier_path}

