"""Configuration partagée des tests pytest.

Placé à la racine du service pour que `main` et le package `src` soient
importables quel que soit l'endroit d'où pytest est lancé.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app  # noqa: E402  (import après ajout du chemin)


@pytest.fixture
def client():
    """Client de test Flask : permet d'appeler l'API sans lancer de vrai serveur."""
    app.config.update(TESTING=True)
    return app.test_client()
