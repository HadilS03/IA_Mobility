import requests
import json
import time
import os

# Configuration
CLE = "UFM1S7RTLN"  # Remplace par ta vraie clé quand tu l'auras
# On ajoute un filtre pour ne prendre que les parkings qui sont 'LIBRE' (ouverts)
URL = f"https://data.bordeaux-metropole.fr/geojson?key={CLE}&typename=st_park_p"
FICHIER_DEST = "data/raw/historique_parkings.json"

def collecter():
    try:
        response = requests.get(URL)
        if response.status_code == 200:
            data = response.json()
            #TEST 
           # print("STRUCTURE DU PREMIER PARKING :", data['features'][0]['properties'])
            #TEST
            nb_recus = len(data.get('features', []))
            print(f"📡 L'API a envoyé {nb_recus} parkings.")
            
            # On ajoute l'heure de la capture
            capture = {
                "sauvegarde_le": time.strftime("%Y-%m-%d %H:%M:%S"),
                "donnees": data['features']
            }
            # On écrit dans le dossier data/raw
            with open(FICHIER_DEST, "a") as f:
                f.write(json.dumps(capture) + "\n")
            print(f"[{capture['sauvegarde_le']}] Données enregistrées.")
        else:
            print(f"Erreur API : {response.status_code}")
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    while True:
        collecter()
        time.sleep(120) # Attend 2 minutes

        

