"""
PHASE 1 — Chargement du CSV et validation.

Charge le fichier source, vérifie les colonnes requises,
ajoute un identifiant unique (row_id) et affiche les statistiques.
Aucune ligne n'est supprimée.
"""

import pandas as pd
from pathlib import Path

from .config import INPUT_CSV, REQUIRED_COLUMNS


def load_csv(path: Path | str | None = None) -> pd.DataFrame:
    """
    Charge le CSV source en forçant tout en str pour éviter
    les conversions automatiques (codes postaux commençant par 0, etc.).

    Retourne un DataFrame avec une colonne row_id (entier, 1-indexé).
    """
    path = Path(path) if path else INPUT_CSV
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {path}")

    df = pd.read_csv(path, dtype=str, keep_default_na=False)

    # ── Validation des colonnes ──────────────────────────────────────
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"Colonnes manquantes dans le CSV : {missing}\n"
            f"Colonnes disponibles : {list(df.columns)}"
        )

    # ── Identifiant unique par ligne ─────────────────────────────────
    df.insert(0, "row_id", range(1, len(df) + 1))

    return df


def print_load_stats(df: pd.DataFrame) -> None:
    """Affiche les statistiques de base après chargement."""
    n = len(df)
    n_empty_addr = (df["organization_address_line"].str.strip() == "").sum()
    n_empty_cp = (df["organization_postal_code"].str.strip() == "").sum()
    n_empty_city = (df["organization_city"].str.strip() == "").sum()
    n_cedex = df["organization_city"].str.upper().str.contains("CEDEX").sum()
    n_unique_rpps = df["rpps"].nunique()

    print(f"  Lignes totales      : {n}")
    print(f"  RPPS uniques        : {n_unique_rpps}")
    print(f"  Adresses vides      : {n_empty_addr}")
    print(f"  CP vides            : {n_empty_cp}")
    print(f"  Villes vides        : {n_empty_city}")
    print(f"  Villes avec CEDEX   : {n_cedex}")
