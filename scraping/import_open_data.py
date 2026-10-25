"""
Mise a jour de la base a partir de l'extraction open data de l'Annuaire Sante.

Source : "Annuaire Sante - Extractions des donnees en libre acces des professionnels
intervenant dans le systeme de Sante (RPPS) - Format Zip", publiee par l'ANS sur
data.gouv.fr et mise a jour regulierement. Aucune cle API n'est necessaire.

Le fichier PS_LibreAcces_Personne_activite contient une ligne par activite
(professionnel x structure d'exercice). On garde la profession demandee et on
ecrit le meme schema CSV que scraping/main.py, lu ensuite par app.py.

L'adresse MSSante personnelle (colonne source_email) vient d'un second jeu de
l'ANS : "Annuaire Sante - Extraction des BAL MSSante - Format Zip".

Usage :
    venv/bin/python scraping/import_open_data.py               # dernieres extractions
    venv/bin/python scraping/import_open_data.py --zip data/raw/PS_LibreAcces_XXX.zip \
        --mssante-zip data/raw/Extraction_Correspondance_MSSante_XXX.zip
"""

import argparse
import csv
import io
import json
import sys
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List
from urllib.request import Request, urlopen

from main import enriched_fieldnames, has_usable_contact

_ROOT = Path(__file__).resolve().parent.parent
DATASET_API = (
    "https://www.data.gouv.fr/api/1/datasets/"
    "annuaire-sante-extractions-des-donnees-en-libre-acces-des-professionnels-"
    "intervenant-dans-le-systeme-de-sante-rpps-format-zip/"
)
MSSANTE_DATASET_API = (
    "https://www.data.gouv.fr/api/1/datasets/annuaire-sante-extraction-des-bal-mssante-format-zip/"
)
DEFAULT_RAW_DIR = _ROOT / "data" / "raw"
DEFAULT_OUTPUT = _ROOT / "data" / "enriched" / "contacts_orthophonistes_basic.csv"
ACTIVITY_FILE_PREFIX = "PS_LibreAcces_Personne_activite"
# Colonnes en plus du schema de scraping/main.py : commune officielle (code INSEE et
# libelle), plus fiables que la ville saisie dans l'adresse (CEDEX, variantes, erreurs)
EXTRA_FIELDS = ["organization_city_code", "organization_commune"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Importe les professionnels d'une profession depuis l'open data Annuaire Sante."
    )
    parser.add_argument("--code", default="91", help="Code profession (defaut: 91, orthophoniste).")
    parser.add_argument("--zip", default=None, help="ZIP deja telecharge (sinon: derniere version).")
    parser.add_argument(
        "--mssante-zip", default=None, help="ZIP MSSante deja telecharge (sinon: derniere version)."
    )
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def latest_zip_resource(dataset_api: str) -> Dict[str, str]:
    request = Request(dataset_api, headers={"User-Agent": "ortho-route-planner"})
    with urlopen(request, timeout=30) as response:
        dataset = json.loads(response.read().decode("utf-8"))
    zips = [r for r in dataset.get("resources", []) if r.get("format", "").lower() == "zip"]
    if not zips:
        raise SystemExit("Aucun ZIP trouve sur la page data.gouv.fr du jeu de donnees.")
    return max(zips, key=lambda r: r.get("last_modified", ""))


def download_latest_zip(dataset_api: str, raw_dir: Path) -> Path:
    resource = latest_zip_resource(dataset_api)
    target = raw_dir / resource["title"]
    if target.exists() and target.stat().st_size == resource.get("filesize"):
        print(f"[zip] deja present : {target}")
        return target

    size_mb = (resource.get("filesize") or 0) / 1e6
    print(f"[zip] telechargement {resource['title']} ({size_mb:.0f} Mo)...")
    raw_dir.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".part")
    request = Request(resource["url"], headers={"User-Agent": "ortho-route-planner"})
    with urlopen(request, timeout=60) as response, tmp.open("wb") as outfile:
        while chunk := response.read(1 << 20):
            outfile.write(chunk)
    tmp.replace(target)
    return target


def iter_activities(zip_path: Path, code: str) -> Iterable[Dict[str, str]]:
    with zipfile.ZipFile(zip_path) as archive:
        members = [n for n in archive.namelist() if Path(n).name.startswith(ACTIVITY_FILE_PREFIX)]
        if not members:
            raise SystemExit(f"{ACTIVITY_FILE_PREFIX}*.txt absent de {zip_path}")
        with archive.open(members[0]) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8", newline="")
            reader = csv.DictReader(text, delimiter="|", quoting=csv.QUOTE_NONE)
            for row in reader:
                if (row.get("Code profession") or "").strip() == code:
                    yield {k: (v or "").strip() for k, v in row.items() if k}


