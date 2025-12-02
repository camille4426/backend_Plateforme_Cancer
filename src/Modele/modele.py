
class Modele:
    """
    Classe de base du Modèle
    """
    # Initialisation de la classe
    def __init__(self, nom: str):
        self.nom = nom

    # Retourne les informations de la classe
    def summary(self):
        return {"type": "Modele générique", "nom": self.nom}

