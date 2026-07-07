"""Tests de l'API via le client de test Flask (E3/C12).

Ces tests ne dépendent pas de la base de données : ils ciblent /health et
/predict, qui ne s'appuient que sur le modèle chargé en mémoire.
"""


def test_health_repond_ok(client):
    reponse = client.get('/health')
    assert reponse.status_code == 200
    data = reponse.get_json()
    assert data["modele_charge"] is True
    assert data["nb_parkings"] > 0


def test_predict_parking_connu(client):
    reponse = client.get('/predict?nom=Clemenceau')
    assert reponse.status_code == 200
    assert 'prediction_occupation' in reponse.get_json()


def test_predict_sans_nom(client):
    reponse = client.get('/predict')
    assert reponse.status_code == 400


def test_predict_parking_inconnu(client):
    reponse = client.get('/predict?nom=ParkingQuiNexistePas')
    assert reponse.status_code == 404


def test_predict_heure_invalide(client):
    # heure=99 est hors bornes -> 400 sans planter.
    reponse = client.get('/predict?nom=Clemenceau&heure=99')
    assert reponse.status_code == 400


def test_predict_avec_parametres_temporels(client):
    # On rejoue une prédiction à un moment précis (fonction utile en démo).
    reponse = client.get('/predict?nom=Clemenceau&heure=8&jour=1&minute=0')
    assert reponse.status_code == 200
    assert reponse.get_json()["heure_analyse"] == "8h00"


# --- Protection des endpoints de données par clé d'API (C5) ---

def test_parkings_sans_cle_renvoie_401(client, monkeypatch):
    # Une clé est configurée mais absente de la requête -> accès refusé.
    monkeypatch.setenv("DATA_API_KEY", "cle-de-test")
    reponse = client.get('/parkings')
    assert reponse.status_code == 401


def test_parkings_avec_cle_valide(client, monkeypatch):
    # Avec la bonne clé, l'accès est autorisé : 200 si la base répond, ou 503
    # si elle est absente en environnement de test (les deux sont acceptables).
    monkeypatch.setenv("DATA_API_KEY", "cle-de-test")
    reponse = client.get('/parkings', headers={"X-API-Key": "cle-de-test"})
    assert reponse.status_code in (200, 503)


def test_documentation_openapi_disponible(client):
    # La spécification OpenAPI (flasgger) doit être générée sans erreur (C5).
    reponse = client.get('/apispec_1.json')
    assert reponse.status_code == 200