def load_mssante(zip_path: Path, code: str) -> Dict[str, str]:
    """RPPS -> adresse MSSante personnelle (BAL de type PER).

    Si un professionnel a plusieurs BAL, on prefere une adresse MSSante native a une
    passerelle (ex: @interop-mssante.apicrypt.org), puis l'ordre alphabetique.
    """
    addresses: Dict[str, List[str]] = {}
    with zipfile.ZipFile(zip_path) as archive:
        with archive.open(archive.namelist()[0]) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8", newline="")
            for row in csv.DictReader(text, delimiter="|", quoting=csv.QUOTE_NONE):
                if row.get("Type de BAL") != "PER" or row.get("Code Profession") != code:
                    continue
                rpps = (row.get("Identifiant PP") or "").strip()
                address = (row.get("Adresse BAL") or "").strip()
                if rpps and address:
                    addresses.setdefault(rpps, []).append(address)
    return {
        rpps: min(found, key=lambda a: ("interop" in a.lower(), a.lower()))
        for rpps, found in addresses.items()
    }


def _join(*parts: str) -> str:
    return " ".join(p for p in parts if p)


def row_from_activity(act: Dict[str, str], mssante: Dict[str, str]) -> Dict[str, str]:
    """Convertit une ligne open data au schema de scraping/main.py.

    L'adresse et la ville sont reconstruites comme dans l'API FHIR (ex: "662 R DES
    JONCHERES", "ST LO") pour que les cles du cache de geocodage restent valables.
    """
    def coord(field: str) -> str:
        return act.get(f"{field} (coord. structure)", "")

    address_line = _join(
        coord("Complément destinataire"),
        coord("Complément point géographique"),
        coord("Numéro Voie"),
        coord("Indice répétition voie"),
        coord("Code type de voie"),
        coord("Libellé Voie"),
        coord("Mention distribution"),
    )
    postal_code = coord("Code postal")
    # "Bureau cedex" = "62008 ARRAS CEDEX" : on retire le code postal en tete
    bureau = coord("Bureau cedex")
    city = bureau.split(" ", 1)[1].strip() if bureau[:5].isdigit() and " " in bureau else bureau
    city = city or coord("Libellé commune")

    return {
        "practitioner_id": act.get("Identification nationale PP", ""),
        "rpps": act.get("Identifiant PP", ""),
        "family_name": act.get("Nom d'exercice", ""),
        "given_names": act.get("Prénom d'exercice", ""),
        "source_email": mssante.get(act.get("Identifiant PP", ""), ""),
        "organization_id": act.get("Identifiant technique de la structure", ""),
        "organization_name": act.get("Raison sociale site", "") or act.get("Enseigne commerciale site", ""),
        "organization_phone": coord("Téléphone") or coord("Téléphone 2"),
        "organization_email": coord("Adresse e-mail"),
        "organization_address_line": address_line,
        "organization_postal_code": postal_code,
        "organization_city": city,
        "organization_country": coord("Libellé pays"),
        "role_phone": "",
        "role_email": "",
        "role_start": "",
        "role_end": "",
        "role_active": "true",
        "organization_city_code": coord("Code commune"),
        "organization_commune": coord("Libellé commune"),
    }


def main() -> None:
    args = parse_args()
    raw_dir = Path(args.raw_dir)
    zip_path = Path(args.zip) if args.zip else download_latest_zip(DATASET_API, raw_dir)
    mssante_zip = (
        Path(args.mssante_zip) if args.mssante_zip
        else download_latest_zip(MSSANTE_DATASET_API, raw_dir)
    )
    mssante = load_mssante(mssante_zip, args.code)
    output = Path(args.output)
    fields: List[str] = enriched_fieldnames() + EXTRA_FIELDS

    seen: set[tuple] = set()
    read = written = no_contact = duplicates = 0
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fields)
        writer.writeheader()
        for activity in iter_activities(zip_path, args.code):
            read += 1
            row = row_from_activity(activity, mssante)
            if not has_usable_contact(row):
                no_contact += 1
                continue
            key = tuple(row[f] for f in fields)
            if key in seen:
                duplicates += 1
                continue
            seen.add(key)
            writer.writerow(row)
            written += 1
    tmp.replace(output)

    rpps = {k[fields.index("rpps")] for k in seen}
    print(
        f"[done] code={args.code} activites={read} ecrites={written} "
        f"sans_coordonnees={no_contact} doublons={duplicates} rpps_uniques={len(rpps)} "
        f"avec_mssante={len(rpps & mssante.keys())}"
    )
    print(f"[done] {output}")


if __name__ == "__main__":
    sys.exit(main())
