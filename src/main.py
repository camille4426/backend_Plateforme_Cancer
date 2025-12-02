from fastapi import FastAPI
import uvicorn

from src.controller import Controller

FRONTEND_URL = "http://localhost:3000"  # URL frontend

app = FastAPI()
controller = Controller(FRONTEND_URL, app) #Creation du controleur à partir de l'adresse du front

if __name__ == "__main__":
    # Lance FastAPI via Uvicorn : crée une instance FastAPI controller.app, unicorn lance un serveur HTTP 127.0.0.1
    uvicorn.run(controller.app, host="127.0.0.1", port=8000, reload=True)
