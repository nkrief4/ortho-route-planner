#!/usr/bin/env python3
"""
Pipeline complet : nettoyage → géocodage → carte → routing TSP.

Usage :
    python run_pipeline.py                                  # phases 1-3
    python run_pipeline.py --phases all                     # tout (1-8)
    python run_pipeline.py --phases all --city PARIS         # Paris complet
    python run_pipeline.py --phases all --dept 75            # département 75
    python run_pipeline.py --phases 1,2,3,4,5               # jusqu'à la carte
    python run_pipeline.py --phases all --tsp-limit 60       # TSP 60s
"""

import argparse
import sys
import time


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Pipeline adresses orthophonistes (nettoyage → route optimale)",
    )
    p.add_argument("--input", type=str, default=None, help="Chemin CSV source")
    p.add_argument("--output", type=str, default=None, help="Dossier de sortie")
    p.add_argument("--city", type=str, default=None, help="Filtrer sur une ville")
    p.add_argument("--dept", type=str, default=None, help="Filtrer sur un département (CP)")
    p.add_argument(
        "--phases", type=str, default="1,2,3",
        help="Phases à exécuter : 1,2,3,4,5,6,7,8 ou 'all'",
    )
    p.add_argument(
        "--tsp-limit", type=int, default=30,
        help="Temps max en secondes pour le solveur TSP (défaut: 30)",
    )
    p.add_argument(
        "--closed-loop", action="store_true",
        help="TSP en boucle fermée (retour au point de départ)",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.phases.strip().lower() == "all":
        phases = {1, 2, 3, 4, 5, 6, 7, 8}
    else:
        phases = {int(p.strip()) for p in args.phases.split(",")}

    # Auto-inclure les prérequis
    if phases & {4, 5, 6, 7, 8}:
        phases |= {1, 2, 3}
    if phases & {6, 7, 8}:
        phases |= {4}
    if phases & {7, 8}:
        phases |= {6}
    if 8 in phases:
        phases.add(7)

    t0 = time.time()

    # ─────────────────────────────────────────────────────────────────
    #  PHASE 1 — Chargement
    # ─────────────────────────────────────────────────────────────────
    from pipeline.load import load_csv, print_load_stats

    print("\n" + "=" * 60)
    print("  PHASE 1 — Chargement du CSV")
    print("=" * 60)

    df_raw = load_csv(args.input)
    print_load_stats(df_raw)

    # ── Filtres optionnels ───────────────────────────────────────────
    if args.city:
        city_filter = args.city.strip().upper()
        mask = df_raw["organization_city"].str.upper().str.contains(
            city_filter, na=False,
        )
        df_raw = df_raw[mask].copy()
        df_raw.reset_index(drop=True, inplace=True)
        df_raw["row_id"] = range(1, len(df_raw) + 1)
        print(f"\n  [filtre] ville={city_filter} → {len(df_raw)} lignes")

    if args.dept:
        dept = args.dept.strip().zfill(2)
        mask = df_raw["organization_postal_code"].str[: len(dept)] == dept
        df_raw = df_raw[mask].copy()
        df_raw.reset_index(drop=True, inplace=True)
        df_raw["row_id"] = range(1, len(df_raw) + 1)
        print(f"\n  [filtre] département={dept} → {len(df_raw)} lignes")

    if len(df_raw) == 0:
        print("\n  [stop] Aucune ligne après filtrage.")
        sys.exit(0)

    # ─────────────────────────────────────────────────────────────────
    #  PHASE 2 — Normalisation
    # ─────────────────────────────────────────────────────────────────
    if 2 in phases:
        print("\n" + "=" * 60)
        print("  PHASE 2 — Normalisation des adresses")
        print("=" * 60)

        from pipeline.clean import apply_normalization, print_clean_stats

        df_raw = apply_normalization(df_raw)
        print_clean_stats(df_raw)

    # ─────────────────────────────────────────────────────────────────
    #  PHASE 3 — Table Sites
    # ─────────────────────────────────────────────────────────────────
    if 3 in phases:
        print("\n" + "=" * 60)
        print("  PHASE 3 — Création table Sites + mapping")
        print("=" * 60)

        from pipeline.sites import (
            create_sites_table,
            export_sites,
            merge_site_ids,
            print_sites_stats,
        )

        df_sites = create_sites_table(df_raw)
        df_orthos = merge_site_ids(df_raw, df_sites)
        print_sites_stats(df_sites, df_orthos)

        sites_p, orthos_p = export_sites(df_sites, df_orthos, args.output)
        print(f"\n  → {sites_p}")
        print(f"  → {orthos_p}")

    # ─────────────────────────────────────────────────────────────────
    #  PHASE 4 — Géocodage
    # ─────────────────────────────────────────────────────────────────
    if 4 in phases:
        print("\n" + "=" * 60)
        print("  PHASE 4 — Géocodage des sites")
        print("=" * 60)

        from pipeline.geocode import (
            export_geocoded,
            geocode_sites,
            print_geocode_stats,
        )

        df_sites = geocode_sites(df_sites)
        print_geocode_stats(df_sites)

        geo_path = export_geocoded(df_sites, args.output)
        print(f"\n  → {geo_path}")

    # ─────────────────────────────────────────────────────────────────
    #  PHASE 5 — Carte des sites
    # ─────────────────────────────────────────────────────────────────
    if 5 in phases:
        print("\n" + "=" * 60)
        print("  PHASE 5 — Carte des sites")
        print("=" * 60)

        from pipeline.mapping import create_sites_map, save_map

        m = create_sites_map(df_sites)
        map_path = save_map(m, "map_sites.html", args.output)
        print(f"  → {map_path}")

    # ─────────────────────────────────────────────────────────────────
    #  Préparation routing (filtrer sites routable)
    # ─────────────────────────────────────────────────────────────────
    df_routable = None
    coords = []

    if phases & {6, 7, 8}:
        df_routable = df_sites[
            df_sites["status"].isin(["OK", "WARNING"])
            & df_sites["latitude"].notna()
            & df_sites["longitude"].notna()
        ].copy().reset_index(drop=True)

        coords = list(
            zip(df_routable["latitude"], df_routable["longitude"])
        )
        n_route = len(df_routable)
        print(f"\n  Sites routable : {n_route}")

        if n_route < 2:
            print("  [stop] Pas assez de sites pour calculer un itinéraire.")
            phases -= {6, 7, 8}
        elif n_route > 500:
            print(
                f"  [warn] {n_route} sites → la matrice OSRM sera longue. "
                f"Utilisez --city ou --dept pour réduire."
            )

    # ─────────────────────────────────────────────────────────────────
    #  PHASE 6 — Matrice de distances OSRM
    # ─────────────────────────────────────────────────────────────────
    matrix = None

    if 6 in phases:
        print("\n" + "=" * 60)
        print("  PHASE 6 — Matrice de durées OSRM")
        print("=" * 60)

        from pipeline.routing import compute_duration_matrix

        matrix = compute_duration_matrix(coords)
        print(f"  Matrice {matrix.shape[0]}×{matrix.shape[1]} calculée")

    # ─────────────────────────────────────────────────────────────────
    #  PHASE 7 — TSP (OR-Tools)
    # ─────────────────────────────────────────────────────────────────
    route_order: list[int] = []
    total_duration = 0.0

    if 7 in phases:
        print("\n" + "=" * 60)
        print("  PHASE 7 — Résolution TSP (OR-Tools)")
        print("=" * 60)

        from pipeline.routing import (
            build_route_solution,
            export_route,
            print_route_stats,
            solve_tsp,
        )

        open_path = not args.closed_loop
        mode = "ouvert (pas de retour)" if open_path else "fermé (boucle)"
        print(f"  Mode : {mode}")
        print(f"  Temps max solveur : {args.tsp_limit}s")

        route_order, total_duration = solve_tsp(
            matrix,
            open_path=open_path,
            time_limit=args.tsp_limit,
        )

        df_route = build_route_solution(df_routable, route_order, matrix)
        print_route_stats(df_route, total_duration)

        route_path = export_route(df_route, args.output)
        print(f"\n  → {route_path}")

    # ─────────────────────────────────────────────────────────────────
    #  PHASE 8 — Carte itinéraire
    # ─────────────────────────────────────────────────────────────────
    if 8 in phases and route_order:
        print("\n" + "=" * 60)
        print("  PHASE 8 — Carte de l'itinéraire")
        print("=" * 60)

        from pipeline.mapping import create_route_map, save_map as save_m
        from pipeline.routing import fetch_route_geometry

        # Géométrie routière OSRM si nombre de sites raisonnable
        route_geom = None
        if len(route_order) <= 300:
            print("  Récupération géométrie routière OSRM…")
            route_geom = fetch_route_geometry(coords, route_order)
        else:
            print("  Trop de sites pour la géométrie OSRM, lignes droites utilisées.")

        m = create_route_map(df_routable, route_order, route_geom)
        map_path = save_m(m, "map_route.html", args.output)
        print(f"  → {map_path}")

    # ─────────────────────────────────────────────────────────────────
    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"  Pipeline terminé en {elapsed:.1f}s")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
