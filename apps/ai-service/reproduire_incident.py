"""Reproduction de l'incident « modèle manquant » (branche incident/modele-manquant).

Ce script simule l'absence des fichiers modèle au démarrage, sans toucher aux
vrais fichiers, et montre que l'API répond alors 500 (plantage) sur cette branche
vulnérable. Sur la branche corrigée (feat/e5-monitorage), la même situation
renvoie proprement 503.

Lancer depuis apps/ai-service :  python reproduire_incident.py
"""
import os

# On force os.path.exists à répondre « non » pour les fichiers .pkl, ce qui
# simule un modèle absent au moment du chargement de l'API.
_exists_original = os.path.exists
os.path.exists = lambda p: False if p.endswith(".pkl") else _exists_original(p)

import main  # noqa: E402  (import volontairement après le monkeypatch)

os.path.exists = _exists_original
main.app.testing = False

client = main.app.test_client()
reponse = client.get("/predict?nom=Clemenceau")
print(f"/predict sans modele -> statut HTTP {reponse.status_code}")
print("Attendu sur cette branche vulnerable : 500 (plantage).")
