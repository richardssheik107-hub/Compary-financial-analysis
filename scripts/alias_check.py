from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.company_aliases import load_aliases
from src.data_service import identify_company


def main() -> None:
    parser = argparse.ArgumentParser(description="Check if alias mapping and company identification work.")
    parser.add_argument("query", nargs="?", default="万科", help="Alias/query to test")
    parser.add_argument("--reload", action="store_true", help="Force reload alias CSV")
    args = parser.parse_args()

    aliases = load_aliases(force_reload=args.reload)
    normalized = args.query.strip().lower()
    mapped = aliases.get(normalized)
    identify = identify_company(args.query)

    print("=== Alias Check ===")
    print(f"query: {args.query}")
    print(f"csv_mapped: {mapped or 'N/A'}")
    print(f"identify_found: {identify.get('found')}")
    print(f"identify_name: {identify.get('company_name')}")
    print(f"identify_code: {identify.get('stock_code')}")
    print(f"identify_source: {identify.get('match_source')}")


if __name__ == "__main__":
    main()
