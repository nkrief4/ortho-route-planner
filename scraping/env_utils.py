import os
from pathlib import Path
from typing import Optional


def _strip_optional_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def load_env_file(filename: str = ".env") -> Optional[Path]:
    candidates = [
        Path.cwd() / filename,
        Path(__file__).resolve().parent / filename,
    ]

    loaded_from: Optional[Path] = None
    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if not path.exists():
            continue
        loaded_from = path
        with path.open("r", encoding="utf-8") as env_file:
            for raw_line in env_file:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[len("export ") :].strip()
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = _strip_optional_quotes(value)
                if not key:
                    continue
                os.environ.setdefault(key, value)
        break

    return loaded_from
