import argparse
import csv
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from env_utils import load_env_file

API_BASE = "https://gateway.api.esante.gouv.fr/fhir/v2"
PRACTITIONER_URL = f"{API_BASE}/Practitioner"
PRACTITIONER_ROLE_URL = f"{API_BASE}/PractitionerRole"
ORGANIZATION_URL = f"{API_BASE}/Organization"

DEFAULT_CODES_FILE = str(Path(__file__).resolve().parent / "code_profession.json")
DEFAULT_RAW_DIR = str(Path(__file__).resolve().parent.parent / "data" / "raw")
DEFAULT_ENRICHED_DIR = str(Path(__file__).resolve().parent.parent / "data" / "enriched")
DEFAULT_RAW_COUNT = 100
DEFAULT_ROLE_COUNT = 25
DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 5
DEFAULT_PROGRESS_EVERY = 500
DEFAULT_SLEEP_MS = 100


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Pipeline eSante complet: selection d'un code profession, extraction brute "
            "puis enrichissement des contacts (PractitionerRole + Organization)."
        )
    )
    parser.add_argument("--api-key", default=os.getenv("ESANTE_API_KEY"))
    parser.add_argument("--codes-file", default=DEFAULT_CODES_FILE)
    parser.add_argument("--code", default=None, help="Code profession, ex: 40. Accepte aussi 40,91.")
    parser.add_argument("--all", action="store_true", help="Traite tous les codes du fichier.")
    parser.add_argument(
        "--list-codes",
        action="store_true",
        help="Affiche la liste des codes disponibles puis quitte.",
    )
    parser.add_argument("--raw-dir", default=DEFAULT_RAW_DIR)
    parser.add_argument("--enriched-dir", default=DEFAULT_ENRICHED_DIR)
    parser.add_argument("--raw-count", type=int, default=DEFAULT_RAW_COUNT)
    parser.add_argument("--role-count", type=int, default=DEFAULT_ROLE_COUNT)
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--max-practitioners", type=int, default=None)
    parser.add_argument("--sleep-ms", type=int, default=DEFAULT_SLEEP_MS)
    parser.add_argument("--include-empty", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force-raw", action="store_true")
    parser.add_argument("--raw-only", action="store_true")
    parser.add_argument("--enrich-only", action="store_true")
    parser.add_argument("--progress-every", type=int, default=DEFAULT_PROGRESS_EVERY)
    return parser.parse_args()


def fetch_json(
    url: str,
    headers: Dict[str, str],
    params: Optional[Dict[str, Any]] = None,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
) -> Dict[str, Any]:
    full_url = f"{url}?{urlencode(params)}" if params else url
    attempt = 0
    while True:
        request = Request(full_url, headers=headers, method="GET")
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            retryable = exc.code in (429, 500, 502, 503, 504)
            if not retryable or attempt >= retries:
                raise
            retry_after = exc.headers.get("Retry-After", "")
            wait_s = float(retry_after) if retry_after.isdigit() else float(2**attempt)
            time.sleep(wait_s)
            attempt += 1
        except URLError:
            if attempt >= retries:
                raise
            time.sleep(float(2**attempt))
            attempt += 1


def next_page_url(bundle: Dict[str, Any]) -> Optional[str]:
    for link in bundle.get("link", []):
        if link.get("relation") == "next":
            return link.get("url")
    return None


def normalize_slug(text: str) -> str:
    ascii_text = (
        unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    )
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_text).strip("_").lower()
    return slug or "profession"


