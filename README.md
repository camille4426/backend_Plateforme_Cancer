# A faire à l'intallation du projet :

Se mettre dans src et : pip install -r requirements.txt

# Lancement de l'application :
Dans backend/ :
.\venv\Scripts\Activate.ps1
uvicorn src.main.controller.app --reload

=> Note : Une fois le serveur lancé, les logs s'actualisent automatiquement à chaque Ctrl + S

Une fois le serveur lancé, on peut trouver l'interface fastAPI à l'adresse :
 http://127.0.0.1:8000/docs#/
