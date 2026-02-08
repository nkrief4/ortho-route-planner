#!/usr/bin/env python3
"""
Point d'entrée unique : charge les données, lance l'interface web.

Usage :
    venv/bin/python app.py
    venv/bin/python app.py --port 5001
    venv/bin/python app.py --skip-geocode     # ne pas géocoder au démarrage
"""

import argparse
import math
import sys
import time
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, render_template, request

# ── Chemin racine ─────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from pipeline.config import INPUT_CSV
from pipeline.load import load_csv
from pipeline.clean import apply_normalization
from pipeline.sites import create_sites_table, merge_site_ids
from pipeline.geocode import geocode_sites

# ── Données globales (chargées au démarrage) ──────────────────────────
_data = {
    "df_raw": None,
    "df_sites": None,
    "df_orthos": None,
    "cities": [],       # [{"name": "PARIS", "count": 1098, "depts": ["75001", ...]}, ...]
    "ready": False,
}


# ═══════════════════════════════════════════════════════════════════════
#  Utilitaires : calcul de distance
# ═══════════════════════════════════════════════════════════════════════

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcule la distance en kilomètres entre deux points GPS (formule de Haversine).
    """
    R = 6371.0  # Rayon de la Terre en km

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


# ═══════════════════════════════════════════════════════════════════════
#  Initialisation des données
# ═══════════════════════════════════════════════════════════════════════

def init_data(skip_geocode: bool = False) -> None:
    """Charge le CSV enrichi, normalise, crée la table sites, géocode."""
    t0 = time.time()

    # ── Vérifier que le CSV enrichi existe ─────────────────────────────
    if not INPUT_CSV.exists():
        print(f"\n  [erreur] Fichier enrichi introuvable : {INPUT_CSV}")
        print("  Lancez d'abord : venv/bin/python scraping/main.py --code 91")
        sys.exit(1)

    # ── Phase 1 : Chargement ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  PHASE 1 — Chargement du CSV")
    print("=" * 60)
    df_raw = load_csv()
    print(f"  {len(df_raw)} lignes chargées")

    # ── Phase 2 : Normalisation ───────────────────────────────────────
    print("\n" + "=" * 60)
    print("  PHASE 2 — Normalisation des adresses")
    print("=" * 60)
    df_raw = apply_normalization(df_raw)
    n_keys = (df_raw["address_key"] != "").sum()
    print(f"  {n_keys} adresses normalisées")

    # ── Phase 3 : Table Sites ─────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  PHASE 3 — Création table Sites")
    print("=" * 60)
    df_sites = create_sites_table(df_raw)
    df_orthos = merge_site_ids(df_raw, df_sites)
    print(f"  {len(df_sites)} sites uniques")

    # ── Phase 4 : Géocodage (optionnel) ───────────────────────────────
    if not skip_geocode:
        print("\n" + "=" * 60)
        print("  PHASE 4 — Géocodage des sites (avec cache)")
        print("=" * 60)
        df_sites = geocode_sites(df_sites)
        n_ok = (df_sites["status"] == "OK").sum()
        n_warn = (df_sites["status"] == "WARNING").sum()
        print(f"  OK={n_ok}  WARNING={n_warn}  FAILED={(df_sites['status'] == 'FAILED').sum()}")
    else:
        print("\n  [skip] Géocodage ignoré (--skip-geocode)")
        # Ajouter des colonnes vides pour éviter les erreurs
        for col in ["geocoded_label", "latitude", "longitude", "score", "status"]:
            if col not in df_sites.columns:
                df_sites[col] = None
        df_sites["status"] = df_sites["status"].fillna("PENDING")
        df_sites["score"] = df_sites["score"].fillna(0.0)

    # ── Construire la liste des villes ─────────────────────────────────
    cities = _build_city_list(df_sites)

    _data["df_raw"] = df_raw
    _data["df_sites"] = df_sites
    _data["df_orthos"] = df_orthos
    _data["cities"] = cities
    _data["ready"] = True

    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"  Données prêtes en {elapsed:.1f}s — {len(cities)} villes disponibles")
    print(f"{'=' * 60}\n")


def _build_city_list(df_sites) -> list[dict]:
    """Construit la liste des villes avec le nombre de sites et les CP."""
    cities_data = []

    grouped = df_sites.groupby("city_clean")
    for city_name, group in grouped:
        if not city_name or city_name == "":
            continue

        depts = sorted(group["postal_code_clean"].unique().tolist())
        n_sites = len(group)
        n_orthos = int(group["nb_orthos"].sum())

        cities_data.append({
            "name": city_name,
            "sites": n_sites,
            "orthos": n_orthos,
            "depts": depts,
        })

    # Trier par nombre d'orthos décroissant
    cities_data.sort(key=lambda c: c["orthos"], reverse=True)
    return cities_data


# ═══════════════════════════════════════════════════════════════════════
#  Application Flask
# ═══════════════════════════════════════════════════════════════════════

app = Flask(__name__, template_folder=str(ROOT / "templates"))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/cities")
def api_cities():
    """Liste des villes avec leurs stats."""
    return jsonify(_data["cities"])


@app.route("/api/geocode", methods=["POST"])
def api_geocode():
    """
    Géocode une adresse de départ fournie par l'utilisateur.
    Body JSON : {
        "address": "15 Avenue des Champs-Élysées",
        "city": "Paris",           # Ville sélectionnée (optionnel)
        "postal_code": "75008"     # Code postal/arrondissement (optionnel)
    }
    """
    from pipeline.geocode import geocode_one

    body = request.get_json(force=True)
    address = (body.get("address") or "").strip()
    city = (body.get("city") or "").strip()
    postal_code = (body.get("postal_code") or "").strip()

    if not address:
        return jsonify({"error": "Adresse vide"}), 400

    try:
        # Si la ville n'est pas fournie, essayer de l'extraire de l'adresse
        if not city:
            parts = address.split(",")
            if len(parts) >= 2:
                city = parts[-1].strip()

        # Chercher un code postal dans l'adresse si non fourni
        if not postal_code:
            import re
            cp_match = re.search(r'\b\d{5}\b', address)
            if cp_match:
                postal_code = cp_match.group()

        # Construire l'adresse complète pour le géocodage
        full_address = address
        if city and city.lower() not in address.lower():
            full_address = f"{address}, {city}"

        result = geocode_one(
            address_line=full_address,
            postal_code=postal_code,
            city=city,
            address_normalized=full_address,
        )

        if not result.get("latitude") or not result.get("longitude"):
            return jsonify({
                "error": "Adresse introuvable",
                "address": full_address,
            }), 404

        if result["score"] < 0.4:
            return jsonify({
                "error": f"Adresse incertaine (score: {result['score']:.2f})",
                "result": result,
                "suggestion": "Vérifiez l'adresse saisie",
            }), 404

        return jsonify({
            "address": full_address,
            "geocoded_label": result["geocoded_label"],
            "latitude": result["latitude"],
            "longitude": result["longitude"],
            "score": result["score"],
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate", methods=["POST"])
def api_generate():
    """
    Génère le shortest path pour une ville ou un code postal.
    Body JSON : {
        "city": "PARIS",
        "dept": "75015",
        "closed_loop": false,
        "tsp_limit": 30,
        "start_address": "15 Avenue des Champs-Élysées, Paris",  # NOUVEAU
        "start_lat": 48.8698,                                      # NOUVEAU (pré-géocodé)
        "start_lon": 2.3078,                                       # NOUVEAU
        "radius_km": 5                                             # NOUVEAU (rayon en km)
    }
    """
    if not _data["ready"]:
        return jsonify({"error": "Données pas encore chargées"}), 503

    body = request.get_json(force=True)
    city_filter = (body.get("city") or "").strip().upper()
    dept_filter = (body.get("dept") or "").strip()
    closed_loop = body.get("closed_loop", False)
    tsp_limit = int(body.get("tsp_limit", 30))

    # NOUVEAU : Point de départ personnalisé
    start_lat = body.get("start_lat")
    start_lon = body.get("start_lon")
    start_address = body.get("start_address", "")

    df_sites = _data["df_sites"].copy()

    # ── Filtrage ──────────────────────────────────────────────────────
    if dept_filter:
        mask = df_sites["postal_code_clean"].str.startswith(dept_filter)
        df_sites = df_sites[mask].copy()
    elif city_filter:
        mask = df_sites["city_clean"].str.upper() == city_filter
        df_sites = df_sites[mask].copy()
    else:
        return jsonify({"error": "Veuillez spécifier une ville ou un code postal"}), 400

    if len(df_sites) == 0:
        return jsonify({"error": "Aucun site trouvé pour ce filtre"}), 404

    # ── Filtrer les sites routable (géocodés) ─────────────────────────
    df_routable = df_sites[
        df_sites["status"].isin(["OK", "WARNING"])
        & df_sites["latitude"].notna()
        & df_sites["longitude"].notna()
    ].copy().reset_index(drop=True)

    n_routable = len(df_routable)

    if n_routable < 2:
        # Pas assez de sites pour un itinéraire → renvoyer juste la carte
        from pipeline.mapping import create_sites_map
        m = create_sites_map(df_sites.reset_index(drop=True))
        map_html = m._repr_html_()
        return jsonify({
            "map_html": map_html,
            "route": [],
            "stats": {
                "total_sites": len(df_sites),
                "routable_sites": n_routable,
                "message": "Pas assez de sites géocodés pour calculer un itinéraire.",
            },
        })

    if n_routable > 300:
        return jsonify({
            "error": (
                f"Trop de sites ({n_routable}) pour le calcul en temps réel. "
                f"Filtrez par arrondissement/code postal."
            ),
        }), 400

    # ── Phase 6 : Matrice OSRM ────────────────────────────────────────
    from pipeline.routing import (
        compute_duration_matrix,
        solve_tsp,
        build_route_solution,
        fetch_route_geometry,
    )
    from pipeline.mapping import create_route_map

    coords = list(zip(df_routable["latitude"], df_routable["longitude"]))

    # ── NOUVEAU : Ajout du point de départ si fourni ──────────────────
    start_point_idx = None
    if start_lat is not None and start_lon is not None:
        # Vérifier si le point de départ est déjà dans la liste
        # (si l'adresse de départ est un cabinet d'ortho)
        is_existing = False
        for i, (lat, lon) in enumerate(coords):
            if abs(lat - start_lat) < 0.0001 and abs(lon - start_lon) < 0.0001:
                start_point_idx = i
                is_existing = True
                print(f"  [route] Point de départ = site existant (index {i})")
                break

        if not is_existing:
            # Ajouter le point de départ au début de coords ET df_routable
            coords.insert(0, (start_lat, start_lon))
            start_point_idx = 0

            # Créer une ligne fictive pour le point de départ dans df_routable
            start_row = pd.DataFrame([{
                "site_id": "START_POINT",
                "geocoded_label": start_address or f"Point de départ ({start_lat:.4f}, {start_lon:.4f})",
                "latitude": start_lat,
                "longitude": start_lon,
                "nb_orthos": 0,
            }])
            df_routable = pd.concat([start_row, df_routable], ignore_index=True)

            print(f"  [route] Point de départ ajouté : {start_address}")

    print(f"  [route] Calcul matrice OSRM pour {len(coords)} points…")
    matrix = compute_duration_matrix(coords)

    # ── Phase 7 : TSP ─────────────────────────────────────────────────
    open_path = not closed_loop
    print(f"  [route] Résolution TSP (limit={tsp_limit}s, open={open_path})…")

    # Si on a un point de départ, forcer le TSP à commencer là
    if start_point_idx is not None:
        route_order, total_duration = solve_tsp(
            matrix,
            open_path=open_path,
            time_limit=tsp_limit,
            start_index=start_point_idx
        )
    else:
        route_order, total_duration = solve_tsp(
            matrix,
            open_path=open_path,
            time_limit=tsp_limit
        )

    # ── Build solution DataFrame ──────────────────────────────────────
    df_route = build_route_solution(df_routable, route_order, matrix)

    # ── Enrichir avec les infos des orthophonistes ────────────────────
    df_orthos = _data["df_orthos"]

    # Pour chaque site de l'itinéraire, récupérer les orthos
    site_ids = df_route["site_id"].tolist()
    orthos_by_site = {}

    for site_id in site_ids:
        orthos_at_site = df_orthos[df_orthos["site_id"] == site_id]
        orthos_list = []
        for _, ortho in orthos_at_site.iterrows():
            orthos_list.append({
                "family_name": str(ortho.get("family_name", "")),
                "given_names": str(ortho.get("given_names", "")),
                "email": str(ortho.get("organization_email", "") or ortho.get("role_email", "")),
                "phone": str(ortho.get("organization_phone", "") or ortho.get("role_phone", "")),
            })
        orthos_by_site[site_id] = orthos_list

    # ── Phase 8 : Géométrie + carte ───────────────────────────────────
    route_geom = None
    if len(route_order) <= 300:
        print("  [route] Récupération géométrie routière OSRM…")
        route_geom = fetch_route_geometry(coords, route_order)

    # Enrichir df_routable avec les noms avant de créer la carte
    df_routable_enriched = df_routable.copy()
    df_routable_enriched["orthos_list"] = df_routable_enriched["site_id"].apply(
        lambda sid: orthos_by_site.get(sid, [])
    )

    m = create_route_map(df_routable_enriched, route_order, route_geom)
    map_html = m._repr_html_()

    # ── Construire la réponse ─────────────────────────────────────────
    route_list = []
    for _, r in df_route.iterrows():
        site_id = r.get("site_id")
        route_list.append({
            "order": int(r["visit_order"]),
            "label": str(r.get("geocoded_label", "")),
            "orthos": int(r.get("nb_orthos", 0)),
            "orthos_list": orthos_by_site.get(site_id, []),
            "segment_min": float(r.get("segment_min", 0)),
            "cumul_min": float(r.get("cumul_min", 0)),
            "lat": float(r.get("latitude", 0)),
            "lon": float(r.get("longitude", 0)),
        })

    total_min = total_duration / 60
    total_h = total_duration / 3600

    return jsonify({
        "map_html": map_html,
        "route": route_list,
        "stats": {
            "total_sites": len(df_sites),
            "routable_sites": n_routable,
            "visited_sites": len(route_order),
            "total_duration_min": round(total_min, 1),
            "total_duration_h": round(total_h, 2),
            "avg_segment_min": round(total_min / max(len(route_order) - 1, 1), 1),
            "closed_loop": closed_loop,
        },
    })


# ═══════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser(description="Ortho Route Planner — Interface Web")
    p.add_argument("--port", type=int, default=5000)
    p.add_argument("--host", type=str, default="127.0.0.1")
    p.add_argument("--skip-geocode", action="store_true",
                   help="Ne pas géocoder au démarrage (utiliser le cache existant)")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    init_data(skip_geocode=args.skip_geocode)
    print(f"  Serveur web : http://{args.host}:{args.port}")
    print("  Ctrl+C pour arrêter\n")
    app.run(host=args.host, port=args.port, debug=False)
