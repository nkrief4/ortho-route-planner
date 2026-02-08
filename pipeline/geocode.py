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
        json.dump(cache, f, ensure_ascii=False)
    tmp.replace(cache_path)


# ═══════════════════════════════════════════════════════════════════════
#  Appel API
# ═══════════════════════════════════════════════════════════════════════

def _call_api(query: str, postcode: str = "") -> dict:
    """
    Appelle l'API de géocodage avec retry et back-off.
    Retourne le JSON brut (GeoJSON FeatureCollection).
    """
    params: dict[str, str | int] = {"q": query, "limit": 1}
    if postcode:
        params["postcode"] = postcode

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
    }


# ═══════════════════════════════════════════════════════════════════════
#  Géocodage d'un site (stratégie multi-niveaux)
# ═══════════════════════════════════════════════════════════════════════

def geocode_one(
    address_line: str,
    postal_code: str,
    city: str,
    address_normalized: str,
) -> dict:
    """
    Géocode une adresse avec 3 niveaux de fallback :
      1. address_line + postcode   (le plus précis)
      2. address_normalized seul   (si score trop bas)
      3. city + postcode           (géoloc au niveau commune)
    """
    # ── Niveau 1 : adresse + code postal ─────────────────────────────
    if address_line:
        try:
            data = _call_api(address_line, postal_code)
            result = _parse_response(data)
            if result["score"] >= 0.3:
                return result
        except Exception:
            pass

    # ── Niveau 2 : adresse normalisée complète ───────────────────────
    if address_normalized:
        try:
            data = _call_api(address_normalized)
            result = _parse_response(data)
            if result["score"] > 0:
                return result
        except Exception:
            pass

    # ── Niveau 3 : ville seule ───────────────────────────────────────
    if city:
        try:
            data = _call_api(city, postal_code)
            return _parse_response(data)
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
) -> pd.DataFrame:
    """
    Géocode chaque site de df_sites.
    Utilise un cache JSON pour éviter de re-géocoder.
    Ajoute les colonnes : geocoded_label, latitude, longitude, score, status.
    """
    cache_path = Path(cache_dir or CACHE_DIR) / "geocode_cache.json"
    cache = _load_cache(cache_path)

    results: list[dict] = []
    n = len(df_sites)
    new_count = 0
    cached_count = 0
    errors = 0

    for i, (_, row) in enumerate(df_sites.iterrows()):
        key = row["address_key"]

        if key in cache:
            results.append(cache[key])
            cached_count += 1
        else:
            try:
                result = geocode_one(
                    row["address_line_clean"],
                    row["postal_code_clean"],
                    row["city_clean"],
                    row["address_normalized"],
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
                f"new={new_count}  erreurs={errors}",
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
