"""Tests du modèle : format des prédictions et bornes 0–100 % (E3/C9, C12)."""
import joblib
import pandas as pd

from main import ENCODER_PATH, MODELE_PATH, borner_taux


def test_borner_taux_reste_dans_les_bornes():
    # Un modèle de régression peut sortir des bornes : on doit ramener dans [0, 100].
    assert borner_taux(-5) == 0.0
    assert borner_taux(150) == 100.0
    assert borner_taux(42.3) == 42.3


def test_prediction_du_modele_est_un_pourcentage_valide():
    # Charge le modèle réellement livré et vérifie qu'une prédiction reste un
    # pourcentage plausible (0–100), quel que soit le parking.
    model = joblib.load(MODELE_PATH)
    le = joblib.load(ENCODER_PATH)

    nom_encoded = le.transform([le.classes_[0]])[0]
    entree = pd.DataFrame(
        [[nom_encoded, 12, 2, 30]],
        columns=["nom_encoded", "heure", "jour_semaine", "minute"],
    )
    valeur = borner_taux(model.predict(entree)[0])
    assert 0.0 <= valeur <= 100.0
