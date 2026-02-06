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
import src.auth as auth  # importing the module to monkeypatch/access helper functions if needed

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
    # Create default user if not exists
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", ("admin",))
    if not cursor.fetchone():
        # Create admin user
        hashed_pw = get_password_hash("admin")
        cursor.execute("INSERT INTO users (username, hashed_password) VALUES (?, ?)", ("admin", hashed_pw))
        conn.commit()
        print("Default user 'admin' created with password 'admin'")
    conn.close()

# -----------------------------------------
# Auth Routes
# -----------------------------------------

# We need to implement authenticate_user in auth.py or here. 
# Let's add it to auth.py via a separate tool call if I missed it, 
# OR implement it here and move it later.
# Actually I missed `authenticate_user` in `auth.py`. I defined `get_user` and `verify_password`.
# I will implement the logic inside the route or add the function to auth.py. 
# Better to add it to auth.py properly, but to save a round trip for now I'll define a helper here 
# or use what I have. I have `get_user` and `verify_password` in auth.py.

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
        result = controller.upload_irm(fichier)
        # Check if result contains an error
        if isinstance(result, dict) and "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement IRM: {str(e)}")

@app.post("/upload-mrsi/")
async def upload_mrsi(
    fichier: UploadFile = File(...), 
    current_user: User = Depends(get_current_user)
):
    try:
        result = controller.upload_mrsi(fichier)
        # Check if result contains an error
        if isinstance(result, dict) and "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement MRSI: {str(e)}")

@app.get("/spectrum/{x}/{y}/{z}")
async def get_spectrum(
    x: int, y: int, z: int, 
    current_user: User = Depends(get_current_user)
):
    result = controller.get_mrsi_spectrum(x, y, z)
    # If result contains an error, raise appropriate HTTP exception
    if isinstance(result, dict) and "error" in result:
        error_msg = result["error"]
        if "hors limites" in error_msg.lower() or "out" in error_msg.lower():
            raise HTTPException(status_code=400, detail=error_msg)
        elif "non trouvée" in error_msg.lower() or "uploadée" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        else:
            raise HTTPException(status_code=500, detail=error_msg)
    return result

@app.post("/upload-json-dataset/")
async def upload_json_dataset(
    json_data: dict = Body(...), 
    current_user: User = Depends(get_current_user)
):
    try:
        result = controller.get_json_by_patient(json_data)
        # Check if result contains an error
        if isinstance(result, dict) and "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement JSON dataset: {str(e)}")

# -----------------------------------------
# Traitement Routes
# -----------------------------------------
@app.post("/traitement/test_fft/")
async def test_fft(filenames: list[str] = Body(...)):
    try:
        result = controller.test_fft(filenames)
        # Check if result contains errors for all files
        if isinstance(result, dict) and all("error" in v for v in result.values()):
            raise HTTPException(status_code=400, detail="Tous les fichiers demandés sont invalides ou non trouvés")
        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement FFT: {str(e)}")