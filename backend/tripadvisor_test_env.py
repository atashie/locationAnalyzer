"""Credential loading for the TripAdvisor diagnostic scripts in this directory.

Those scripts talk to the live TripAdvisor Content API, so they need a real key. The key must
never sit in a file git tracks: it lives in `backend/.env` — which `.gitignore` covers — as
`TRIPADVISOR_API_KEY`, and `load_api_key()` is the only way these scripts should obtain it.

`masked()` exists because several of the scripts print their request parameters. Printing the key
puts it into terminal scrollback, captured logs and pasted output, which is the same disclosure as
committing it, just slower.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ENV_VAR = "TRIPADVISOR_API_KEY"

#: Explicit, so the scripts work from the repo root as well as from `backend/`. `load_dotenv`
#: searches upward from the working directory by default, which would miss `backend/.env`.
ENV_FILE = Path(__file__).resolve().parent / ".env"


def load_api_key() -> str:
    """The TripAdvisor key from the environment, or exit saying how to supply it.

    An already-exported variable wins: `load_dotenv` does not override the environment.
    """
    load_dotenv(ENV_FILE)
    key = os.environ.get(ENV_VAR, "").strip()
    if not key:
        sys.exit(
            f"{ENV_VAR} is not set.\n"
            f"Put it in {ENV_FILE} (git ignores that file) as\n"
            f"    {ENV_VAR}=<your key>\n"
            "or export it in this shell. See .env.example for the full list."
        )
    return key


def masked(params: dict[str, Any], *, field: str = "key") -> dict[str, Any]:
    """`params` with the credential replaced, for printing."""
    safe = dict(params)
    if field in safe:
        safe[field] = "<redacted>"
    return safe
