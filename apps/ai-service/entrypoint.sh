#!/bin/sh
# Démarrage du service IA dans le conteneur.
# 1) On importe les données dans PostgreSQL (idempotent : sans effet si déjà fait).
# 2) On lance l'API. L'import n'est pas bloquant : même s'il échoue, l'API démarre
#    (mode dégradé), on préfère un service qui répond à un service qui ne démarre pas.
set -e

echo "[entrypoint] Import des donnees dans PostgreSQL (idempotent)..."
python src/importer.py || echo "[entrypoint] Import ignore (base indisponible ?)."

echo "[entrypoint] Demarrage de l'API Flask..."
exec python main.py
