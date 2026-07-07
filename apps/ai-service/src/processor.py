import pandas as pd
import json
import os

# Chemins des fichiers

# Change cette ligne pour correspondre au vrai nom dans ton dossier
FICHIER_RAW = os.path.join("data", "raw", "historique_parkings.json")
DOSSIER_PROCESSED = os.path.join("data", "processed")
FICHIER_CLEAN = os.path.join(DOSSIER_PROCESSED, "data_training.csv")

def transformer_donnees():
    print(f"--- Démarrage de la transformation ---")
    
    # 1. Vérification de l'existence du fichier source
    if not os.path.exists(FICHIER_RAW):
        print(f"[ERREUR] Le fichier {FICHIER_RAW} est introuvable.")
        return

    # 2. Création du dossier processed s'il n'existe pas
    if not os.path.exists(DOSSIER_PROCESSED):
        os.makedirs(DOSSIER_PROCESSED)

    all_rows = []
    
    # 3. Lecture et extraction des données
    with open(FICHIER_RAW, "r") as f:
        for i, line in enumerate(f):
            if not line.strip(): 
                continue 
            
            try:
                capture = json.loads(line)
                date_capture = pd.to_datetime(capture["sauvegarde_le"])
                
                # --- TON BLOC DE CODE INTÉGRÉ ICI ---
                for parking in capture["donnees"]:
                    prop = parking["properties"]
                    nom = prop.get("nom", "Inconnu")
                    
                    # On teste avec des valeurs par défaut précises
                    total = prop.get("total")
                    if total is None: total = prop.get("np_total")
                    if total is None: total = prop.get("np_global")
                    
                    libres = prop.get("libres")
                    if libres is None: libres = prop.get("nb_places_disponibles")

                    # --- LE TEST DE VERITE ---
                    if total is not None and total > 0:
                        # Si on a un total mais pas de "libres", on met 0 au lieu de rien
                        libres_clean = libres if libres is not None else 0
                        occ_pct = (total - libres_clean) / total * 100
                        
                        all_rows.append({
                            "nom": nom,
                            "total": total,
                            "libres": libres_clean,
                            "occupation_pct": round(occ_pct, 2),
                            "heure": date_capture.hour,
                            "jour_semaine": date_capture.dayofweek,
                            "minute": date_capture.minute
                        })
                    else:
                        # Diagnostic pour comprendre pourquoi on n'en a que 4
                        if i == 0: # On affiche seulement pour la première capture
                            print(f"[IGNORE] Parking: {nom} | total={total} | libres={libres}")
                # --------------------------------------

            except Exception as e:
                print(f"[ATTENTION] Erreur a la ligne {i+1} : {e}")

    # 4. Conversion et sauvegarde
    if all_rows:
        df = pd.DataFrame(all_rows)
        # Supprime les doublons si on a collecté plusieurs fois les mêmes données
        df = df.drop_duplicates()
        df.to_csv(FICHIER_CLEAN, index=False)
        print(f"[OK] {len(df)} lignes enregistrées.")
        print(f"Parkings differents dans le CSV : {df['nom'].nunique()}")
    else:
        print("[ATTENTION] Aucune donnee n'a pu être extraite.")

if __name__ == "__main__":
    transformer_donnees()