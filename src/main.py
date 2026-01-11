# src/main.py
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from src.controller import Controller

# -----------------------------------------
# Initialisation FastAPI + Controller
# -----------------------------------------
FRONTEND_URL = "http://localhost:3000"

app = FastAPI()

# CORS (évite les soucis de requêtes depuis le front React)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

controller = Controller(FRONTEND_URL, app)

# -----------------------------------------
# Routes
# -----------------------------------------
@app.get("/")
def root():
    return {"status": "ok", "message": "API backend Plateforme Cancer running"}

@app.post("/upload-irm/")
async def upload_irm(fichier: UploadFile = File(...)):
    # renvoie les coupes IRM (axial/coronal/sagittal) + shape
    return controller.upload_irm(fichier)

@app.post("/upload-mrsi/")
async def upload_mrsi(fichier: UploadFile = File(...)):
    # renvoie la voxel-map MRSI (ex: coupe z centrale) selon controller.upload_mrsi
    return controller.upload_mrsi(fichier)

# (Optionnel) si tu as ajouté controller.get_mrsi_spectrum(x,y,z)
@app.get("/mrsi-spectrum/")
def mrsi_spectrum(x: int, y: int, z: int):
    return controller.get_mrsi_spectrum(x, y, z)



# -----------------------------------------
# Lancement serveur (ça que si on lance avec python main.py, mais c'est bof)
# -----------------------------------------
#if __name__ == "__main__":
#    logger.info("Lancement du serveur Uvicorn")
    # Lance FastAPI via Uvicorn : crée une instance FastAPI controller.app, unicorn lance un serveur HTTP 127.0.0.1
#    uvicorn.run(controller.app, host="127.0.0.1", port=8000, reload=True)
