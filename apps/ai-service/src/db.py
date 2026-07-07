"""Accès à la base PostgreSQL.

Un seul point d'entrée (get_connection) partagé par l'importer et l'API.
Les paramètres viennent des variables d'environnement (voir .env.example),
jamais du code : on ne veut pas de mot de passe en dur dans le dépôt.
"""
import os
import psycopg2


def get_connection():
    """Ouvre une connexion PostgreSQL à partir des variables d'environnement.

    Laisse remonter l'exception psycopg2 si la base est injoignable :
    l'appelant (API ou script) décide quoi en faire, plutôt que de masquer
    l'erreur ici.
    """
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "ia_mobility"),
        user=os.getenv("POSTGRES_USER", "ia_mobility"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
    )