def load_professions(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        raise SystemExit(f"Fichier codes professions introuvable: {path}")

    with path.open("r", encoding="utf-8") as infile:
        data = json.load(infile)

    professions: List[Dict[str, str]] = []
    seen_codes: set[str] = set()
    for item in data:
        code = str(item.get("code", "")).strip()
        label = str(item.get("profession", "")).strip()
        if not code or not label:
            continue
        if code in seen_codes:
            continue
        seen_codes.add(code)
        professions.append({"code": code, "profession": label})

    professions.sort(key=lambda row: int(row["code"]) if row["code"].isdigit() else row["code"])
    return professions


def print_profession_list(professions: List[Dict[str, str]]) -> None:
    for item in professions:
        print(f"{item['code']:>3} - {item['profession']}")


def parse_codes_arg(raw_codes: str) -> List[str]:
    codes = [piece.strip() for piece in raw_codes.split(",") if piece.strip()]
    return list(dict.fromkeys(codes))


def prompt_for_codes(valid_codes: set[str]) -> List[str]:
    while True:
        value = input("\nEntre un code profession (ou 'all', ou '40,91'): ").strip()
        if not value:
            continue
        if value.lower() == "all":
            return ["all"]
        codes = parse_codes_arg(value)
        unknown = [code for code in codes if code not in valid_codes]
        if not unknown:
            return codes
        print(f"Code(s) invalide(s): {', '.join(unknown)}")


def raw_fieldnames() -> List[str]:
    return [
        "id",
        "active",
        "family_name",
        "given_names",
        "gender",
        "birth_date",
        "phone",
        "email",
        "address_line",
        "postal_code",
        "city",
        "country",
        "identifiers",
        "last_updated",
    ]


def enriched_fieldnames() -> List[str]:
    return [
        "practitioner_id",
        "rpps",
        "family_name",
        "given_names",
        "source_email",
        "organization_id",
        "organization_name",
        "organization_phone",
        "organization_email",
        "organization_address_line",
        "organization_postal_code",
        "organization_city",
        "organization_country",
        "role_phone",
        "role_email",
        "role_start",
        "role_end",
        "role_active",
    ]


def first_name(practitioner: Dict[str, Any]) -> Tuple[str, str]:
    names = practitioner.get("name", [])
    if not names:
        return "", ""
    official = next((name for name in names if name.get("use") == "official"), names[0])
    family = official.get("family", "") or ""
    given = " ".join(official.get("given", []) or [])
    return family, given


def first_telecom(resource: Dict[str, Any]) -> Tuple[str, str]:
    phone = ""
    email = ""
    for telecom in resource.get("telecom", []):
        system = telecom.get("system")
        value = telecom.get("value", "") or ""
        if system == "phone" and not phone:
            phone = value
        if system == "email" and not email:
            email = value
    return phone, email


def first_address(resource: Dict[str, Any]) -> Tuple[str, str, str, str]:
    addresses = resource.get("address", [])
    if not addresses:
        return "", "", "", ""
    address = addresses[0]
    return (
        " ".join(address.get("line", []) or []),
        address.get("postalCode", "") or "",
        address.get("city", "") or "",
        address.get("country", "") or "",
    )


def stringify_identifiers(practitioner: Dict[str, Any]) -> str:
    values: List[str] = []
    for identifier in practitioner.get("identifier", []):
        system = identifier.get("system", "") or ""
        value = identifier.get("value", "") or ""
        if value:
            values.append(f"{system}|{value}" if system else value)
    return ";".join(values)


def parse_rpps(identifiers: str) -> str:
    for item in (identifiers or "").split(";"):
        if "|" not in item:
            continue
        system, value = item.split("|", 1)
        if "rpps" in (system or "").lower():
            return value.strip()
    return ""


def row_from_practitioner(practitioner: Dict[str, Any]) -> Dict[str, str]:
    family_name, given_names = first_name(practitioner)
    phone, email = first_telecom(practitioner)
    address_line, postal_code, city, country = first_address(practitioner)
    return {
        "id": practitioner.get("id", "") or "",
        "active": str(practitioner.get("active", "")),
        "family_name": family_name,
        "given_names": given_names,
        "gender": practitioner.get("gender", "") or "",
        "birth_date": practitioner.get("birthDate", "") or "",
        "phone": phone,
        "email": email,
        "address_line": address_line,
        "postal_code": postal_code,
        "city": city,
        "country": country,
        "identifiers": stringify_identifiers(practitioner),
        "last_updated": practitioner.get("meta", {}).get("lastUpdated", "") or "",
    }


def row_from_resources(
    practitioner: Dict[str, str],
    role: Dict[str, Any],
    organization: Dict[str, Any],
) -> Dict[str, str]:
    org_phone, org_email = first_telecom(organization)
    role_phone, role_email = first_telecom(role)
    addr_line, postal_code, city, country = first_address(organization)
    period = role.get("period", {}) if isinstance(role.get("period"), dict) else {}
    role_active = role.get("active", "")
    if isinstance(role_active, bool):
        role_active = "true" if role_active else "false"
    else:
        role_active = str(role_active)

    return {
        "practitioner_id": (practitioner.get("id", "") or "").strip(),
        "rpps": parse_rpps(practitioner.get("identifiers", "") or ""),
        "family_name": (practitioner.get("family_name", "") or "").strip(),
        "given_names": (practitioner.get("given_names", "") or "").strip(),
        "source_email": (practitioner.get("email", "") or "").strip(),
        "organization_id": organization.get("id", "") or "",
        "organization_name": organization.get("name", "") or "",
        "organization_phone": org_phone,
        "organization_email": org_email,
        "organization_address_line": addr_line,
        "organization_postal_code": postal_code,
        "organization_city": city,
        "organization_country": country,
        "role_phone": role_phone,
        "role_email": role_email,
        "role_start": period.get("start", "") or "",
        "role_end": period.get("end", "") or "",
        "role_active": role_active,
    }


def parse_reference_id(reference: str, expected_resource: str) -> str:
    if not reference:
        return ""
    marker = f"{expected_resource}/"
    if marker in reference:
        return reference.split(marker, 1)[1]
    if "/" in reference:
        return reference.rsplit("/", 1)[-1]
    return reference


def row_signature(row: Dict[str, str]) -> str:
    return "|".join(
        [
            (row.get("practitioner_id", "") or "").strip(),
            (row.get("organization_id", "") or "").strip(),
            (row.get("role_phone", "") or "").strip(),
            (row.get("role_email", "") or "").strip(),
            (row.get("role_start", "") or "").strip(),
            (row.get("role_end", "") or "").strip(),
        ]
    )


def has_usable_contact(row: Dict[str, str]) -> bool:
    return any(
        (
            row.get("organization_phone", "").strip(),
            row.get("organization_email", "").strip(),
            row.get("organization_address_line", "").strip(),
            row.get("role_phone", "").strip(),
            row.get("role_email", "").strip(),
        )
    )


def iter_raw_practitioners(
    input_path: Path, max_practitioners: Optional[int]
) -> Iterable[Dict[str, str]]:
    seen: set[str] = set()
    with input_path.open("r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            practitioner_id = (row.get("id", "") or "").strip()
            if not practitioner_id or practitioner_id in seen:
                continue
            seen.add(practitioner_id)
            yield row
            if max_practitioners is not None and len(seen) >= max_practitioners:
                return


def fetch_roles_and_orgs(
    practitioner_id: str, headers: Dict[str, str], role_count: int
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    roles: List[Dict[str, Any]] = []
    orgs: Dict[str, Dict[str, Any]] = {}
    next_url: Optional[str] = PRACTITIONER_ROLE_URL
    next_params: Optional[Dict[str, Any]] = {
        "practitioner": practitioner_id,
        "active": "true",
        "_include": "PractitionerRole:organization",
        "_count": role_count,
    }

    while next_url:
        bundle = fetch_json(next_url, headers=headers, params=next_params)
        for entry in bundle.get("entry", []):
            resource = entry.get("resource", {})
            rtype = resource.get("resourceType")
            if rtype == "PractitionerRole":
                roles.append(resource)
            elif rtype == "Organization":
                org_id = resource.get("id", "")
                if org_id:
                    orgs[org_id] = resource
        next_url = next_page_url(bundle)
        next_params = None
    return roles, orgs


def fetch_organization_by_id(
    org_id: str, headers: Dict[str, str], cache: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    if not org_id:
        return {}
    if org_id in cache:
        return cache[org_id]

    url = f"{ORGANIZATION_URL}/{quote(org_id)}"
    resource = fetch_json(url, headers=headers, params=None)
    if resource.get("resourceType") == "Organization":
        cache[org_id] = resource
    else:
        cache[org_id] = {}
    return cache[org_id]


def load_resume_state(
    output: Path, expected_fields: List[str]
) -> Tuple[set[str], set[str], int]:
    practitioners: set[str] = set()
    signatures: set[str] = set()
    rows = 0

    if not output.exists() or output.stat().st_size == 0:
        return practitioners, signatures, rows

    with output.open("r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        actual_fields = list(reader.fieldnames or [])
        if actual_fields != expected_fields:
            preview_rows = list(reader)
            if len(preview_rows) == 0:
                return practitioners, signatures, -1
            raise SystemExit(
                "Schema CSV incompatible pour --resume.\n"
                f"Attendu: {expected_fields}\n"
                f"Actuel: {actual_fields}\n"
                "Utilise un autre --output ou vide ce fichier."
            )
        for row in reader:
            rows += 1
            pid = (row.get("practitioner_id", "") or "").strip()
            if pid:
                practitioners.add(pid)
            signatures.add(row_signature(row))
    return practitioners, signatures, rows


def export_raw_practitioners(
    code: str,
    raw_output: Path,
    headers: Dict[str, str],
    raw_count: int,
    max_pages: Optional[int],
    max_practitioners: Optional[int],
    progress_every: int,
) -> int:
    params: Dict[str, Any] = {"qualification-code": code, "_count": raw_count}
    next_url: Optional[str] = PRACTITIONER_URL
    next_params: Optional[Dict[str, Any]] = params
    pages = 0
    rows_written = 0
    seen_ids: set[str] = set()

    fields = raw_fieldnames()
    raw_output.parent.mkdir(parents=True, exist_ok=True)
    with raw_output.open("w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fields)
        writer.writeheader()

        while next_url and (max_pages is None or pages < max_pages):
            bundle = fetch_json(next_url, headers=headers, params=next_params)
            for entry in bundle.get("entry", []):
                resource = entry.get("resource", {})
                if resource.get("resourceType") != "Practitioner":
                    continue
                practitioner_id = (resource.get("id", "") or "").strip()
                if not practitioner_id or practitioner_id in seen_ids:
                    continue
                writer.writerow(row_from_practitioner(resource))
                seen_ids.add(practitioner_id)
                rows_written += 1
                if max_practitioners is not None and rows_written >= max_practitioners:
                    return rows_written
                if progress_every > 0 and rows_written % progress_every == 0:
                    print(
                        f"[raw] code={code} pages={pages + 1} praticiens={rows_written}",
                        file=sys.stderr,
                    )
            next_url = next_page_url(bundle)
            next_params = None
            pages += 1
    return rows_written


def enrich_from_raw_file(
    raw_input: Path,
    enriched_output: Path,
    headers: Dict[str, str],
    role_count: int,
    include_empty: bool,
    resume: bool,
    max_practitioners: Optional[int],
    sleep_ms: int,
    progress_every: int,
) -> Dict[str, int]:
    fields = enriched_fieldnames()
    enriched_output.parent.mkdir(parents=True, exist_ok=True)

    resume_practitioners: set[str] = set()
    resume_signatures: set[str] = set()
    resume_rows = 0
    reset_output_for_schema = False
    if resume:
        resume_practitioners, resume_signatures, resume_rows = load_resume_state(
            enriched_output, fields
        )
        if resume_rows == -1:
            reset_output_for_schema = True
            resume_rows = 0
            print(
                "[resume] fichier de sortie incompatible mais vide, reinitialisation du header.",
                file=sys.stderr,
            )
        print(
            f"[resume] lignes_existantes={resume_rows} praticiens_existants={len(resume_practitioners)}",
            file=sys.stderr,
        )

    file_mode = (
        "a"
        if resume
        and enriched_output.exists()
        and enriched_output.stat().st_size > 0
        and not reset_output_for_schema
        else "w"
    )

    org_cache: Dict[str, Dict[str, Any]] = {}
    sleep_seconds = max(sleep_ms, 0) / 1000.0

    processed = 0
    written = 0
    with_contact = 0
    without_role = 0
    errors = 0
    skipped_practitioners = 0
    skipped_duplicates = 0

    with enriched_output.open(file_mode, newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fields)
        if file_mode == "w":
            writer.writeheader()

        for practitioner in iter_raw_practitioners(raw_input, max_practitioners):
            practitioner_id = (practitioner.get("id", "") or "").strip()
            if resume and practitioner_id in resume_practitioners:
                skipped_practitioners += 1
                continue

            processed += 1
            try:
                roles, orgs = fetch_roles_and_orgs(practitioner_id, headers, role_count)
            except (HTTPError, URLError, json.JSONDecodeError) as exc:
                errors += 1
                print(f"[warn] practitioner={practitioner_id} erreur={exc}", file=sys.stderr)
                continue

            if not roles:
                without_role += 1
                if include_empty:
                    row = row_from_resources(practitioner, {}, {})
                    sig = row_signature(row)
                    if resume and sig in resume_signatures:
                        skipped_duplicates += 1
                    else:
                        writer.writerow(row)
                        written += 1
                        if resume:
                            resume_signatures.add(sig)
                continue

            for role in roles:
                org_ref = (
                    role.get("organization", {}).get("reference", "")
                    if isinstance(role.get("organization"), dict)
                    else ""
                )
                org_id = parse_reference_id(org_ref, "Organization")
                organization = orgs.get(org_id, {})
                if not organization and org_id:
                    try:
                        organization = fetch_organization_by_id(org_id, headers, org_cache)
                    except (HTTPError, URLError, json.JSONDecodeError):
                        organization = {}

                row = row_from_resources(practitioner, role, organization)
                if not include_empty and not has_usable_contact(row):
                    continue

                sig = row_signature(row)
                if resume and sig in resume_signatures:
                    skipped_duplicates += 1
                    continue

                writer.writerow(row)
                written += 1
                if resume:
                    resume_signatures.add(sig)
                if has_usable_contact(row):
                    with_contact += 1

            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
            if progress_every > 0 and processed % progress_every == 0:
                print(
                    f"[enrich] praticiens={processed} lignes={written} erreurs={errors}",
                    file=sys.stderr,
                )

    return {
        "processed": processed,
        "written": written,
        "with_contact": with_contact,
        "without_role": without_role,
        "errors": errors,
        "skipped_practitioners": skipped_practitioners,
        "skipped_duplicates": skipped_duplicates,
    }


def build_output_paths(raw_dir: Path, enriched_dir: Path, code: str, label: str) -> Tuple[Path, Path]:
    slug = normalize_slug(label)
    raw_path = raw_dir / f"{slug}_{code}.csv"
    enriched_path = enriched_dir / f"contacts_{slug}_{code}.csv"
    return raw_path, enriched_path


def process_profession(
    code: str,
    label: str,
    args: argparse.Namespace,
    headers: Dict[str, str],
) -> None:
    raw_dir = Path(args.raw_dir)
    enriched_dir = Path(args.enriched_dir)
    raw_path, enriched_path = build_output_paths(raw_dir, enriched_dir, code, label)

    print(f"\n=== {code} - {label} ===")
    print(f"raw: {raw_path}")
    print(f"enriched: {enriched_path}")

    if args.raw_only and args.enrich_only:
        raise SystemExit("--raw-only et --enrich-only ne peuvent pas etre utilises ensemble.")

    run_raw = not args.enrich_only
    run_enrich = not args.raw_only

    if run_raw:
        should_skip_raw = (
            args.resume and not args.force_raw and raw_path.exists() and raw_path.stat().st_size > 0
        )
        if should_skip_raw:
            print("[resume] extraction brute sautee (fichier deja present).")
        else:
            print("[start] extraction brute...")
            started = time.time()
            rows_raw = export_raw_practitioners(
                code=code,
                raw_output=raw_path,
                headers=headers,
                raw_count=args.raw_count,
                max_pages=args.max_pages,
                max_practitioners=args.max_practitioners,
                progress_every=args.progress_every,
            )
            elapsed = time.time() - started
            print(f"[done] raw rows={rows_raw} duree={elapsed:.1f}s")

    if run_enrich:
        if not raw_path.exists():
            raise SystemExit(
                f"Fichier brut introuvable pour enrichissement: {raw_path}\n"
                "Lance sans --enrich-only ou genere d'abord le brut."
            )
        print("[start] enrichissement...")
        started = time.time()
        stats = enrich_from_raw_file(
            raw_input=raw_path,
            enriched_output=enriched_path,
            headers=headers,
            role_count=args.role_count,
            include_empty=args.include_empty,
            resume=args.resume,
            max_practitioners=args.max_practitioners,
            sleep_ms=args.sleep_ms,
            progress_every=args.progress_every,
        )
        elapsed = time.time() - started
        print(
            "[done] enrich "
            f"praticiens={stats['processed']} lignes={stats['written']} "
            f"avec_contact={stats['with_contact']} erreurs={stats['errors']} "
            f"skip_praticiens_resume={stats['skipped_practitioners']} "
            f"skip_lignes_doublons={stats['skipped_duplicates']} "
            f"duree={elapsed:.1f}s"
        )


def main() -> None:
    load_env_file()
    args = parse_args()

    if not args.api_key:
        raise SystemExit("Cle API manquante. Definis ESANTE_API_KEY dans .env ou --api-key.")
    if args.raw_count <= 0:
        raise SystemExit("--raw-count doit etre > 0.")
    if args.role_count <= 0:
        raise SystemExit("--role-count doit etre > 0.")

    professions = load_professions(Path(args.codes_file))
    if not professions:
        raise SystemExit("Aucune profession chargee depuis le fichier de codes.")

    code_to_label = {item["code"]: item["profession"] for item in professions}
    valid_codes = set(code_to_label.keys())

    if args.list_codes:
        print_profession_list(professions)
        return

    selected_codes: List[str]
    if args.all:
        selected_codes = [item["code"] for item in professions]
    elif args.code:
        selected_codes = parse_codes_arg(args.code)
        if not selected_codes:
            raise SystemExit("Aucun code fourni via --code.")
        unknown = [code for code in selected_codes if code not in valid_codes]
        if unknown:
            raise SystemExit(f"Code(s) inconnu(s): {', '.join(unknown)}")
    else:
        print("\nCodes professions disponibles:")
        print_profession_list(professions)
        entered = prompt_for_codes(valid_codes)
        if len(entered) == 1 and entered[0] == "all":
            selected_codes = [item["code"] for item in professions]
        else:
            selected_codes = entered

    headers = {"ESANTE-API-KEY": args.api_key}
    global_start = time.time()
    for code in selected_codes:
        label = code_to_label[code]
        try:
            process_profession(code, label, args, headers)
        except HTTPError as exc:
            print(
                f"[error] code={code} HTTP {exc.code}: {exc.reason}",
                file=sys.stderr,
            )
        except URLError as exc:
            print(
                f"[error] code={code} erreur reseau: {exc.reason}",
                file=sys.stderr,
            )

    total_elapsed = time.time() - global_start
    print(f"\nTermine. codes={len(selected_codes)} duree_totale={total_elapsed:.1f}s")


if __name__ == "__main__":
    main()
