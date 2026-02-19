# src/main.py
from fastapi import FastAPI, UploadFile, File, Response, Depends, HTTPException, status, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

from src.logger import get_logger

from src.controller import Controller
from src.database import init_db, get_db_connection
from src.auth import (
    Token, User, get_current_user, 
    ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token, get_password_hash
)
import src.auth as auth

logger = get_logger(__name__)  # logger spécifique au module controller.py

# -----------------------------------------
# Initialisation FastAPI + Controller
# -----------------------------------------
FRONTEND_URL = "http://localhost:3000"

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL,
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

controller = Controller(FRONTEND_URL, app)

@app.on_event("startup")
def startup_event():
    init_db()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", ("admin",))
    if not cursor.fetchone():

        hashed_pw = get_password_hash("admin")
        cursor.execute("INSERT INTO users (username, hashed_password) VALUES (?, ?)", ("admin", hashed_pw))
        conn.commit()
        print("Default user 'admin' created with password 'admin'")
    conn.close()

# -----------------------------------------
# Auth Routes
# -----------------------------------------


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = auth.get_user(form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# -----------------------------------------
# Upload Routes
# -----------------------------------------
@app.get("/fusion/")
async def get_fusion(mri: str, mrsi: str, force_center: bool = False, channel: int = None):
    return controller.get_fusion(mri, mrsi, force_center, channel=channel)

@app.get("/catalog/")
def catalog_root():
    return {"status": "ok", "message": "API backend Plateforme Cancer running"}

@app.get("/")
def root():
    return {"status": "ok", "message": "API backend Plateforme Cancer running"}

@app.post("/upload-irm/")
async def upload_irm(
    fichier: UploadFile = File(...), 
    current_user: User = Depends(get_current_user)
):
    try:
        return controller.upload_irm(fichier)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

@app.post("/upload-mrsi/")
async def upload_mrsi(
    fichier: UploadFile = File(...), 
    current_user: User = Depends(get_current_user)
):
    try:
        logger.debug("main.py : Démarrage traitement MRSI")
        return controller.upload_mrsi(fichier)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

@app.get("/spectrum/{name}/{x}/{y}/{z}")
async def get_spectrum(
    name : str, x: int, y: int, z: int, 
    current_user: User = Depends(get_current_user)
):
    logger.debug(f"main.py : Démarrage traitement spectrum MRSI name : {name}")
    return controller.get_mrsi_spectrum(name, x, y, z)

@app.post("/upload-json-dataset/")
async def upload_json_dataset(
    json_data: dict = Body(...), 
    current_user: User = Depends(get_current_user)
):
    try:
        return controller.get_json_by_patient(json_data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
    
# -----------------------------------------
# Traitement Routes
# -----------------------------------------
@app.get("/traitements/catalog")
async def traitements_catalog():
    """
    Permet au front d'obtenir la liste des traitements avec les paramètres demandés pour l'affichage
    """
    return controller.get_catalog()


@app.post("/traitements")
async def run_traitements(catalog: dict = Body(...)):
    """
    catalog attendu :
    {
        "MsrGB01_PUI_20110324_0000.nii.gz": {
            "type_traitement": "fft",
            "params": {"sigma": 20, "filtre": True}
        },
        "MsrGB01_PUI_20110324_0001.nii.gz": {
            "type_traitement": "metabolite_extractor",
            "params": {"metabolites": ["NAA","Cr"]}
        }
    }

    type_traitement actuellement disponibles (les valeurs des params sont celles par défaut si paramètre non fourni) :
        fft | params : sigma: int = 20, filtre: bool = True
        metabolite_extractor | params : 

    """
    try:
        return controller.upload_traitements(catalog)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
    
# -----------------------------------------
# Prediction via exams Routes
# -----------------------------------------
@app.post("/predict")
async def get_prediction_from_exam(exams: list = Body(...)):
    """
        entrée attendue : exams : list de dictionnaires
        [
            {
                "type_traitement": "NOM_PREDICTION",
                "fichiers": ["fich1_nom", "fich2_nom", "fich3_nom"]
            },
            {
                "type_traitement": "NOM_PREDICTION",
                "fichiers": ["fich1_nom", "fich2_nom", "fich3_nom"]
            }
        ]

        Retourne dictionnaire pour chaque prédiction demandée :
        {
            "Fichiers_memoire": "manquants",
            "fichiers_manquants": ["fich1_nom", "fich3_nom"]
        }
        ou
        {
            "Fichiers_memoire": "OK",
            "Result": Resultat
        }
       
        """
    try:
        return controller.get_prediction_from_exam(exams)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

# -----------------------------------------
# Storage Routes
# -----------------------------------------
@app.post("/storage/previous")
async def get_previous(catalog: dict = Body(...)):
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
    try:
        return controller.get_previous(catalog)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
    

@app.post("/storage/upload_memoire")
async def upload_memoire(fichiers: list = Body(...)):
    """
        List attendue :
        [
            ["IRM", UploadFile],
            ["IRM", UploadFile],
            ["MRSI", UploadFile]
        ]
        List de list : Chaque fichier en UploadFile avec son type devant
        Retourne "Success" si tous les fichiers fournis ont bien été mis en mémoire
        """
    try:
        return controller.upload_memoire(fichiers)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}