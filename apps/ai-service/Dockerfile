# 1. Utiliser une version légère de Python
FROM python:3.11-slim

# 2. Définir le répertoire de travail
WORKDIR /app

# 3. Copier le fichier des dépendances en premier (pour le cache)
COPY requirements.txt .

# 4. Installer les bibliothèques
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copier tout le projet (scripts, modèles, API)
COPY . .

# 6. On expose le port 5000 pour Flask
EXPOSE 5000

# 7. Au démarrage : import des données puis lancement de l'API (voir entrypoint.sh).
#    On passe par "sh" pour ne pas dépendre du bit exécutable (perdu sous Windows).
CMD ["sh", "entrypoint.sh"]