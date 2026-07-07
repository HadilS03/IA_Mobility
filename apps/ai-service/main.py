import csv
import io
import os
import time
from datetime import datetime

import joblib
import pandas as pd
import psycopg2
from flask import Flask, Response, g, jsonify, request

from src.db import get_connection
from src.logging_config import configurer_logs

app = Flask(__name__)

# Chemins ancrés sur l'emplacement du fichier : le service fonctionne quel que
# soit le dossier depuis lequel on le lance (démo, tests, Docker).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELE_PATH = os.path.join(BASE_DIR, "models", "modele_parkings.pkl")
ENCODER_PATH = os.path.join(BASE_DIR, "models", "encoder_noms.pkl")
DATASET_PATH = os.path.join(BASE_DIR, "data", "processed", "data_training.csv")
LOG_DIR = os.path.join(BASE_DIR, "logs")

logger = configurer_logs(LOG_DIR)

# Chargement du modèle et de l'encodeur. En cas d'absence, on laisse model/le à
# None : les endpoints répondront proprement (503) plutôt que de planter à l'import.
model = None
le = None
if os.path.exists(MODELE_PATH) and os.path.exists(ENCODER_PATH):
    model = joblib.load(MODELE_PATH)
    le = joblib.load(ENCODER_PATH)
    logger.info("Modele et encodeur charges (%s parkings).", len(le.classes_))
else:
    logger.error("Modeles introuvables : lance predictor.py d'abord.")


# ---------------------------------------------------------------------------
# Journalisation de chaque requête (E3/C11, E5/C20)
# ---------------------------------------------------------------------------
@app.before_request
def _demarrer_chrono():
    # Mémorise l'instant de début pour mesurer la durée de traitement.
    g.debut = time.perf_counter()


@app.after_request
def _journaliser(response):
    duree_ms = None
    if hasattr(g, "debut"):
        duree_ms = round((time.perf_counter() - g.debut) * 1000, 1)
    # On journalise le nom de parking demandé (donnée publique), jamais de
    # donnée personnelle.
    logger.info(
        "requete",
        extra={
            "endpoint": request.path,
            "parking": request.args.get("nom"),
            "duree_ms": duree_ms,
            "statut": response.status_code,
        },
    )
    return response


# ---------------------------------------------------------------------------
# Helpers de validation
# ---------------------------------------------------------------------------
def _entier_optionnel(nom_param, defaut, mini, maxi):
    """Lit un paramètre entier optionnel et le valide dans [mini, maxi].

    Renvoie (valeur, None) si tout va bien, (None, message) en cas d'erreur.
    Permet de rejouer une prédiction à un autre moment (démo), tout en refusant
    une valeur aberrante.
    """
    brut = request.args.get(nom_param)
    if brut is None:
        return defaut, None
    try:
        valeur = int(brut)
    except ValueError:
        return None, f"{nom_param} doit etre un entier."
    if valeur < mini or valeur > maxi:
        return None, f"{nom_param} doit etre entre {mini} et {maxi}."
    return valeur, None


def borner_taux(valeur):
    """Ramène un taux d'occupation dans [0, 100].

    Un modèle de régression peut renvoyer une valeur légèrement hors bornes ;
    or un taux d'occupation n'a de sens qu'entre 0 et 100 %.
    """
    return max(0.0, min(100.0, float(valeur)))


# ---------------------------------------------------------------------------
# Santé du service (E3/C11)
# ---------------------------------------------------------------------------
@app.route('/health', methods=['GET'])
def health():
    """Indique si le service est opérationnel (modèle chargé)."""
    charge = model is not None and le is not None
    corps = {
        "status": "ok" if charge else "degraded",
        "modele_charge": charge,
        "nb_parkings": len(le.classes_) if charge else 0,
    }
    return jsonify(corps), 200 if charge else 503


