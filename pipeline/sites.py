"""
PHASE 3 — Création de la table Sites et mapping orthos → site_id.

Un « site » = une adresse physique unique (identifiée par address_key).
Plusieurs orthophonistes peuvent partager le même site_id.
"""

import pandas as pd
from pathlib import Path

from .config import OUTPUT_DIR


def create_sites_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Crée un DataFrame df_sites dédoublonné sur address_key.

    Colonnes :
      site_id  (entier, 1-indexé)
      address_key
      address_normalized
      address_line_clean
      postal_code_clean
      city_clean
      nb_orthos  (nombre d'orthophonistes associés à ce site)

    Les lignes sans address_key (adresses vides) sont exclues.
    """
    # Filtrer les lignes sans clé
    df_valid = df[df["address_key"] != ""].copy()

    # Dédoublonner : garder la première occurrence de chaque adresse
    df_sites = (
        df_valid
        .groupby("address_key", sort=False)
        .agg(
            address_normalized=("address_normalized", "first"),
            address_line_clean=("address_line_clean", "first"),
            postal_code_clean=("postal_code_clean", "first"),
            city_clean=("city_clean", "first"),
            nb_orthos=("row_id", "count"),
        )
        .reset_index()
    )

    # Ajouter site_id (entier séquentiel)
    df_sites.insert(0, "site_id", range(1, len(df_sites) + 1))

    return df_sites


def merge_site_ids(
    df: pd.DataFrame,
    df_sites: pd.DataFrame,
) -> pd.DataFrame:
    """
    Ajoute la colonne site_id dans le DataFrame des orthophonistes
    via un merge sur address_key.

    Les lignes sans address_key recevront site_id = NaN.
    """
    mapping = df_sites[["address_key", "site_id"]].copy()
    df_out = df.merge(mapping, on="address_key", how="left")
    return df_out


def export_sites(
    df_sites: pd.DataFrame,
    df_orthos: pd.DataFrame,
    output_dir: Path | str | None = None,
) -> tuple[Path, Path]:
    """
    Exporte :
      - sites_clean.csv           (table des sites uniques)
      - orthos_with_site_id.csv   (toutes les lignes orthos + site_id)

    Retourne les chemins des deux fichiers.
    """
    out = Path(output_dir) if output_dir else OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    sites_path = out / "sites_clean.csv"
    orthos_path = out / "orthos_with_site_id.csv"

    df_sites.to_csv(sites_path, index=False, encoding="utf-8")
    df_orthos.to_csv(orthos_path, index=False, encoding="utf-8")

    return sites_path, orthos_path


def print_sites_stats(df_sites: pd.DataFrame, df_orthos: pd.DataFrame) -> None:
    """Affiche les statistiques de la table sites."""
    n_sites = len(df_sites)
    n_orthos = len(df_orthos)
    n_with_site = df_orthos["site_id"].notna().sum()
    n_without_site = n_orthos - n_with_site

    # Distribution du nombre d'orthos par site
    top = df_sites.nlargest(5, "nb_orthos")[["site_id", "city_clean", "nb_orthos"]]

    print(f"  Sites uniques       : {n_sites}")
    print(f"  Orthos total        : {n_orthos}")
    print(f"  Orthos avec site_id : {n_with_site}")
    print(f"  Orthos sans site_id : {n_without_site}")
    print(f"  Orthos/site moyen   : {df_sites['nb_orthos'].mean():.1f}")
    print(f"  Orthos/site max     : {df_sites['nb_orthos'].max()}")
    print(f"\n  Top 5 sites (+ peuplés) :")
    for _, row in top.iterrows():
        print(f"    site {row['site_id']:>5} | {row['city_clean']:<25} | {row['nb_orthos']} orthos")
