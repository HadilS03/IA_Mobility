import json
import os

import pandas as pd

# Chemins des fichiers
FICHIER_RAW = os.path.join("data", "raw", "historique_parkings.json")
DOSSIER_PROCESSED = os.path.join("data", "processed")
FICHIER_CLEAN = os.path.join(DOSSIER_PROCESSED, "data_training.csv")


def extraire_lignes(capture):
    """Transforme une capture brute en lignes propres, prêtes pour l'entraînement.

    Fonction pure (pas de lecture/écriture de fichier) pour être testable
    facilement. Elle applique le nettoyage décrit dans le rapport E1 :
      - récupère nom/total/libres malgré les noms de champ variables de la source ;
      - écarte les parkings sans capacité valide (non exploitables) ;
      - calcule le taux d'occupation ;
      - enrichit avec des variables temporelles tirées de l'horodatage.
    """
    date_capture = pd.to_datetime(capture["sauvegarde_le"])
    lignes = []

    for parking in capture["donnees"]:
        prop = parking["properties"]
        nom = prop.get("nom", "Inconnu")

        # La source ne nomme pas toujours les champs pareil : on teste plusieurs clés.
        total = prop.get("total")
        if total is None:
            total = prop.get("np_total")
        if total is None:
            total = prop.get("np_global")

        libres = prop.get("libres")
        if libres is None:
            libres = prop.get("nb_places_disponibles")

        # On ne conserve une ligne que si la capacité ET la mesure de places
        # libres sont réellement disponibles. On écarte une ligne sans mesure
        # plutôt que d'inventer une donnée d'apprentissage : imputer libres=0
        # fabriquerait des parkings « pleins » fantômes et biaiserait le modèle
        # vers la saturation.
        if total is not None and total > 0 and libres is not None:
            # Un taux d'occupation est physiquement borné à [0, 100]. La source
            # renvoie parfois plus de places libres que la capacité (bruit
            # capteur) -> taux négatif : on borne, comme le font déjà importer.py
            # et l'API (borner_taux), pour garder une cible d'apprentissage propre.
            occ_pct = max(0.0, min(100.0, round((total - libres) / total * 100, 2)))
            lignes.append({
                "nom": nom,
                "total": total,
                "libres": libres,
                "occupation_pct": occ_pct,
                "heure": date_capture.hour,
                "jour_semaine": date_capture.dayofweek,
                "minute": date_capture.minute,
            })

    return lignes


def transformer_donnees():
    print("--- Demarrage de la transformation ---")

    if not os.path.exists(FICHIER_RAW):
        print(f"[ERREUR] Le fichier {FICHIER_RAW} est introuvable.")
        return

    if not os.path.exists(DOSSIER_PROCESSED):
        os.makedirs(DOSSIER_PROCESSED)

    all_rows = []

    with open(FICHIER_RAW, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if not line.strip():
                continue
            try:
                capture = json.loads(line)
                all_rows.extend(extraire_lignes(capture))
            except Exception as e:
                print(f"[ATTENTION] Erreur a la ligne {i + 1} : {e}")

    if all_rows:
        df = pd.DataFrame(all_rows)
        # Supprime les doublons : deux captures rapprochées peuvent être identiques.
        df = df.drop_duplicates()
        df.to_csv(FICHIER_CLEAN, index=False)
        print(f"[OK] {len(df)} lignes enregistrees.")
        print(f"Parkings differents dans le CSV : {df['nom'].nunique()}")
    else:
        print("[ATTENTION] Aucune donnee n'a pu etre extraite.")


if __name__ == "__main__":
    transformer_donnees()
