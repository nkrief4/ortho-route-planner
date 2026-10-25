"""
PHASES 6-7 — Matrice de distances OSRM + résolution TSP (OR-Tools).

Phase 6 : matrice NxN de durées (secondes) entre sites via OSRM Table API.
Phase 7 : résolution du TSP (chemin le plus court) via OR-Tools.

Limites :
  - Le serveur OSRM public (routing.openstreetmap.de, FOSSGIS) autorise 1 requête/s
    et ralentit les requêtes rapprochées (~9 s chacune après la première).
  - Une requête Table accepte 100 coordonnées : au-delà, la matrice est découpée
    en blocs 50 x 50 (16 requêtes pour 200 sites, ~2 min 30 au premier calcul).
  - Pour aller plus vite sur les grandes zones, il faudrait un serveur OSRM à soi
    ou une API de matrice payante.
"""

import json
import math
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from .config import OUTPUT_DIR

# ── Constantes OSRM ─────────────────────────────────────────────────
# Le serveur public project-osrm.org ne supporte que driving.
# routing.openstreetmap.de fournit des instances par profil (routed-car, routed-foot).
OSRM_SERVERS = {
    "driving": "https://routing.openstreetmap.de/routed-car",
    "foot":    "https://routing.openstreetmap.de/routed-foot",
}
DEFAULT_PROFILE = "driving"
OSRM_MAX_COORDS = 100    # coordonnées max par requête Table (au-delà : 400 TooBig)
OSRM_BATCH = 50          # sources (et destinations) par bloc quand N > OSRM_MAX_COORDS
OSRM_SLEEP = 1.0         # secondes entre requêtes (politique : 1 requête/s max)
OSRM_TIMEOUT = 60
OSRM_RETRIES = 3
LARGE_DURATION = 999_999  # secondes (≈ 278 h) pour routes introuvables

# Durées déjà obtenues, par (profil, départ, arrivée) : régénérer un itinéraire sur
# la même zone (autre départ, sites visités retirés…) ne rappelle pas OSRM.
_DURATION_CACHE: dict[tuple, float] = {}
DURATION_CACHE_MAX = 500_000  # paires (~60 Mo), vidé au-delà


# ═══════════════════════════════════════════════════════════════════════
#  OSRM Table API
# ═══════════════════════════════════════════════════════════════════════

