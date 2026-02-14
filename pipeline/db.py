"""
Module de connexion MongoDB Atlas pour le suivi des visites.

Collection : get_ortho.visits
Document :
    {
        "site_id": "48.86444,2.34709",
        "label": "28 Rue Etienne Marcel 75002 Paris",
        "lat": 48.864435,
        "lon": 2.347086,
        "visited_at": "2026-02-14T10:30:00Z"
    }
"""

import os
from datetime import datetime, timezone

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

_client = None
_collection = None


def _get_collection():
    """Lazy-init : connexion MongoDB à la première utilisation."""
    global _client, _collection
    if _collection is not None:
        return _collection

    uri = os.environ.get("MONGODB_URI", "")
    if not uri:
        raise RuntimeError(
            "MONGODB_URI non défini. Ajoutez-le dans votre fichier .env"
        )

    _client = MongoClient(uri)

    # Vérifier la connexion
    try:
        _client.admin.command("ping")
        print("  [MongoDB] Connexion OK")
    except ConnectionFailure as e:
        raise RuntimeError(f"Impossible de se connecter à MongoDB : {e}")

    db = _client["get_ortho"]
    _collection = db["visits"]

    # Index unique sur site_id pour éviter les doublons
    _collection.create_index("site_id", unique=True)

    return _collection


def get_all_visits() -> list[dict]:
    """Retourne tous les sites visités."""
    col = _get_collection()
    visits = []
    for doc in col.find({}, {"_id": 0}):
        visits.append(doc)
    return visits


def mark_visited(site_id: str, label: str, lat: float, lon: float) -> dict:
    """Insère un document visite. Retourne le document inséré."""
    col = _get_collection()
    doc = {
        "site_id": site_id,
        "label": label,
        "lat": lat,
        "lon": lon,
        "visited_at": datetime.now(timezone.utc).isoformat(),
    }
    col.update_one(
        {"site_id": site_id},
        {"$setOnInsert": doc},
        upsert=True,
    )
    return doc


def unmark_visited(site_id: str) -> bool:
    """Supprime une visite. Retourne True si supprimé."""
    col = _get_collection()
    result = col.delete_one({"site_id": site_id})
    return result.deleted_count > 0


def is_visited(site_id: str) -> bool:
    """Retourne True si le site a été visité."""
    col = _get_collection()
    return col.count_documents({"site_id": site_id}, limit=1) > 0
