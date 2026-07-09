"""Verify a URL actually contains a claimed value before it can be a [ref] — SKELETON.

    python scripts/url_verifier.py --url <url> --contains "350,000 bpd"

Hard requirement (CLAUDE.md): every URL in the staging xlsx passes this first, even URLs
inherited from RMI/OGJ. "Verified" means: the page loads AND the specific claimed value
(capacity, owner, status, year, coords) appears in the fetched text/PDF. A page that loads
but lacks the value is a FAILED citation, not a source.

Rejects outright (returns fail without fetching):
  - gem.wiki / globalenergymonitor.org (circular — GEM's own publication)
  - abarrelfull.wikidot.com (community wiki echoing OGJ/GEM — chase its footnote instead)

TODO: implement fetch (requests + pdf text extraction), normalized value matching
(handle 350000 vs "350,000" vs "350 kbpd"), and a batch mode over a staged xlsx column.
Reuse ../lng-terminals-researcher/scripts/url_verifier.py as the base.
"""

from __future__ import annotations
import argparse
import sys
from urllib.parse import urlparse

BLOCKED_HOSTS = ("gem.wiki", "globalenergymonitor.org", "abarrelfull.wikidot.com")


def is_blocked(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == b or host.endswith("." + b) for b in BLOCKED_HOSTS)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--contains", required=True, help="the exact value the cell asserts")
    args = ap.parse_args()
    if is_blocked(args.url):
        print(f"BLOCKED (non-citable host): {args.url}")
        sys.exit(2)
    raise NotImplementedError("url_verifier.py fetch/match is a skeleton — see the docstring.")


if __name__ == "__main__":
    main()
