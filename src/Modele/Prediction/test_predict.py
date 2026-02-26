from src.Modele.mrsi import MRSI
from src.Modele.irm import IRM
from src.logger import get_logger

logger = get_logger(__name__)

class TEST_PREDICT:
    """
    Test de prediction à partir d'un exam complet donné (IRM + MRSI)
    """
    def __init__(self, noms_fichiers: list):
        self.noms_fichiers = noms_fichiers

    def run(self):
        return "TEST_PREDICT pas encore fait, mais si ça retourne ce message -> la structure fonctionne"