# ---------------------------------------------------------------------------
# Prédiction d'occupation (E3/C9)
# ---------------------------------------------------------------------------
@app.route('/predict', methods=['GET'])
def predict():
    if model is None or le is None:
        return jsonify({"erreur": "Modele indisponible."}), 503

    nom_parking = request.args.get('nom')
    if not nom_parking:
        return jsonify({"erreur": "Veuillez preciser un nom de parking"}), 400

    # Paramètres temporels optionnels : par défaut « maintenant », mais on peut
    # forcer un moment précis pour reproduire une prédiction (utile en démo).
    maintenant = datetime.now()
    heure, err = _entier_optionnel('heure', maintenant.hour, 0, 23)
    if err:
        return jsonify({"erreur": err}), 400
    jour, err = _entier_optionnel('jour', maintenant.weekday(), 0, 6)
    if err:
        return jsonify({"erreur": err}), 400
    minute, err = _entier_optionnel('minute', maintenant.minute, 0, 59)
    if err:
        return jsonify({"erreur": err}), 400

    # Parking inconnu du modèle -> 404 explicite (et non une erreur générique).
    try:
        nom_encoded = le.transform([nom_parking])[0]
    except ValueError:
        return jsonify({
            "erreur": f"Le parking '{nom_parking}' est inconnu.",
            "liste_disponible": list(le.classes_[:5]) + ["..."],
        }), 404

    try:
        input_data = pd.DataFrame(
            [[nom_encoded, heure, jour, minute]],
            columns=['nom_encoded', 'heure', 'jour_semaine', 'minute'],
        )
        prediction = borner_taux(model.predict(input_data)[0])
        return jsonify({
            "parking": nom_parking,
            "prediction_occupation": f"{round(prediction, 2)}%",
            "heure_analyse": f"{heure}h{minute:02d}",
            "jour_semaine": jour,
            "status": "Succes",
        })
    except Exception:
        # On ne renvoie jamais la stack trace au client : message générique.
        logger.exception("Erreur interne lors de la prediction")
        return jsonify({"erreur": "Erreur interne lors de la prediction."}), 500


# ---------------------------------------------------------------------------
# Mise à disposition des données (rapport E1, compétence C5)
# ---------------------------------------------------------------------------
@app.route('/parkings', methods=['GET'])
def liste_parkings():
    """Renvoie le référentiel des parkings (nom, position, capacité).

    C'est cette liste que le frontend utilise pour poser un marqueur par parking.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT nom, latitude, longitude, capacite_totale FROM parkings ORDER BY nom"
        )
        parkings = [
            {"nom": r[0], "latitude": r[1], "longitude": r[2], "capacite_totale": r[3]}
            for r in cur.fetchall()
        ]
        cur.close()
        conn.close()
        return jsonify(parkings)
    except psycopg2.Error:
        # Base indisponible : on renvoie une erreur claire, sans détail technique.
        return jsonify({"erreur": "Base de donnees indisponible."}), 503


@app.route('/parkings/<nom>/historique', methods=['GET'])
def historique_parking(nom):
    """Renvoie l'historique horodaté d'un parking, paginé.

    Pagination via ?page (>=1) et ?limite (1 à 500) : on ne renvoie jamais des
    milliers de relevés d'un coup, ce qui protège la mémoire et le réseau.
    """
    try:
        page = int(request.args.get('page', 1))
        limite = int(request.args.get('limite', 50))
    except ValueError:
        return jsonify({"erreur": "page et limite doivent etre des entiers."}), 400

    if page < 1 or limite < 1 or limite > 500:
        return jsonify({"erreur": "page >= 1 et limite entre 1 et 500."}), 400

    offset = (page - 1) * limite

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT id FROM parkings WHERE nom = %s", (nom,))
        ligne = cur.fetchone()
        if ligne is None:
            cur.close()
            conn.close()
            return jsonify({"erreur": f"Parking '{nom}' inconnu."}), 404
        parking_id = ligne[0]

        cur.execute(
            """
            SELECT horodatage, places_libres, taux_occupation
            FROM releves
            WHERE parking_id = %s
            ORDER BY horodatage DESC
            LIMIT %s OFFSET %s
            """,
            (parking_id, limite, offset),
        )
        releves = [
            {
                "horodatage": r[0].strftime("%Y-%m-%d %H:%M:%S"),
                "places_libres": r[1],
                "taux_occupation": float(r[2]) if r[2] is not None else None,
            }
            for r in cur.fetchall()
        ]
        cur.close()
        conn.close()
        return jsonify({"parking": nom, "page": page, "limite": limite, "releves": releves})
    except psycopg2.Error:
        return jsonify({"erreur": "Base de donnees indisponible."}), 503


@app.route('/dataset', methods=['GET'])
def dataset():
    """Exporte le jeu d'entraînement, en CSV (défaut) ou en JSON (?format=json)."""
    if not os.path.exists(DATASET_PATH):
        return jsonify({"erreur": "Jeu d'entrainement introuvable."}), 404

    format_demande = request.args.get('format', 'csv').lower()
    df = pd.read_csv(DATASET_PATH)

    if format_demande == 'json':
        return jsonify(df.to_dict(orient='records'))
    elif format_demande == 'csv':
        buffer = io.StringIO()
        df.to_csv(buffer, index=False, quoting=csv.QUOTE_MINIMAL)
        return Response(buffer.getvalue(), mimetype='text/csv')
    else:
        return jsonify({"erreur": "format doit valoir 'csv' ou 'json'."}), 400


if __name__ == "__main__":
    # debug désactivé par défaut ; activable via FLASK_DEBUG=1 en développement.
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug)
