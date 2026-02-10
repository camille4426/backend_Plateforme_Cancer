# src/main.py
from fastapi import FastAPI, UploadFile, File, Response, Depends, HTTPException, status, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

from src.controller import Controller
from src.database import init_db, get_db_connection
from src.auth import (
    Token, User, get_current_user, 
    ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token, get_password_hash
)
import src.auth as auth

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
        return controller.upload_mrsi(fichier)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

@app.get("/spectrum/{x}/{y}/{z}")
async def get_spectrum(
    x: int, y: int, z: int, 
    current_user: User = Depends(get_current_user)
):
    return controller.get_mrsi_spectrum(x, y, z)

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