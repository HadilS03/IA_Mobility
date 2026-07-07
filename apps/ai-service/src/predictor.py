import os

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder

# Chemins
FICHIER_CLEAN = os.path.join("data", "processed", "data_training.csv")
DOSSIER_MODELE = "models"
MODELE_PATH = os.path.join(DOSSIER_MODELE, "modele_parkings.pkl")
ENCODER_PATH = os.path.join(DOSSIER_MODELE, "encoder_noms.pkl")

def entrainer_ia():
    print(f"--- Entraînement de l'IA sur {FICHIER_CLEAN} ---")

    if not os.path.exists(FICHIER_CLEAN):
        print("[ERREUR] CSV introuvable. Lance processor.py d'abord.")
        return

    # 1. Chargement des données
    df = pd.read_csv(FICHIER_CLEAN)

    if len(df) < 10:
        print("[ATTENTION] Pas assez de donnees pour entrainer l'IA.")
        return

    # 2. Encodage des noms (Transformer 'Clemenceau' en 1, 'Victoire' en 2, etc.)
    le = LabelEncoder()
    df['nom_encoded'] = le.fit_transform(df['nom'])

    # 3. Préparation des variables (X = entrées, y = ce qu'on veut deviner)
    # On utilise : Nom du parking, Heure, Jour de la semaine, Minute
    X = df[['nom_encoded', 'heure', 'jour_semaine', 'minute']]
    y = df['occupation_pct']

    # 4. Création et entraînement du modèle (Random Forest est top pour ça)
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)

    # 5. Sauvegarde du modèle ET de l'encodeur
    os.makedirs(DOSSIER_MODELE, exist_ok=True)
    joblib.dump(model, MODELE_PATH)
    joblib.dump(le, ENCODER_PATH)

    print("[OK] IA entrainee avec succes.")
    print(f"Parkings memorises : {len(le.classes_)}")
    print(f"Precision du modele (R2) : {round(model.score(X, y) * 100, 2)}%")

if __name__ == "__main__":
    entrainer_ia()
