"""
Configuration globale du pipeline.

Chemins, colonnes attendues, constantes de normalisation.
"""

from pathlib import Path

# ── Chemins ──────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
INPUT_CSV = DATA_DIR / "enriched" / "contacts_orthophonistes_basic.csv"
OUTPUT_DIR = PROJECT_ROOT / "output"
CACHE_DIR = OUTPUT_DIR / "cache"

# ── Colonnes obligatoires dans le CSV source ─────────────────────────
REQUIRED_COLUMNS = [
    "rpps",
    "family_name",
    "given_names",
    "organization_name",
    "organization_address_line",
    "organization_postal_code",
    "organization_city",
]

# ── Abréviations de types de voie (ordre : plus spécifiques d'abord) ─
# Chaque tuple : (regex avec word-boundary, forme longue)
STREET_ABBREVS: list[tuple[str, str]] = [
    (r"\bBLVD\b", "BOULEVARD"),
    (r"\bBD\b", "BOULEVARD"),
    (r"\bAV\b", "AVENUE"),
    (r"\bPL\b", "PLACE"),
    (r"\bIMP\b", "IMPASSE"),
    (r"\bALL\b", "ALLEE"),
    (r"\bCHE\b", "CHEMIN"),
    (r"\bRTE\b", "ROUTE"),
    (r"\bSQ\b", "SQUARE"),
    (r"\bPASS\b", "PASSAGE"),
    (r"\bSEN\b", "SENTIER"),
    (r"\bCRS\b", "COURS"),
    (r"\bFBG\b", "FAUBOURG"),
    (r"\bTRAV\b", "TRAVERSE"),
    (r"\bQU\b", "QUAI"),
    (r"\bRPT\b", "ROND POINT"),
    (r"\bHAM\b", "HAMEAU"),
    # R en dernier : 1 seule lettre, risque de faux positif plus élevé
    (r"\bR\b", "RUE"),
]

# Abréviations de noms de communes (SAINT / SAINTE)
CITY_ABBREVS: list[tuple[str, str]] = [
    (r"\bSTE\b", "SAINTE"),  # avant ST pour éviter match partiel
    (r"\bST\b", "SAINT"),
]

# ── Patterns de bruit à supprimer dans address_line ──────────────────
# Appliqués APRÈS expansion des abréviations.
NOISE_PATTERNS: list[str] = [
    r"\bBAT(?:IMENT)?\s*[A-Z]?\d*\b",       # BAT A, BATIMENT C3
    r"\b(?:ETAGE|ETG)\s*\d*\b",              # ETAGE 2
    r"\b1ER\s*ETAGE\b",                       # 1ER ETAGE
    r"\b\d+E(?:ME)?\s*ETAGE\b",              # 2EME ETAGE
    r"\bAPP(?:T|ARTEMENT)?\s*\d*\b",         # APPT 1
    r"\bENTREE\s*[A-Z]?\d*\b",              # ENTREE E
    r"\bHALL\s*[A-Z]?\d*\b",                # HALL A4
    r"\bESC(?:ALIER)?\s*[A-Z]?\d*\b",       # ESC A
    r"\bPORTE\s*\d*\b",                      # PORTE 3
    r"\bBP\s+\d+\b",                         # BP 30039
    r"\bCS\s+\d+\b",                         # CS 51069
    r"\bCEDEX\s*\d*\b",                      # CEDEX 1
]

# Types de voie reconnus (formes longues) pour l'extraction de l'adresse noyau
STREET_TYPES_LONG = [
    "BOULEVARD", "AVENUE", "RUE", "PLACE", "ROUTE", "CHEMIN",
    "IMPASSE", "ALLEE", "ALLEES", "SQUARE", "QUAI", "COURS",
    "PASSAGE", "TRAVERSE", "FAUBOURG", "SENTIER", "ROND POINT",
    "HAMEAU", "LOTISSEMENT", "DOMAINE", "RESIDENCE",
]

# ── Géocodage ────────────────────────────────────────────────────────
GEOCODE_URL = "https://data.geopf.fr/geocodage/search"
GEOCODE_SCORE_OK = 0.70
GEOCODE_SCORE_WARN = 0.50
GEOCODE_SLEEP = 0.08          # secondes entre requêtes
GEOCODE_TIMEOUT = 10          # secondes
GEOCODE_RETRIES = 3
