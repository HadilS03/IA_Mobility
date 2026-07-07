"""Collecte de l'état des parkings depuis l'Open Data de Bordeaux Métropole.

Deux modes d'exécution :
  - une seule capture (défaut) : pratique pour un test ou une tâche cron externe ;
  - en boucle (--loop) : capture répétée à intervalle régulier pour constituer
    l'historique décrit dans le rapport E1.

Chaque exécution est journalisée (horodatage + résultat) afin de garder une trace
des collectes, comme demandé pour rendre la collecte planifiable et traçable.
"""
import argparse
import json
import logging
import os
import time

import requests

# La clé vient d'une variable d'environnement (voir .env.example) : on ne veut
# plus la voir en dur dans le code. Une valeur par défaut garde la démo simple.
CLE = os.getenv("BORDEAUX_API_KEY", "UFM1S7RTLN")
URL = f"https://data.bordeaux-metropole.fr/geojson?key={CLE}&typename=st_park_p"
FICHIER_DEST = os.path.join("data", "raw", "historique_parkings.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("collector")


def collecter():
    """Effectue une capture et l'ajoute au fichier d'historique.

    On n'écrit rien si l'API ne répond pas 200 : mieux vaut une capture
    manquante qu'une donnée corrompue dans l'historique.
    """
    try:
        response = requests.get(URL, timeout=15)
        if response.status_code != 200:
            logger.error("API a répondu %s, capture ignorée.", response.status_code)
            return

        data = response.json()
        features = data.get("features", [])
        capture = {
            "sauvegarde_le": time.strftime("%Y-%m-%d %H:%M:%S"),
            "donnees": features,
        }

        os.makedirs(os.path.dirname(FICHIER_DEST), exist_ok=True)
        with open(FICHIER_DEST, "a", encoding="utf-8") as f:
            f.write(json.dumps(capture) + "\n")

        logger.info("Capture enregistrée : %s parkings.", len(features))
    except Exception as e:
        logger.error("Erreur de collecte : %s", e)


def main():
    parser = argparse.ArgumentParser(description="Collecte des parkings Bordeaux Métropole.")
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Collecte en continu au lieu d'une seule capture.",
    )
    parser.add_argument(
        "--intervalle",
        type=int,
        default=120,
        help="Secondes entre deux captures en mode --loop (défaut : 120).",
    )
    args = parser.parse_args()

    if args.loop:
        logger.info("Collecte en boucle toutes les %s secondes (Ctrl+C pour arreter).",
                    args.intervalle)
        try:
            while True:
                collecter()
                time.sleep(args.intervalle)
        except KeyboardInterrupt:
            # Arrêt propre : pas de trace d'erreur quand on stoppe la collecte.
            logger.info("Arret de la collecte demande par l'utilisateur.")
    else:
        collecter()


if __name__ == "__main__":
    main()
