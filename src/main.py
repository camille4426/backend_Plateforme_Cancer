# src/main.py
from fastapi import FastAPI
#import uvicorn

from src.controller import Controller
#from src.logger import get_logger #Décommenter si logs ici

# -----------------------------------------
# Initialisation FastAPI + Controller
# -----------------------------------------
FRONTEND_URL = "http://localhost:3000"  # URL frontend

app = FastAPI()
controller = Controller(FRONTEND_URL, app) #Creation du controleur à partir de l'adresse du front


# -----------------------------------------
# Lancement serveur (ça que si on lance avec python main.py, mais c'est bof)
# -----------------------------------------
#if __name__ == "__main__":
#    logger.info("Lancement du serveur Uvicorn")
    # Lance FastAPI via Uvicorn : crée une instance FastAPI controller.app, unicorn lance un serveur HTTP 127.0.0.1
#    uvicorn.run(controller.app, host="127.0.0.1", port=8000, reload=True)
