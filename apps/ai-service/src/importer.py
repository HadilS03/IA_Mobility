"""Import de l'historique brut des parkings dans PostgreSQL.

On lit data/raw/historique_parkings.json (une capture GeoJSON horodatée par ligne)
et on alimente les deux tables : parkings (référentiel) et releves (historique).

Le script est IDEMPOTENT et RELANÇABLE : on peut le rejouer autant de fois qu'on
veut sans créer de doublon, grâce aux contraintes UNIQUE de la base
(nom unique pour un parking, couple parking+horodatage unique pour un relevé).
On choisit le JSON brut plutôt que le CSV car lui seul contient les coordonnées
GPS, indispensables pour afficher les parkings sur la carte.
"""
import json
import os
import sys

# Permet de lancer le script directement (python src/importer.py) tout en
# important le module db du même dossier.
sys.path.insert(0, os.path.dirname(__file__))
from db import get_connection

FICHIER_RAW = os.path.join("data", "raw", "historique_parkings.json")


def _extraire_total(prop):
    """Récupère la capacité totale malgré les noms de champ variables de la source."""
    for cle in ("total", "np_total", "np_global"):
        if prop.get(cle) is not None:
            return prop[cle]
    return None


def _extraire_libres(prop):
    """Récupère les places libres malgré les noms de champ variables de la source."""
    for cle in ("libres", "nb_places_disponibles"):
        if prop.get(cle) is not None:
            return prop[cle]
    return None


def importer():
    if not os.path.exists(FICHIER_RAW):
        print(f"ERREUR : fichier introuvable : {FICHIER_RAW}")
        return

    conn = get_connection()
    cur = conn.cursor()

    # Cache nom -> id pour éviter de réinterroger la base à chaque relevé.
    parkings_vus = {}

    with open(FICHIER_RAW, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if not line.strip():
                continue
            try:
                capture = json.loads(line)
                horodatage = capture["sauvegarde_le"]

                for feature in capture["donnees"]:
                    prop = feature["properties"]
                    nom = prop.get("nom")
                    if not nom:
                        continue

                    total = _extraire_total(prop)
                    if total is None or total <= 0:
                        # Sans capacité valide, la ligne n'est pas exploitable.
                        continue

                    libres = _extraire_libres(prop)
                    libres = max(0, libres if libres is not None else 0)
                    # Un taux d'occupation est borné à [0, 100] : on nettoie les
                    # valeurs aberrantes de la source (ex. plus de places libres
                    # que la capacité annoncée) avant insertion.
                    taux = max(0.0, min(100.0, round((total - libres) / total * 100, 2)))

                    # Coordonnées GeoJSON : [longitude, latitude].
                    coords = feature.get("geometry", {}).get("coordinates", [None, None])
                    longitude, latitude = coords[0], coords[1]

                    # 1) Upsert du parking. ON CONFLICT rend l'opération idempotente
                    #    et garde la plus grande capacité observée.
                    if nom not in parkings_vus:
                        cur.execute(
                            """
                            INSERT INTO parkings (nom, latitude, longitude, capacite_totale)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (nom) DO UPDATE
                              SET latitude = EXCLUDED.latitude,
                                  longitude = EXCLUDED.longitude,
                                  capacite_totale = GREATEST(parkings.capacite_totale,
                                                             EXCLUDED.capacite_totale)
                            RETURNING id
                            """,
                            (nom, latitude, longitude, total),
                        )
                        parkings_vus[nom] = cur.fetchone()[0]

                    parking_id = parkings_vus[nom]

                    # 2) Insert du relevé. ON CONFLICT DO NOTHING : un relevé déjà
                    #    présent (même parking, même horodatage) est ignoré.
                    cur.execute(
                        """
                        INSERT INTO releves (parking_id, horodatage, places_libres, taux_occupation)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (parking_id, horodatage) DO NOTHING
                        """,
                        (parking_id, horodatage, libres, taux),
                    )

                # Commit après chaque capture : on garde la progression, et une
                # capture problématique n'annule pas tout l'import.
                conn.commit()

            except Exception as e:
                # En cas d'erreur, on annule uniquement la capture en cours et on
                # repart proprement (le cache doit refléter l'état commité).
                conn.rollback()
                parkings_vus.clear()
                print(f"Ligne {i + 1} ignorée : {e}")

    # On rapporte l'état réel de la base plutôt qu'un compteur mémoire.
    cur.execute("SELECT (SELECT count(*) FROM parkings), (SELECT count(*) FROM releves)")
    nb_parkings, nb_releves = cur.fetchone()
    cur.close()
    conn.close()
    print(f"Import terminé : {nb_parkings} parkings, {nb_releves} relevés en base.")


if __name__ == "__main__":
    importer()
