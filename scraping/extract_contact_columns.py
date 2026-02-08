import argparse
import csv
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = str(_ROOT / "data" / "enriched" / "contacts_orthophonistes_basic.csv")
DEFAULT_OUTPUT = str(_ROOT / "data" / "exports" / "annuaire_orthophonistes_contacts.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extrait des colonnes de contact d'un CSV enrichi d'orthophonistes "
            "dans un ordre specifique."
        )
    )
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Fichier source introuvable: {input_path}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "family_name",
        "given_name",
        "organization_email",
        "organization_address_line",
        "organization_postal_code",
        "organization_city",
        "organization_phone",
    ]

    with input_path.open("r", newline="", encoding="utf-8") as infile, output_path.open(
        "w", newline="", encoding="utf-8"
    ) as outfile:
        reader = csv.DictReader(infile)
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        rows = 0
        for row in reader:
            writer.writerow(
                {
                    "family_name": (row.get("family_name", "") or "").strip(),
                    "given_name": (row.get("given_names", "") or "").strip(),
                    "organization_email": (
                        row.get("organization_email", "") or ""
                    ).strip(),
                    "organization_address_line": (
                        row.get("organization_address_line", "") or ""
                    ).strip(),
                    "organization_postal_code": (
                        row.get("organization_postal_code", "") or ""
                    ).strip(),
                    "organization_city": (row.get("organization_city", "") or "").strip(),
                    "organization_phone": (
                        row.get("organization_phone", "") or ""
                    ).strip(),
                }
            )
            rows += 1

    print(f"{rows} lignes exportees dans {output_path}")


if __name__ == "__main__":
    main()