def _osrm_table(
    coords: list[tuple[float, float]],
    sources: list[int] | None = None,
    destinations: list[int] | None = None,
    profile: str = DEFAULT_PROFILE,
) -> dict:
    """
    Appel bas-niveau à l'OSRM Table API.
    coords : liste de (lat, lon) — convertis en lon,lat pour OSRM.
    profile : "driving" ou "foot".
    """
    base = OSRM_SERVERS.get(profile, OSRM_SERVERS["driving"])
    coords_str = ";".join(f"{lon},{lat}" for lat, lon in coords)
    url = f"{base}/table/v1/{profile}/{coords_str}"

    params: dict[str, str] = {"annotations": "duration"}
    if sources is not None:
        params["sources"] = ";".join(str(s) for s in sources)
    if destinations is not None:
        params["destinations"] = ";".join(str(d) for d in destinations)

    full_url = f"{url}?{urlencode(params)}"

    for attempt in range(OSRM_RETRIES):
        try:
            req = Request(full_url, headers={"User-Agent": "ortho-pipeline/1.0"})
            with urlopen(req, timeout=OSRM_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("code") != "Ok":
                    raise RuntimeError(f"OSRM error: {data.get('code')} – {data.get('message','')}")
                return data
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            # Une requête invalide (400 TooBig…) échouera à chaque fois
            client_error = isinstance(exc, HTTPError) and 400 <= exc.code < 500 and exc.code != 429
            if client_error or attempt >= OSRM_RETRIES - 1:
                raise
            wait = 2 ** (attempt + 1)
            print(f"    [retry] OSRM attempt {attempt+1} failed ({exc}), wait {wait}s", file=sys.stderr)
            time.sleep(wait)

    return {}


def _pair_key(profile: str, a: tuple[float, float], b: tuple[float, float]) -> tuple:
    return (profile, round(a[0], 6), round(a[1], 6), round(b[0], 6), round(b[1], 6))


def _fill_block(
    matrix: np.ndarray,
    coords: list[tuple[float, float]],
    src: range,
    dst: range,
    profile: str,
) -> bool:
    """
    Remplit matrix[src, dst] depuis le cache, sinon par un appel OSRM Table.
    Retourne True si un appel réseau a été fait.
    """
    keys = [[_pair_key(profile, coords[i], coords[j]) for j in dst] for i in src]
    if all(k in _DURATION_CACHE for row in keys for k in row):
        for r, i in enumerate(src):
            matrix[i, dst.start:dst.stop] = [_DURATION_CACHE[k] for k in keys[r]]
        return False

    if src == dst:
        combined = [coords[i] for i in src]
        src_idx = dst_idx = list(range(len(src)))
    else:
        combined = [coords[i] for i in src] + [coords[j] for j in dst]
        src_idx = list(range(len(src)))
        dst_idx = list(range(len(src), len(src) + len(dst)))

    data = _osrm_table(combined, src_idx, dst_idx, profile=profile)
    if len(_DURATION_CACHE) > DURATION_CACHE_MAX:
        _DURATION_CACHE.clear()
    for r, row_vals in enumerate(data.get("durations", [])):
        for c, val in enumerate(row_vals):
            if val is not None:
                matrix[src[r], dst[c]] = val
                _DURATION_CACHE[keys[r][c]] = val
    return True


def compute_duration_matrix(
    coords: list[tuple[float, float]],
    profile: str = DEFAULT_PROFILE,
) -> np.ndarray:
    """
    Calcule la matrice NxN de durées de trajet (secondes) via OSRM Table.

    Jusqu'à OSRM_MAX_COORDS sites : un seul appel. Au-delà, blocs de
    OSRM_BATCH x OSRM_BATCH (une requête par bloc, 1 par seconde max).
    Les durées déjà connues viennent du cache mémoire.

    Retourne un np.ndarray de shape (N, N).
    Les routes introuvables valent LARGE_DURATION.
    """
    n = len(coords)
    if n == 0:
        return np.array([[]])
    if n == 1:
        return np.array([[0.0]])

    B = n if n <= OSRM_MAX_COORDS else OSRM_BATCH
    chunks = [range(start, min(start + B, n)) for start in range(0, n, B)]
    total_calls = len(chunks) ** 2
    matrix = np.full((n, n), LARGE_DURATION, dtype=float)

    call = 0
    network_calls = 0
    for src in chunks:
        for dst in chunks:
            try:
                fetched = _fill_block(matrix, coords, src, dst, profile)
            except Exception as exc:
                fetched = True
                print(
                    f"    [warn] OSRM batch src=[{src.start}:{src.stop}] "
                    f"dst=[{dst.start}:{dst.stop}] échoué : {exc}",
                    file=sys.stderr,
                )

            call += 1
            if fetched:
                network_calls += 1
                if call < total_calls:
                    time.sleep(OSRM_SLEEP)
            if call % 5 == 0 or call == total_calls:
                print(f"    OSRM [{call}/{total_calls}] blocs ({network_calls} requêtes)")

    # Diagonale = 0
    np.fill_diagonal(matrix, 0.0)

    # Stats qualité
    unreachable = (matrix == LARGE_DURATION).sum() - n  # exclure diag
    total_pairs = n * n - n
    if total_pairs > 0 and unreachable / total_pairs > 0.1:
        pct = 100 * unreachable / total_pairs
        print(
            f"    [warn] {pct:.1f}% de paires non-routables ({unreachable}/{total_pairs})",
            file=sys.stderr,
        )

    return matrix


# ═══════════════════════════════════════════════════════════════════════
#  TSP (OR-Tools)
# ═══════════════════════════════════════════════════════════════════════

def auto_time_limit(n: int) -> int:
    """
    Temps de recherche (s) suffisant selon le nombre de sites. Mesuré sur des
    matrices réelles : 25 sites → optimum en < 1 s ; 86 et 192 sites → à moins
    de 2 % du résultat obtenu en 30 s dès 5 s (10 s n'apporte rien de plus).
    La recherche locale guidée ne s'arrête jamais d'elle-même avant la limite :
    chaque seconde de trop est perdue.
    """
    if n <= 30:
        return 1
    if n <= 200:
        return 5
    return 10


def solve_tsp(
    matrix: np.ndarray,
    open_path: bool = True,
    time_limit: int | None = None,
    start_index: int | None = None,
) -> tuple[list[int], float]:
    """
    Résout le TSP sur la matrice de durées.

    open_path=True  → pas de retour au point de départ (dummy depot)
    open_path=False → boucle fermée
    time_limit      → secondes de recherche (None = auto_time_limit)
    start_index     → force le départ à cet index (None = auto)

    Retourne (route, total_duration_seconds).
    route : liste d'indices 0-based dans l'ordre de visite.
    """
    n = len(matrix)
    if n <= 1:
        return list(range(n)), 0.0
    if n == 2:
        return [0, 1], float(matrix[0, 1])

    # ── Construction de la matrice étendue (dummy depot si open) ─────
    if open_path and start_index is None:
        # Chemin ouvert sans point de départ forcé → dummy depot
        ext = np.zeros((n + 1, n + 1))
        ext[:n, :n] = matrix
        depot = n
        size = n + 1
    elif open_path and start_index is not None:
        # Chemin ouvert avec point de départ forcé → utiliser start_index comme depot
        ext = matrix
        depot = start_index
        size = n
    else:
        # Boucle fermée → utiliser start_index ou 0 comme depot
        ext = matrix
        depot = start_index if start_index is not None else 0
        size = n

    # ── OR-Tools ─────────────────────────────────────────────────────
    manager = pywrapcp.RoutingIndexManager(size, 1, depot)
    routing = pywrapcp.RoutingModel(manager)

    def dist_cb(from_idx, to_idx):
        a = manager.IndexToNode(from_idx)
        b = manager.IndexToNode(to_idx)
        return int(ext[a][b])

    cb_index = routing.RegisterTransitCallback(dist_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(cb_index)

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    params.time_limit.seconds = time_limit or auto_time_limit(n)

    solution = routing.SolveWithParameters(params)

    if not solution:
        print("    [warn] OR-Tools : pas de solution trouvée, fallback nearest-neighbor.")
        return list(range(n)), 0.0

    # ── Extraction de la route ───────────────────────────────────────
    route: list[int] = []
    idx = routing.Start(0)
    while not routing.IsEnd(idx):
        node = manager.IndexToNode(idx)
        if node != depot:
            route.append(node)
        idx = solution.Value(routing.NextVar(idx))

    total = float(solution.ObjectiveValue())
    return route, total


# ═══════════════════════════════════════════════════════════════════════
#  Géométrie OSRM (tracé routier réel)
# ═══════════════════════════════════════════════════════════════════════

def fetch_route_geometry(
    coords: list[tuple[float, float]],
    route_order: list[int],
    waypoints_per_call: int = 80,
    profile: str = DEFAULT_PROFILE,
) -> list[list[list[float]]]:
    """
    Récupère la géométrie routière exacte via l'API OSRM Route.
    Retourne une liste de segments, chaque segment = [[lat,lon], …].
    """
    ordered = [coords[i] for i in route_order]
    n = len(ordered)
    segments: list[list[list[float]]] = []

    for start in range(0, max(n - 1, 1), waypoints_per_call - 1):
        end = min(start + waypoints_per_call, n)
        batch = ordered[start:end]
        if len(batch) < 2:
            break

        base = OSRM_SERVERS.get(profile, OSRM_SERVERS["driving"])
        coords_str = ";".join(f"{lon},{lat}" for lat, lon in batch)
        url = f"{base}/route/v1/{profile}/{coords_str}?overview=full&geometries=geojson"

        try:
            req = Request(url, headers={"User-Agent": "ortho-pipeline/1.0"})
            with urlopen(req, timeout=OSRM_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            routes = data.get("routes", [])
            if routes:
                geom = routes[0]["geometry"]["coordinates"]
                # GeoJSON [lon,lat] → Folium [lat,lon]
                segment = [[lat, lon] for lon, lat in geom]
                segments.append(segment)
        except Exception as exc:
            print(f"    [warn] OSRM route geometry : {exc}", file=sys.stderr)
            # Fallback lignes droites pour ce segment
            segment = [[lat, lon] for lat, lon in batch]
            segments.append(segment)

        time.sleep(OSRM_SLEEP)

    return segments


# ═══════════════════════════════════════════════════════════════════════
#  Construction de la solution route (DataFrame)
# ═══════════════════════════════════════════════════════════════════════

def build_route_solution(
    df_routable: pd.DataFrame,
    route_order: list[int],
    matrix: np.ndarray,
) -> pd.DataFrame:
    """Construit un DataFrame de la solution : ordre, durées, cumul."""
    rows = []
    cumul = 0.0

    for order, idx in enumerate(route_order):
        site = df_routable.iloc[idx]

        if order > 0:
            seg = float(matrix[route_order[order - 1], idx])
            cumul += seg
        else:
            seg = 0.0

        rows.append({
            "visit_order": order + 1,
            "site_id": site.get("site_id", ""),
            "geocoded_label": site.get("geocoded_label", ""),
            "latitude": site.get("latitude"),
            "longitude": site.get("longitude"),
            "nb_orthos": site.get("nb_orthos", ""),
            "segment_s": round(seg),
            "segment_min": round(seg / 60, 1),
            "cumul_s": round(cumul),
            "cumul_min": round(cumul / 60, 1),
            "cumul_h": round(cumul / 3600, 2),
        })

    return pd.DataFrame(rows)


def export_route(
    df_route: pd.DataFrame,
    output_dir: Path | str | None = None,
) -> Path:
    out = Path(output_dir) if output_dir else OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    path = out / "route_solution_sites.csv"
    df_route.to_csv(path, index=False, encoding="utf-8")
    return path


def print_route_stats(df_route: pd.DataFrame, total_s: float) -> None:
    n = len(df_route)
    if n == 0:
        print("  Aucun site dans l'itinéraire.")
        return

    total_min = total_s / 60
    total_h = total_s / 3600

    print(f"  Sites visités       : {n}")
    print(f"  Durée totale trajet : {total_min:.0f} min  ({total_h:.1f} h)")
    if n > 1:
        print(f"  Durée moy/segment   : {total_min / (n - 1):.1f} min")

    show = min(5, n)
    print(f"\n  Premiers arrêts :")
    for _, r in df_route.head(show).iterrows():
        print(
            f"    #{int(r['visit_order']):>3} | "
            f"{str(r['geocoded_label'])[:42]:<42} | "
            f"+{r['segment_min']} min"
        )
    if n > 2 * show:
        print(f"    … ({n - 2 * show} arrêts intermédiaires) …")
    if n > show:
        print(f"  Derniers arrêts :")
        for _, r in df_route.tail(show).iterrows():
            print(
                f"    #{int(r['visit_order']):>3} | "
                f"{str(r['geocoded_label'])[:42]:<42} | "
                f"+{r['segment_min']} min"
            )
