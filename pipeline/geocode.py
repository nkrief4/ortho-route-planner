"""
PHASE 4 — Géocodage des sites via l'API publique française.

Utilise https://data.geopf.fr/geocodage/search (API BAN / IGN).
Implémente :
  - cache disque (JSON) pour éviter les requêtes redondantes
  - throttle (sleep entre requêtes)
  - retry avec back-off exponentiel
  - stratégie de fallback (adresse → adresse complète → ville seule)
  - scoring : OK ≥ 0.7 / WARNING ≥ 0.5 / FAILED < 0.5
"""

import json
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from .config import (
    CACHE_DIR,
    GEOCODE_RETRIES,
    GEOCODE_SCORE_OK,
    GEOCODE_SCORE_WARN,
    GEOCODE_SLEEP,
    GEOCODE_TIMEOUT,
    GEOCODE_URL,
)


# ═══════════════════════════════════════════════════════════════════════
#  Cache disque
# ═══════════════════════════════════════════════════════════════════════

def _load_cache(cache_path: Path) -> dict:
    if cache_path.exists():
        with cache_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_cache(cache: dict, cache_path: Path) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache_path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=4)  # indenté : diffs git lisibles
    tmp.replace(cache_path)


# ═══════════════════════════════════════════════════════════════════════
#  Appel API
# ═══════════════════════════════════════════════════════════════════════

