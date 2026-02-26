# A faire à l'intallation du projet :

Création environnement virtuel à la source backend\ : 
```bash
python -m venv venv
venv\Scripts\activate
cd ./src
pip install -r requirements.txt
```

# Lancement de l'application :
Dans backend/ :
```bash
venv\Scripts\activate
uvicorn src.main:controller.app --reload
```

=> Note : Une fois le serveur lancé, les logs s'actualisent automatiquement à chaque Ctrl + S

Une fois le serveur lancé, on peut trouver l'interface fastAPI à l'adresse :
 http://127.0.0.1:8000/docs#/

 # Requirements: après l'ajout de la quantification (depend de fsl qui ne supporte pas les nouvelles versions de ceratines librairies )

 ``fastapi==0.110.0
uvicorn==0.29.0
python-multipart==0.0.9
passlib[bcrypt]==1.7.4
bcrypt==4.0.1
python-jose[cryptography]==3.3.0
requests==2.31.0
colorlog
click==8.1.7``
