"""Test de non-régression de l'incident « modèle manquant » (E5/C21).

Contexte : si le fichier modèle est absent au démarrage (oubli d'entraînement,
artefact non déployé), l'API doit rester debout et répondre proprement — et non
planter avec une erreur 500.

Ici on simule un modèle non chargé en forçant model/le à None, puis on vérifie
que /predict et /health répondent bien 503 (service dégradé) au lieu de 500.
"""
import main


def test_predict_sans_modele_repond_503(client):
    modele, encodeur = main.model, main.le
    main.model, main.le = None, None
    try:
        reponse = client.get('/predict?nom=Clemenceau')
        assert reponse.status_code == 503
    finally:
        # On restaure le modèle pour ne pas perturber les autres tests.
        main.model, main.le = modele, encodeur


def test_health_signale_le_service_degrade(client):
    modele, encodeur = main.model, main.le
    main.model, main.le = None, None
    try:
        reponse = client.get('/health')
        assert reponse.status_code == 503
        assert reponse.get_json()["modele_charge"] is False
    finally:
        main.model, main.le = modele, encodeur


def test_metrics_repond_meme_service_normal(client):
    # /metrics doit toujours répondre (support du monitorage, E5/C20).
    reponse = client.get('/metrics')
    assert reponse.status_code == 200
    corps = reponse.get_json()
    assert "nb_requetes" in corps
    assert "taux_erreur_pct" in corps
    assert "temps_reponse_moyen_ms" in corps