def _call_api(query: str, postcode: str = "", **filters: str) -> dict:
    """
    Appelle l'API de géocodage avec retry et back-off.
    filters : autres filtres de l'API (citycode, type…), ignorés s'ils sont vides.
    Retourne le JSON brut (GeoJSON FeatureCollection).
    """
    params: dict[str, str | int] = {"q": query, "limit": 1}
    if postcode:
        params["postcode"] = postcode
    params.update({k: v for k, v in filters.items() if v})

    url = f"{GEOCODE_URL}?{urlencode(params)}"

    for attempt in range(GEOCODE_RETRIES):
        try:
            req = Request(url, headers={"User-Agent": "ortho-pipeline/1.0"})
            with urlopen(req, timeout=GEOCODE_TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 429 or exc.code >= 500:
                time.sleep(2 ** attempt)
                continue
            raise
        except (URLError, TimeoutError, OSError):
            if attempt >= GEOCODE_RETRIES - 1:
                raise
            time.sleep(2 ** attempt)

    return {}


def _parse_response(data: dict) -> dict:
    """Parse le GeoJSON et retourne un dict plat."""
    features = data.get("features", [])
    if not features:
        return {
            "geocoded_label": "",
            "latitude": None,
            "longitude": None,
            "score": 0.0,
            "status": "FAILED",
        }

    feat = features[0]
    props = feat.get("properties", {})
    coords = feat.get("geometry", {}).get("coordinates", [None, None])
    score = float(props.get("score", 0))

    if score >= GEOCODE_SCORE_OK:
        status = "OK"
    elif score >= GEOCODE_SCORE_WARN:
        status = "WARNING"
    else:
        status = "FAILED"

    return {
        "geocoded_label": props.get("label", ""),
        "latitude": coords[1],
        "longitude": coords[0],
        "score": round(score, 4),
        "status": status,
        "postcode": props.get("postcode", ""),
        "citycode": props.get("citycode", ""),
    }


def _department(code: str) -> str:
    """Département d'un code postal ou INSEE : 2 chiffres, 3 en outre-mer (97x)."""
    code = code.strip() if isinstance(code, str) else ""
    if code[:2] in ("2A", "2B"):
        return "20"
    return code[:3] if code.startswith("97") else code[:2]


def result_department(result: dict) -> str:
    """Département d'un résultat de géocodage (y compris les entrées du cache
    antérieures à l'ajout du champ postcode, via le CP du libellé)."""
    postcode = result.get("postcode")
    if not isinstance(postcode, str) or not postcode:
        label = result.get("geocoded_label")
        match = re.search(r"\b(\d{5})\b", label if isinstance(label, str) else "")
        postcode = match.group(1) if match else ""
    return _department(postcode)


# ═══════════════════════════════════════════════════════════════════════
#  Géocodage d'un site (stratégie multi-niveaux)
# ═══════════════════════════════════════════════════════════════════════

def geocode_one(
    address_line: str,
    postal_code: str,
    city: str,
    address_normalized: str,
    city_code: str = "",
) -> dict:
    """
    Géocode une adresse avec 3 niveaux de fallback :
      1. address_line filtrée sur la commune (code INSEE), puis sur le code postal.
         Le code INSEE marche aussi pour les CP CEDEX, que l'API ne connaît pas.
      2. address_normalized sans filtre, accepté seulement dans la bonne commune
         (ou le bon département si le code INSEE est inconnu) : sinon on obtient une
         rue homonyme d'une autre ville (Marseille 13015 → Paris 75015)
      3. commune seule : centre de la commune, statut WARNING au mieux

    Tout résultat retenu est dans la bonne commune : un score faible (< 0.5) donne
    WARNING (« position approximative ») et non FAILED, pour garder le cabinet
    dans les itinéraires. FAILED = aucune position trouvée.
    """
    expected_dept = _department(postal_code or city_code)

    def same_place(result: dict) -> bool:
        if city_code:
            return result.get("citycode") == city_code
        return not expected_dept or result_department(result) == expected_dept

    def approximate(result: dict) -> dict:
        if result["status"] == "FAILED":
            result["status"] = "WARNING"
        return result

    # ── Niveau 1 : adresse + commune ou code postal ──────────────────
    if address_line:
        for filters in ({"citycode": city_code}, {"postcode": postal_code}):
            if not any(filters.values()):
                continue
            try:
                result = _parse_response(_call_api(address_line, **filters))
                if result["score"] >= 0.3:
                    return approximate(result)
            except Exception:
                pass

    # ── Niveau 2 : adresse normalisée complète ───────────────────────
    if address_normalized:
        try:
            result = _parse_response(_call_api(address_normalized))
            if result["score"] > 0 and same_place(result):
                return approximate(result)
        except Exception:
            pass

    # ── Niveau 3 : ville seule ───────────────────────────────────────
    if city or city_code:
        for query, filters in (
            (city, {"citycode": city_code, "type": "municipality"}),
            (city, {"postcode": postal_code}),
        ):
            if not filters.get("citycode") and not filters.get("postcode"):
                continue
            try:
                result = _parse_response(_call_api(query or city_code, **filters))
                if result["score"] > 0:
                    # Position approximative (centre de la commune) : jamais OK
                    result["status"] = "WARNING"
                    return result
            except Exception:
                pass

    return {
        "geocoded_label": "",
        "latitude": None,
        "longitude": None,
        "score": 0.0,
        "status": "FAILED",
    }


# ═══════════════════════════════════════════════════════════════════════
#  Géocodage de tous les sites (avec cache et progression)
# ═══════════════════════════════════════════════════════════════════════

def geocode_sites(
    df_sites: pd.DataFrame,
    cache_dir: Path | str | None = None,
    cache_only: bool = False,
) -> pd.DataFrame:
    """
    Géocode chaque site de df_sites.
    Utilise un cache JSON pour éviter de re-géocoder.
    Avec cache_only=True, aucun appel API : les sites absents du cache sont PENDING.
    Ajoute les colonnes : geocoded_label, latitude, longitude, score, status.
    """
    cache_path = Path(cache_dir or CACHE_DIR) / "geocode_cache.json"
    cache = _load_cache(cache_path)

    results: list[dict] = []
    n = len(df_sites)
    new_count = 0
    cached_count = 0
    pending_count = 0
    errors = 0

    for i, (_, row) in enumerate(df_sites.iterrows()):
        key = row["address_key"]

        if key in cache:
            results.append(cache[key])
            cached_count += 1
        elif cache_only:
            results.append({
                "geocoded_label": "",
                "latitude": None,
                "longitude": None,
                "score": 0.0,
                "status": "PENDING",
            })
            pending_count += 1
        else:
            try:
                result = geocode_one(
                    row["address_line_clean"],
                    row["postal_code_clean"],
                    row["city_clean"],
                    row["address_normalized"],
                    city_code=row.get("city_code", ""),
                )
            except Exception as exc:
                print(f"    [erreur] site {key}: {exc}", file=sys.stderr)
                result = {
                    "geocoded_label": "",
                    "latitude": None,
                    "longitude": None,
                    "score": 0.0,
                    "status": "FAILED",
                }
                errors += 1

            cache[key] = result
            results.append(result)
            new_count += 1

            if new_count % 100 == 0:
                _save_cache(cache, cache_path)

            time.sleep(GEOCODE_SLEEP)

        # Progression
        done = i + 1
        if done % 500 == 0 or done == n:
            print(
                f"    [{done}/{n}]  cache={cached_count}  "
                f"new={new_count}  pending={pending_count}  erreurs={errors}",
            )

    if new_count > 0:
        _save_cache(cache, cache_path)

    df_results = pd.DataFrame(results, index=df_sites.index)
    return pd.concat([df_sites, df_results], axis=1)


def export_geocoded(
    df: pd.DataFrame,
    output_dir: Path | str | None = None,
) -> Path:
    from .config import OUTPUT_DIR
    out = Path(output_dir) if output_dir else OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    path = out / "sites_geocoded.csv"
    df.to_csv(path, index=False, encoding="utf-8")
    return path


def print_geocode_stats(df: pd.DataFrame) -> None:
    n = len(df)
    if n == 0:
        print("  Aucun site à géocoder.")
        return

    n_ok = (df["status"] == "OK").sum()
    n_warn = (df["status"] == "WARNING").sum()
    n_fail = (df["status"] == "FAILED").sum()

    print(f"  Sites total         : {n}")
    print(f"  OK    (score >= 0.7): {n_ok}  ({100 * n_ok / n:.1f}%)")
    print(f"  WARN  (0.5 – 0.7)  : {n_warn}  ({100 * n_warn / n:.1f}%)")
    print(f"  FAILED (< 0.5)     : {n_fail}  ({100 * n_fail / n:.1f}%)")

    valid = df[df["status"].isin(["OK", "WARNING"])]
    if len(valid) > 0:
        print(f"  Score moyen (OK+W)  : {valid['score'].mean():.3f}")
