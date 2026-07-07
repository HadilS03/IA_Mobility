import csv
import io
import json
import os
import time
from datetime import datetime
from functools import wraps

import joblib
import pandas as pd
import psycopg2
from flasgger import Swagger
from flask import Flask, Response, g, jsonify, request

from src.db import get_connection
from src.logging_config import configurer_logs

app = Flask(__name__)

# Documentation OpenAPI auto-générée (accessible sur /apidocs).
app.config["SWAGGER"] = {"title": "IA Mobility — API", "openapi": "3.0.2"}
swagger = Swagger(app)

# Chemins ancrés sur l'emplacement du fichier : le service fonctionne quel que
# soit le dossier depuis lequel on le lance (démo, tests, Docker).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELE_PATH = os.path.join(BASE_DIR, "models", "modele_parkings.pkl")
ENCODER_PATH = os.path.join(BASE_DIR, "models", "encoder_noms.pkl")
DATASET_PATH = os.path.join(BASE_DIR, "data", "processed", "data_training.csv")
RAW_PATH = os.path.join(BASE_DIR, "data", "raw", "historique_parkings.json")
LOG_DIR = os.path.join(BASE_DIR, "logs")

logger = configurer_logs(LOG_DIR)

# Compteurs de monitorage (E5/C20), alimentés à chaque requête. En mémoire :
# simples et suffisants pour suivre la santé du service ; remis à zéro au
# redémarrage, ce qui est acceptable pour ce niveau de supervision.
metriques = {"nb_requetes": 0, "nb_erreurs": 0, "duree_totale_ms": 0.0}

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

    # Alimente les compteurs de monitorage (une requête = un point de mesure).
    metriques["nb_requetes"] += 1
    if response.status_code >= 400:
        metriques["nb_erreurs"] += 1
    if duree_ms is not None:
        metriques["duree_totale_ms"] += duree_ms

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


@app.after_request
def _autoriser_cors(response):
    # Le frontend (autre origine : port différent) doit pouvoir appeler l'API.
    # L'API est publique et en lecture seule, on autorise donc toutes les origines.
    # Nos requêtes sont de simples GET : pas de préflight à gérer.
    response.headers["Access-Control-Allow-Origin"] = "*"
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


# Clé d'API attendue pour les endpoints de données (valeur au démarrage ;
# le décorateur la relit dynamiquement via os.getenv pour rester testable).
API_KEY = os.getenv("DATA_API_KEY", "")


