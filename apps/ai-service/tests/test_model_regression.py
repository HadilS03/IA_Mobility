"""Tests de non-régression du modèle évalué (E3/C12).

Ils s'appuient sur les artefacts produits par src/evaluator.py
(models/modele_evalue.pkl et data/processed/test_set_fige.csv). Tant que
l'évaluation n'a pas été lancée, ces fichiers sont absents et les tests se
skippent proprement, afin de ne pas casser la CI.
"""
import os

import joblib
import pandas as pd
import pytest
from sklearn.metrics import mean_absolute_error

# Seuil maximal de MAE toléré sur le jeu de test figé.
# TODO: fixer à MAE mesurée + 20 % après la première évaluation.
SEUIL_MAE = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUNDLE_PATH = os.path.join(BASE_DIR, "models", "modele_evalue.pkl")
TEST_SET_PATH = os.path.join(BASE_DIR, "data", "processed", "test_set_fige.csv")


def _charger_artefacts():
    """Charge le bundle du modèle évalué et le jeu figé, ou skippe s'ils sont absents."""
    if not os.path.exists(BUNDLE_PATH) or not os.path.exists(TEST_SET_PATH):
        pytest.skip(
            "Evaluation non lancee : modele_evalue.pkl / test_set_fige.csv absents."
        )
    bundle = joblib.load(BUNDLE_PATH)
    jeu = pd.read_csv(TEST_SET_PATH)
    return bundle, jeu


def test_predictions_dans_les_bornes():
    # Toute prédiction sur le jeu figé doit rester un pourcentage plausible.
    bundle, jeu = _charger_artefacts()
    predictions = bundle["model"].predict(jeu[bundle["features"]])
    assert predictions.min() >= 0
    assert predictions.max() <= 100


def test_non_regression_mae():
    # Garde-fou : la performance ne doit pas se dégrader au-delà du seuil fixé.
    if SEUIL_MAE is None:
        pytest.skip("SEUIL_MAE non fixe : lancer l'evaluation puis definir le seuil.")
    bundle, jeu = _charger_artefacts()
    predictions = bundle["model"].predict(jeu[bundle["features"]])
    mae = mean_absolute_error(jeu["occupation_pct"], predictions)
    assert mae <= SEUIL_MAE


def test_format_features():
    # Les variables attendues par le modèle doivent exister dans le jeu figé.
    bundle, jeu = _charger_artefacts()
    for feature in bundle["features"]:
        assert feature in jeu.columns
