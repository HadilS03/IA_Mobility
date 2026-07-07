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

        # Sans capacité valide, la ligne n'est pas exploitable : on l'ignore.
        if total is not None and total > 0:
            libres_clean = libres if libres is not None else 0
            occ_pct = (total - libres_clean) / total * 100
            lignes.append({
                "nom": nom,
                "total": total,
                "libres": libres_clean,
                "occupation_pct": round(occ_pct, 2),
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
