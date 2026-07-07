"""Configuration de la journalisation du service IA.

On produit des logs *structurés* (une ligne = un objet JSON) pour que chaque
événement soit facilement exploitable ensuite : c'est la base du monitorage
(indicateurs de santé, endpoint /metrics de l'épreuve E5).

Les logs partent à la fois vers la console (pratique en développement) et vers
un fichier rotatif (garde une trace sans jamais grossir sans limite).
Aucune donnée personnelle n'est journalisée : on ne manipule que des noms de
parkings publics.
"""
import json
import logging
import os
from logging.handlers import RotatingFileHandler


class FormatteurJson(logging.Formatter):
    """Sérialise chaque enregistrement de log en JSON.

    Les champs métier (endpoint, parking, durée, statut) sont passés via
    l'argument `extra=` des appels au logger et ajoutés ici s'ils sont présents.
    """

    CHAMPS_METIER = ("endpoint", "parking", "duree_ms", "statut")

    def format(self, record):
        entree = {
            "horodatage": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
            "niveau": record.levelname,
            "message": record.getMessage(),
        }
        for champ in self.CHAMPS_METIER:
            if hasattr(record, champ):
                entree[champ] = getattr(record, champ)
        return json.dumps(entree, ensure_ascii=False)


def configurer_logs(log_dir, nom="ia_mobility"):
    """Prépare et renvoie le logger du service.

    Idempotent : si le logger a déjà ses handlers (import multiple, rechargement
    par les tests), on ne les ajoute pas une seconde fois pour éviter les doublons.
    """
    logger = logging.getLogger(nom)
    if logger.handlers:
        return logger

    os.makedirs(log_dir, exist_ok=True)
    logger.setLevel(logging.INFO)
    formatteur = FormatteurJson()

    # Fichier rotatif : 1 Mo par fichier, 3 anciens conservés.
    fichier = RotatingFileHandler(
        os.path.join(log_dir, "api.log"),
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    fichier.setFormatter(formatteur)

    console = logging.StreamHandler()
    console.setFormatter(formatteur)

    logger.addHandler(fichier)
    logger.addHandler(console)
    logger.propagate = False  # évite que Flask ne redouble les lignes
    return logger
