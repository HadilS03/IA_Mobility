from flask import Flask, jsonify, request, Response
import joblib
import pandas as pd
import os
import csv
import io
from datetime import datetime

import psycopg2
from src.db import get_connection

app = Flask(__name__)

# Chemins des modèles
MODELE_PATH = os.path.join("models", "modele_parkings.pkl")
ENCODER_PATH = os.path.join("models", "encoder_noms.pkl")
DATASET_PATH = os.path.join("data", "processed", "data_training.csv")

# Chargement du modèle et de l'encodeur
if os.path.exists(MODELE_PATH) and os.path.exists(ENCODER_PATH):
    model = joblib.load(MODELE_PATH)
    le = joblib.load(ENCODER_PATH)
    print(f"[OK] Modele et encodeur charges ({len(le.classes_)} parkings prets).")
else:
    print("[ERREUR] Modeles introuvables. Lance predictor.py d'abord.")


@app.route('/predict', methods=['GET'])
def predict():
    # Récupération du nom du parking dans l'URL (ex: ?nom=Clemenceau)
    nom_parking = request.args.get('nom')

    if not nom_parking:
        return jsonify({"erreur": "Veuillez préciser un nom de parking"}), 400

    try:
        # 1. On transforme le nom en chiffre
        # Si le parking n'est pas connu, ça ira dans le 'except'
        nom_encoded = le.transform([nom_parking])[0]

        # 2. On récupère l'heure actuelle
        maintenant = datetime.now()
        heure = maintenant.hour
        jour = maintenant.weekday()
        minute = maintenant.minute

        # 3. Prédiction
        input_data = pd.DataFrame([[nom_encoded, heure, jour, minute]],
                                 columns=['nom_encoded', 'heure', 'jour_semaine', 'minute'])
        prediction = model.predict(input_data)[0]

        return jsonify({
            "parking": nom_parking,
            "prediction_occupation": f"{round(prediction, 2)}%",
            "heure_analyse": f"{heure}h{minute}",
            "status": "Succès"
        })

    except ValueError:
        return jsonify({
            "erreur": f"Le parking '{nom_parking}' est inconnu.",
            "liste_disponible": list(le.classes_[:5]) + ["..."] # On en montre quelques-uns
        }), 404
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500


# ---------------------------------------------------------------------------
# Mise à disposition des données (rapport E1, compétence C5)
# Ces trois endpoints exposent le référentiel et l'historique stockés dans
# PostgreSQL, ainsi que le jeu d'entraînement. Ils permettent au frontend et
# à un tiers de consommer la donnée sans connaître son stockage interne.
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
        return jsonify({"erreur": "Base de données indisponible."}), 503


@app.route('/parkings/<nom>/historique', methods=['GET'])
def historique_parking(nom):
    """Renvoie l'historique horodaté d'un parking, paginé.

    Pagination via ?page (>=1) et ?limite (1 à 500) : on ne renvoie jamais des
    milliers de relevés d'un coup, ce qui protège la mémoire et le réseau.
    """
    # Validation des paramètres : on refuse tout de suite une entrée invalide.
    try:
        page = int(request.args.get('page', 1))
        limite = int(request.args.get('limite', 50))
    except ValueError:
        return jsonify({"erreur": "page et limite doivent être des entiers."}), 400

    if page < 1 or limite < 1 or limite > 500:
        return jsonify({"erreur": "page >= 1 et limite entre 1 et 500."}), 400

    offset = (page - 1) * limite

    try:
        conn = get_connection()
        cur = conn.cursor()

        # Le parking existe-t-il ? Sinon 404 explicite plutôt qu'une liste vide.
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
        return jsonify({"erreur": "Base de données indisponible."}), 503


@app.route('/dataset', methods=['GET'])
def dataset():
    """Exporte le jeu d'entraînement, en CSV (défaut) ou en JSON (?format=json).

    Utile pour rejouer l'entraînement ou vérifier la donnée qui alimente le modèle.
    """
    if not os.path.exists(DATASET_PATH):
        return jsonify({"erreur": "Jeu d'entraînement introuvable."}), 404

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
    # On lance l'API sur le port 5000
    app.run(host="0.0.0.0", port=5000, debug=True)
