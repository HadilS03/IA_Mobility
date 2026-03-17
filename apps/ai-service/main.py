from flask import Flask, jsonify, request
import joblib
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)

# Chemins des modèles
MODELE_PATH = os.path.join("models", "modele_parkings.pkl")
ENCODER_PATH = os.path.join("models", "encoder_noms.pkl")

# Chargement du modèle et de l'encodeur
if os.path.exists(MODELE_PATH) and os.path.exists(ENCODER_PATH):
    model = joblib.load(MODELE_PATH)
    le = joblib.load(ENCODER_PATH)
    print(f"✅ IA et Encodeur chargés (92 parkings prêts !)")
else:
    print("❌ ERREUR : Modèles introuvables. Lance predictor.py d'abord.")

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

if __name__ == "__main__":
    # On lance l'API sur le port 5000
    app.run(host="0.0.0.0", port=5000, debug=True)