def cle_api_requise(vue):
    """Protège un endpoint par une clé d'API transmise dans l'en-tête X-API-Key.

    Sécurité par défaut : si aucune clé n'est configurée (DATA_API_KEY vide),
    l'accès est refusé — jamais d'API de données ouverte par simple oubli de
    configuration.
    """
    @wraps(vue)
    def wrapper(*args, **kwargs):
        # Lecture dynamique : indispensable pour que les tests puissent définir
        # la clé via monkeypatch après l'import du module.
        cle_attendue = os.getenv("DATA_API_KEY", "")
        cle_fournie = request.headers.get("X-API-Key", "")
        if not cle_attendue or cle_fournie != cle_attendue:
            return jsonify({"erreur": "Cle d'API manquante ou invalide."}), 401
        return vue(*args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------------
# Santé du service (E3/C11)
# ---------------------------------------------------------------------------
@app.route('/health', methods=['GET'])
def health():
    """Indique si le service est opérationnel (modèle chargé).
    ---
    tags:
      - Supervision (C20)
    responses:
      200:
        description: Service opérationnel, modèle chargé.
      503:
        description: Service dégradé, modèle non chargé.
    """
    charge = model is not None and le is not None
    corps = {
        "status": "ok" if charge else "degraded",
        "modele_charge": charge,
        "nb_parkings": len(le.classes_) if charge else 0,
    }
    return jsonify(corps), 200 if charge else 503


def _derniere_collecte():
    """Horodatage de la dernière capture enregistrée par le collecteur.

    Lu depuis la dernière ligne du fichier d'historique brut : indicateur
    concret de « la collecte tourne-t-elle toujours ? ». None si indisponible.
    """
    try:
        derniere = None
        with open(RAW_PATH, "r", encoding="utf-8") as f:
            for ligne in f:
                if ligne.strip():
                    derniere = ligne
        if derniere:
            return json.loads(derniere).get("sauvegarde_le")
    except Exception:
        return None
    return None


@app.route('/metrics', methods=['GET'])
def metrics():
    """Indicateurs de santé du service, issus de la journalisation des requêtes.

    Nombre de requêtes, taux d'erreur, temps de réponse moyen et date de la
    dernière collecte réussie : de quoi surveiller l'application d'un coup d'œil (E5/C20).
    ---
    tags:
      - Supervision (C20)
    responses:
      200:
        description: Indicateurs de monitorage du service.
    """
    nb = metriques["nb_requetes"]
    taux_erreur = round(metriques["nb_erreurs"] / nb * 100, 2) if nb else 0.0
    temps_moyen = round(metriques["duree_totale_ms"] / nb, 2) if nb else 0.0
    return jsonify({
        "nb_requetes": nb,
        "nb_erreurs": metriques["nb_erreurs"],
        "taux_erreur_pct": taux_erreur,
        "temps_reponse_moyen_ms": temps_moyen,
        "modele_charge": model is not None and le is not None,
        "derniere_collecte": _derniere_collecte(),
    })


# ---------------------------------------------------------------------------
# Prédiction d'occupation (E3/C9)
# ---------------------------------------------------------------------------
@app.route('/predict', methods=['GET'])
def predict():
    """Prédit le taux d'occupation d'un parking à un moment donné.
    ---
    tags:
      - Modele (C9)
    parameters:
      - name: nom
        in: query
        required: true
        schema:
          type: string
        description: Nom du parking (doit être connu du modèle).
      - name: heure
        in: query
        required: false
        schema:
          type: integer
        description: Heure 0-23 (défaut - heure courante).
      - name: jour
        in: query
        required: false
        schema:
          type: integer
        description: Jour de la semaine 0-6, lundi=0 (défaut - jour courant).
      - name: minute
        in: query
        required: false
        schema:
          type: integer
        description: Minute 0-59 (défaut - minute courante).
    responses:
      200:
        description: Prédiction d'occupation renvoyée.
      400:
        description: Paramètre manquant ou invalide.
      404:
        description: Parking inconnu du modèle.
      500:
        description: Erreur interne lors de la prédiction.
      503:
        description: Modèle indisponible.
    """
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
#
# Seuls ces trois endpoints (exposition du jeu de données) sont protégés par
# clé d'API. On NE protège PAS /health ni /metrics (sondes de supervision qui
# doivent rester interrogeables), ni /predict (exposition du modèle, périmètre
# C9, appelé librement par l'interface).
# ---------------------------------------------------------------------------
@app.route('/parkings', methods=['GET'])
@cle_api_requise
def liste_parkings():
    """Renvoie le référentiel des parkings (nom, position, capacité).

    C'est cette liste que le frontend utilise pour poser un marqueur par parking.
    ---
    tags:
      - Donnees (C5)
    parameters:
      - name: X-API-Key
        in: header
        required: true
        schema:
          type: string
        description: Clé d'API d'accès aux données.
    responses:
      200:
        description: Liste des parkings.
      401:
        description: Clé d'API manquante ou invalide.
      503:
        description: Base de données indisponible.
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
@cle_api_requise
def historique_parking(nom):
    """Renvoie l'historique horodaté d'un parking, paginé.

    Pagination via ?page (>=1) et ?limite (1 à 500) : on ne renvoie jamais des
    milliers de relevés d'un coup, ce qui protège la mémoire et le réseau.
    ---
    tags:
      - Donnees (C5)
    parameters:
      - name: nom
        in: path
        required: true
        schema:
          type: string
        description: Nom du parking.
      - name: X-API-Key
        in: header
        required: true
        schema:
          type: string
        description: Clé d'API d'accès aux données.
      - name: page
        in: query
        required: false
        schema:
          type: integer
        description: Numéro de page (>= 1, défaut 1).
      - name: limite
        in: query
        required: false
        schema:
          type: integer
        description: Nombre de relevés par page (1 à 500, défaut 50).
    responses:
      200:
        description: Historique paginé du parking.
      400:
        description: Paramètre de pagination invalide.
      401:
        description: Clé d'API manquante ou invalide.
      404:
        description: Parking inconnu.
      503:
        description: Base de données indisponible.
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
@cle_api_requise
def dataset():
    """Exporte le jeu d'entraînement, en CSV (défaut) ou en JSON (?format=json).
    ---
    tags:
      - Donnees (C5)
    parameters:
      - name: X-API-Key
        in: header
        required: true
        schema:
          type: string
        description: Clé d'API d'accès aux données.
      - name: format
        in: query
        required: false
        schema:
          type: string
          enum: [csv, json]
        description: Format d'export (csv par défaut).
    responses:
      200:
        description: Jeu d'entraînement exporté.
      400:
        description: Format demandé invalide.
      401:
        description: Clé d'API manquante ou invalide.
      404:
        description: Jeu d'entraînement introuvable.
    """
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
