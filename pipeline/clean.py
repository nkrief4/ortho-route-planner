"""
PHASE 2 — Normalisation des adresses françaises.

Nettoie, standardise et canonise les adresses sans supprimer aucune ligne.
Chaque ligne reçoit :
  - address_line_clean
  - postal_code_clean
  - city_clean
  - address_normalized  (forme géocodable : ligne + CP + ville)
  - address_key          (MD5 de address_normalized → clé de dédoublonnage)
"""

import hashlib
import re
import unicodedata

import pandas as pd

from .config import (
    CITY_ABBREVS,
    NOISE_PATTERNS,
    STREET_ABBREVS,
    STREET_TYPES_LONG,
)


# ═══════════════════════════════════════════════════════════════════════
#  Fonctions utilitaires bas-niveau
# ═══════════════════════════════════════════════════════════════════════

def _remove_accents(text: str) -> str:
    """Supprime les diacritiques (é→E, ç→C, etc.)."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _clean_spaces(text: str) -> str:
    """Espaces multiples → un seul, strip."""
    return re.sub(r"\s+", " ", text).strip()


def _remove_consecutive_dupes(text: str) -> str:
    """Supprime les mots consécutifs identiques (ex: BOULEVARD BOULEVARD)."""
    return re.sub(r"\b(\w+)\s+\1\b", r"\1", text)


def _remove_punctuation_light(text: str) -> str:
    """
    Retire la ponctuation superflue dans une adresse :
    - tirets isolés (séparateurs)  →  espace
    - points (C.H.R → CHR)        →  rien
    - virgules, parenthèses, guillemets
    Conserve les tirets intra-mot (SAINT-ETIENNE).
    """
    # Tirets servant de séparateur (entourés d'espaces)
    text = re.sub(r"\s+-\s+", " ", text)
    # Points
    text = text.replace(".", "")
    # Virgules, parenthèses, guillemets, apostrophes typographiques
    text = re.sub(r"[,;()\[\]\"'`''«»]", " ", text)
    return text


# ═══════════════════════════════════════════════════════════════════════
#  Expansion des abréviations
# ═══════════════════════════════════════════════════════════════════════

def _expand_abbreviations(text: str, abbrevs: list[tuple[str, str]]) -> str:
    """Applique une liste de (regex, remplacement) séquentiellement."""
    for pattern, replacement in abbrevs:
        text = re.sub(pattern, replacement, text)
    return text


# ═══════════════════════════════════════════════════════════════════════
#  Suppression du bruit dans address_line
# ═══════════════════════════════════════════════════════════════════════

def _remove_noise(text: str) -> str:
    """Supprime les éléments parasites (BAT, ETAGE, BP, CS, etc.)."""
    for pattern in NOISE_PATTERNS:
        text = re.sub(pattern, " ", text)
    return text


def _try_extract_street(text: str) -> str:
    """
    Tente d'extraire l'adresse « noyau » quand la ligne contient
    un préfixe parasite (nom d'établissement, résidence, etc.)
    suivi d'une vraie adresse postale.

    Heuristique :
      on cherche le pattern  <numéro> <TYPE_DE_VOIE> <suite>
      et on extrait à partir du numéro.

    Si aucun pattern reconnu → retourne le texte tel quel.
    """
    types_re = "|".join(STREET_TYPES_LONG)

    # Pattern 1 : numéro + type de voie + suite
    #   ex : "MAISON DE SANTE 2 RUE DU CHENE" → "2 RUE DU CHENE"
    m = re.search(
        rf"(\d+\s*(?:BIS|TER|QUATER|[A-D])?\s+)({types_re})\b\s+(.+)",
        text,
    )
    if m:
        return m.group(0).strip()

    # Pattern 2 : type de voie + suite (sans numéro)
    #   ex : "CLINIQUE XYZ AVENUE DU GENERAL DE GAULLE" → "AVENUE DU GENERAL DE GAULLE"
    m = re.search(rf"\b({types_re})\b\s+(.+)", text)
    if m:
        return m.group(0).strip()

    return text


# ═══════════════════════════════════════════════════════════════════════
#  Normalisation du code postal
# ═══════════════════════════════════════════════════════════════════════

def _normalize_postal_code(raw: str) -> str:
    """
    Extrait un code postal français à 5 chiffres.
    Gère les cas type '69678' (CEDEX), '75 011' (espace), etc.
    """
    raw = raw.strip()
    digits = re.sub(r"\D", "", raw)
    if len(digits) >= 5:
        return digits[:5]
    if digits:
        return digits.zfill(5)
    return ""


# ═══════════════════════════════════════════════════════════════════════
#  Normalisation de la ville
# ═══════════════════════════════════════════════════════════════════════

def _normalize_city(raw: str) -> str:
    """
    Met en majuscules, retire accents, supprime 'CEDEX …',
    et expanse ST/STE → SAINT/SAINTE.
    """
    text = raw.strip().upper()
    text = _remove_accents(text)
    # Retirer CEDEX + éventuel numéro
    text = re.sub(r"\bCEDEX\s*\d*\b", "", text)
    # Ponctuation légère
    text = _remove_punctuation_light(text)
    # Expansion SAINT / SAINTE
    text = _expand_abbreviations(text, CITY_ABBREVS)
    return _clean_spaces(text)


# ═══════════════════════════════════════════════════════════════════════
#  Normalisation de address_line
# ═══════════════════════════════════════════════════════════════════════

def _normalize_address_line(raw: str) -> str:
    """
    Pipeline complet de nettoyage d'une ligne d'adresse :
    1. majuscules + suppression accents
    2. nettoyage ponctuation
    3. expansion abréviations voie
    4. expansion ST/STE
    5. suppression bruit (BAT, ETAGE, BP…)
    6. extraction du noyau si préfixe parasite
    7. nettoyage espaces
    """
    text = raw.strip().upper()
    text = _remove_accents(text)
    text = _remove_punctuation_light(text)
    text = _expand_abbreviations(text, STREET_ABBREVS)
    text = _expand_abbreviations(text, CITY_ABBREVS)
    text = _remove_noise(text)
    text = _try_extract_street(text)
    # Supprimer les tirets en fin de ligne qui traînent
    text = re.sub(r"\s*-\s*$", "", text)
    text = _clean_spaces(text)
    # Supprimer les mots consécutifs dupliqués (ex: BD BD → BOULEVARD BOULEVARD)
    text = _remove_consecutive_dupes(text)
    return text


# ═══════════════════════════════════════════════════════════════════════
#  Fonction principale de normalisation
# ═══════════════════════════════════════════════════════════════════════

def normalize_address_fr(
    address_line: str,
    postal_code: str,
    city: str,
) -> dict[str, str]:
    """
    Normalise un triplet (adresse, CP, ville) et retourne un dict
    avec les champs nettoyés + la clé de dédoublonnage.

    Retourne :
      address_line_clean, postal_code_clean, city_clean,
      address_normalized, address_key
    """
    addr_clean = _normalize_address_line(address_line)
    cp_clean = _normalize_postal_code(postal_code)
    city_clean = _normalize_city(city)

    # Forme canonique pour géocodage
    parts = [p for p in (addr_clean, cp_clean, city_clean) if p]
    address_normalized = " ".join(parts)

    # Clé de dédoublonnage (MD5 stable)
    if address_normalized:
        address_key = hashlib.md5(address_normalized.encode("utf-8")).hexdigest()
    else:
        address_key = ""

    return {
        "address_line_clean": addr_clean,
        "postal_code_clean": cp_clean,
        "city_clean": city_clean,
        "address_normalized": address_normalized,
        "address_key": address_key,
    }


# ═══════════════════════════════════════════════════════════════════════
#  Application vectorisée sur le DataFrame
# ═══════════════════════════════════════════════════════════════════════

def apply_normalization(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ajoute les colonnes de normalisation au DataFrame.
    Aucune ligne n'est supprimée.
    """
    results = df.apply(
        lambda row: normalize_address_fr(
            row["organization_address_line"],
            row["organization_postal_code"],
            row["organization_city"],
        ),
        axis=1,
        result_type="expand",
    )
    return pd.concat([df, results], axis=1)


def print_clean_stats(df: pd.DataFrame) -> None:
    """Affiche les statistiques après normalisation."""
    n = len(df)
    n_with_key = (df["address_key"] != "").sum()
    n_empty = n - n_with_key
    n_unique_keys = df.loc[df["address_key"] != "", "address_key"].nunique()
    n_cedex_in_clean = df["city_clean"].str.contains("CEDEX").sum()

    print(f"  Lignes totales      : {n}")
    print(f"  Adresses normalisées: {n_with_key}")
    print(f"  Adresses vides      : {n_empty}")
    print(f"  Clés uniques        : {n_unique_keys}")
    print(f"  CEDEX résiduels     : {n_cedex_in_clean}")
