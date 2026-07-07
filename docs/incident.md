# Fiche d'incident — Modèle absent au démarrage

Document de l'épreuve E5 (Bloc 3, compétence C21). Il décrit un incident
technique réel et reproductible, son diagnostic à partir des journaux, sa
résolution et la vérification associée.

| | |
|---|---|
| **Composant** | Service IA (API Flask `apps/ai-service`) |
| **Symptôme** | `/predict` et `/health` renvoient une erreur 500 |
| **Périmètre** | Prédictions indisponibles ; le reste de l'application (carte, liste) continue de fonctionner en mode dégradé |
| **Gravité** | Élevée (fonction cœur indisponible), mais sans perte de données |
| **Branche de reproduction** | `incident/modele-manquant` |
| **Correctif** | Branche `feat/e5-monitorage`, commit `fix:` + test de non-régression |

## 1. Déclenchement

L'API charge le modèle (`models/modele_parkings.pkl`) et l'encodeur au démarrage.
Si ces fichiers sont **absents** — par exemple parce qu'on a oublié de lancer
`predictor.py`, ou que l'artefact n'a pas été déployé — le service démarre quand
même, mais la variable `model` n'est jamais définie dans la version fautive.

## 2. Détection (monitorage — C20)

L'anomalie est visible via le dispositif de surveillance mis en place :

- `GET /metrics` : le **taux d'erreur** grimpe (chaque appel à `/predict` échoue).
- Les **journaux** enregistrent une erreur applicative et un statut 500 :

```json
{"horodatage": "2026-07-07 14:20:29", "niveau": "ERROR", "message": "Modeles introuvables : lance predictor.py d'abord."}
{"horodatage": "2026-07-07 14:20:29", "niveau": "INFO", "message": "requete", "endpoint": "/predict", "parking": "Clemenceau", "duree_ms": 130.5, "statut": 500}
```

## 3. Diagnostic

Les journaux horodatés situent le problème :

1. Au démarrage, la ligne `ERROR ... Modeles introuvables` indique que les
   fichiers modèle n'ont pas été chargés.
2. Chaque `/predict` se termine ensuite en `statut: 500`.

La cause n'est donc **pas** le modèle lui-même, mais le fait que le code
n'anticipe pas son absence : la variable `model` n'existe pas, et l'appel à
`le.transform(...)` provoque une exception non maîtrisée, remontée en 500.

### Reproduction

Sur la branche `incident/modele-manquant`, depuis `apps/ai-service` :

```bash
python reproduire_incident.py
# -> /predict sans modele -> statut HTTP 500 (plantage)
```

## 4. Résolution (correctif — C21)

La correction rend le service **tolérant** à l'absence du modèle :

- on initialise `model = None` et `le = None` avant le chargement conditionnel ;
- `/predict` vérifie que le modèle est chargé et renvoie sinon un **503**
  (« service momentanément indisponible ») avec un message clair, au lieu d'un 500 ;
- `/health` signale l'état `degraded`, ce qui permet de détecter le problème
  immédiatement plutôt qu'au premier appel de prédiction.

Comportement après correctif :

```
/predict sans modele -> statut 503 | {"erreur": "Modele indisponible."}
/health  sans modele -> statut 503 | {"modele_charge": false, "status": "degraded"}
```

Le reste de l'application (carte, liste des parkings) continue de fonctionner :
le frontend affiche « Prédiction indisponible » sans planter (mode dégradé).

## 5. Vérification et non-régression

Un test automatisé fige ce comportement pour éviter que l'incident ne réapparaisse
(`apps/ai-service/tests/test_incident.py`) :

- `test_predict_sans_modele_repond_503` : `/predict` renvoie 503 quand le modèle
  n'est pas chargé ;
- `test_health_signale_le_service_degrade` : `/health` renvoie 503 et
  `modele_charge = false`.

```
pytest -q
15 passed
```

Sur la branche `incident/modele-manquant`, ce même test **échoue** (le service
renvoie 500), ce qui matérialise l'incident ; sur `feat/e5-monitorage`, il
**passe**, ce qui prouve la correction.
