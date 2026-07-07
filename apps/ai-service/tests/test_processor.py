"""Tests unitaires du nettoyage des données (processor.py, E1/C3)."""
from src.processor import extraire_lignes


def _capture(features):
    return {"sauvegarde_le": "2026-03-17 14:30:00", "donnees": features}


def _feature(props):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [0, 0]},
        "properties": props,
    }


def test_calcul_occupation():
    # 100 places, 25 libres -> 75 % d'occupation.
    cap = _capture([_feature({"nom": "Test", "total": 100, "libres": 25})])
    lignes = extraire_lignes(cap)
    assert len(lignes) == 1
    ligne = lignes[0]
    assert ligne["occupation_pct"] == 75.0
    # Variables temporelles tirées de l'horodatage.
    assert ligne["heure"] == 14
    assert ligne["minute"] == 30


def test_parking_sans_capacite_est_ignore():
    # Sans total valide, la ligne n'est pas exploitable.
    cap = _capture([_feature({"nom": "SansCapacite", "total": None, "libres": 10})])
    assert extraire_lignes(cap) == []


def test_libres_absent_compte_zero():
    # Si "libres" manque, on considère 0 place libre (parking plein).
    cap = _capture([_feature({"nom": "Complet", "total": 50})])
    ligne = extraire_lignes(cap)[0]
    assert ligne["libres"] == 0
    assert ligne["occupation_pct"] == 100.0


def test_noms_de_champ_alternatifs():
    # La source nomme parfois les champs différemment : on doit les reconnaître.
    cap = _capture([_feature({"nom": "Alt", "np_total": 200, "nb_places_disponibles": 50})])
    ligne = extraire_lignes(cap)[0]
    assert ligne["total"] == 200
    assert ligne["libres"] == 50
    assert ligne["occupation_pct"] == 75.0
