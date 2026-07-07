"""Protocole d'évaluation du modèle de prédiction d'occupation.

Module séparé de l'entraînement de production (src/predictor.py, non modifié) :
il sert à MESURER honnêtement la qualité du modèle, pas à le livrer. Il fait un
découpage temporel, calcule des métriques d'erreur, les compare à des baselines
simples, et fige un jeu de test pour les tests de non-régression.

Lancer depuis apps/ai-service :  python -m src.evaluator
"""
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import LabelEncoder

FICHIER_CLEAN = os.path.join("data", "processed", "data_training.csv")
TEST_SET_FIGE = os.path.join("data", "processed", "test_set_fige.csv")
DOSSIER_MODELE = "models"
MODELE_EVALUE = os.path.join(DOSSIER_MODELE, "modele_evalue.pkl")
IMPORTANCE_PNG = "importance_variables.png"

# Mêmes variables d'entrée que le modèle de production (src/predictor.py).
FEATURES = ["nom_encoded", "heure", "jour_semaine", "minute"]
CIBLE = "occupation_pct"


def _diagnostic(df):
    """Affiche un état des lieux du jeu de données avant évaluation."""
    print(f"Lignes : {len(df)} | Parkings : {df['nom'].nunique()}")
    jours = sorted(df["jour_semaine"].unique().tolist())
    heures = sorted(df["heure"].unique().tolist())
    print(f"Jours de semaine distincts : {jours}")
    print(f"Heures distinctes : {heures}")
    if len(jours) < 5:
        print(
            "[AVERTISSEMENT] la variable jour_semaine ne peut pas etre apprise, "
            "prolongez la collecte."
        )


def _baseline_moyenne(train, test):
    """Baseline (a) : moyenne d'occupation par (nom, jour_semaine, heure).

    Repli en cascade quand la combinaison exacte n'a jamais été observée dans le
    train : moyenne du parking, puis moyenne globale.
    """
    moy_fine = train.groupby(["nom", "jour_semaine", "heure"])[CIBLE].mean()
    moy_parking = train.groupby("nom")[CIBLE].mean()
    moy_globale = train[CIBLE].mean()

    predictions = []
    for _, ligne in test.iterrows():
        cle = (ligne["nom"], ligne["jour_semaine"], ligne["heure"])
        if cle in moy_fine.index:
            predictions.append(moy_fine.loc[cle])
        elif ligne["nom"] in moy_parking.index:
            predictions.append(moy_parking.loc[ligne["nom"]])
        else:
            predictions.append(moy_globale)
    return predictions


def _baseline_persistance(train, test):
    """Baseline (b) : dernière valeur connue du parking dans le train.

    Le train étant chronologique, la dernière ligne d'un parking est sa dernière
    mesure observée. Repli sur la moyenne globale si le parking est absent du train.
    """
    derniere = train.groupby("nom")[CIBLE].last()
    globale = train[CIBLE].mean()
    return [derniere.loc[n] if n in derniere.index else globale for n in test["nom"]]


def _sauver_importance(model):
    """Sauvegarde le graphique d'importance des variables si matplotlib est présent.

    matplotlib est optionnel : l'import est protégé pour ne pas en faire une
    dépendance obligatoire du service.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")  # backend sans écran (exécution en ligne de commande)
        import matplotlib.pyplot as plt
    except ImportError:
        print("[INFO] matplotlib absent : graphique d'importance non genere.")
        return
    plt.figure()
    plt.bar(FEATURES, model.feature_importances_)
    plt.title("Importance des variables")
    plt.tight_layout()
    plt.savefig(IMPORTANCE_PNG)
    plt.close()
    print(f"[OK] Graphique d'importance : {IMPORTANCE_PNG}")


def evaluer():
    if not os.path.exists(FICHIER_CLEAN):
        print(f"[ERREUR] Jeu de donnees introuvable : {FICHIER_CLEAN}")
        return

    df = pd.read_csv(FICHIER_CLEAN)
    _diagnostic(df)

    if len(df) < 10:
        print("[ERREUR] Pas assez de donnees pour evaluer.")
        return

    # Découpage temporel 80/20 PAR POSITION de ligne (jamais aléatoire) : le CSV
    # est en append chronologique. Un split aléatoire placerait des captures quasi
    # identiques (relevées à 2 min d'intervalle) des deux côtés du découpage, ce
    # qui provoquerait une fuite temporelle et des scores trop optimistes.
    split = int(len(df) * 0.8)
    train = df.iloc[:split].copy()
    test = df.iloc[split:].copy()

    # Encodage des noms ajusté sur le TRAIN uniquement (comme en conditions réelles).
    le = LabelEncoder()
    train["nom_encoded"] = le.fit_transform(train["nom"])

    # On écarte du test les parkings jamais vus dans le train (non encodables).
    connus = set(le.classes_)
    avant = len(test)
    test = test[test["nom"].isin(connus)].copy()
    ecartes = avant - len(test)
    if ecartes:
        print(f"[INFO] {ecartes} ligne(s) de test ecartee(s) : parking inconnu du train.")

    if train.empty or test.empty:
        print("[ERREUR] Train ou test vide apres decoupage.")
        return

    test["nom_encoded"] = le.transform(test["nom"])

    # Entraînement (mêmes hyperparamètres que src/predictor.py).
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(train[FEATURES], train[CIBLE])

    pred_test = model.predict(test[FEATURES])
    pred_train = model.predict(train[FEATURES])
    mae_test = mean_absolute_error(test[CIBLE], pred_test)
    rmse_test = float(np.sqrt(mean_squared_error(test[CIBLE], pred_test)))
    mae_train = mean_absolute_error(train[CIBLE], pred_train)

    print(
        f"\nModele : MAE test = {mae_test:.2f} | RMSE test = {rmse_test:.2f} "
        f"| MAE train = {mae_train:.2f} (ecart train/test = indice de sur-apprentissage)"
    )

    # Baselines évaluées sur le MÊME jeu de test que le modèle.
    mae_moy = mean_absolute_error(test[CIBLE], _baseline_moyenne(train, test))
    mae_persist = mean_absolute_error(test[CIBLE], _baseline_persistance(train, test))
    print(f"Baseline moyenne (nom,jour,heure) : MAE = {mae_moy:.2f}")
    print(f"Baseline persistance : MAE = {mae_persist:.2f}")

    # Importance des variables.
    print("\nImportance des variables :")
    for nom_var, imp in zip(FEATURES, model.feature_importances_):
        print(f"  {nom_var} : {imp:.3f}")
    _sauver_importance(model)

    # Sauvegardes : jeu de test figé + bundle du modèle évalué.
    os.makedirs(DOSSIER_MODELE, exist_ok=True)
    test[FEATURES + [CIBLE]].to_csv(TEST_SET_FIGE, index=False)
    joblib.dump(
        {"model": model, "label_encoder": le, "features": FEATURES, "mae_test": mae_test},
        MODELE_EVALUE,
    )
    print(f"\n[OK] Jeu de test fige : {TEST_SET_FIGE}")
    print(f"[OK] Modele evalue : {MODELE_EVALUE}")

    # Phrase récapitulative, prête pour une diapositive de soutenance.
    print(
        f"\nRECAP : le modele Random Forest atteint une MAE de {mae_test:.2f} points "
        f"d'occupation sur un test temporel, contre {mae_moy:.2f} pour la baseline "
        f"moyenne (nom, jour, heure) et {mae_persist:.2f} pour la persistance."
    )


if __name__ == "__main__":
    evaluer()
