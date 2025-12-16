# src/logger.py
import logging
import colorlog #pour colorer nos logs sinon on voit rien

# -----------------------------------------
# Configuration des logs, centralisé
# -----------------------------------------
#Important : la configuration des logs se fait avant l'initialisation FastAPI
def get_logger(name: str):
    handler = colorlog.StreamHandler()
    formatter = colorlog.ColoredFormatter(
        "[\033[35mLog projet\033[0m] %(log_color)s[%(levelname)s]%(reset)s %(asctime)s: %(message)s",
        log_colors={
            'DEBUG': 'blue',
            'INFO': 'blue',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red'
        },
        style='%'
    )
    handler.setFormatter(formatter)

    logger = colorlog.getLogger(name) # Pour ajout de nos propres logs
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    #logger.setLevel(logging.DEBUG) #Utiliser cette ligne à la place de celle au dessus pour voir les debugs aussi.
    logger.propagate = False  # <-- important pour éviter l'affichage Message: ... Arguments: ()

    # On récupère les logs donnés par uvicorn:
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)

    return logger