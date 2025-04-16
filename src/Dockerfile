FROM python:3.10

# Eviter les .pyc et activer logs direct
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

#Definir le dossier de travail dans le conteneur 
WORKDIR /app

# Copier les dependances et les installer 
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le code backend
COPY . . 

#Commande de dev django
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# Ouvrir le port 8000
EXPOSE 8000
