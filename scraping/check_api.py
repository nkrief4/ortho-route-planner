import argparse
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from env_utils import load_env_file

API_URL = "https://gateway.api.esante.gouv.fr/fhir/v2/Practitioner"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test simple de disponibilite de l'API Annuaire Sante."
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Cle API. Si absente, lit ESANTE_API_KEY depuis .env.",
    )
    parser.add_argument(
        "--qualification-code",
        default="91",
        help="Code profession pour le test (defaut: 91).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=15,
        help="Timeout HTTP en secondes (defaut: 15).",
    )
    return parser.parse_args()


def main() -> None:
    load_env_file()
    args = parse_args()

    api_key = args.api_key or os.environ.get("ESANTE_API_KEY")
    if not api_key:
        raise SystemExit("Cle API manquante. Definis ESANTE_API_KEY dans .env.")

    params = {
        "qualification-code": args.qualification_code,
        "_count": 1,
    }
    url = f"{API_URL}?{urlencode(params)}"
    headers = {"ESANTE-API-KEY": api_key}

    request = Request(url, headers=headers, method="GET")
    started = time.monotonic()

    try:
        with urlopen(request, timeout=args.timeout) as response:
            elapsed_ms = int((time.monotonic() - started) * 1000)
            status = getattr(response, "status", 200)
            payload = response.read().decode("utf-8")
            data = json.loads(payload)
            entries = len(data.get("entry", []) or [])
            first_id = ""
            if entries > 0:
                first_id = (
                    data["entry"][0]
                    .get("resource", {})
                    .get("id", "")
                )
            print(
                f"OK status={status} time_ms={elapsed_ms} entries={entries} first_id={first_id}"
            )
    except HTTPError as exc:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        print(f"ERREUR_HTTP code={exc.code} reason={exc.reason} time_ms={elapsed_ms}")
        raise SystemExit(1) from exc
    except URLError as exc:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        print(f"ERREUR_RESEAU reason={exc.reason} time_ms={elapsed_ms}")
        raise SystemExit(1) from exc
    except json.JSONDecodeError as exc:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        print(f"ERREUR_JSON message={exc} time_ms={elapsed_ms}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
