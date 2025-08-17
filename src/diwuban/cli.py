import argparse
from pathlib import Path


def cli() -> int:
    parser = argparse.ArgumentParser(
        prog="diwuban", description="diwuban CLI prototype"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ingest = sub.add_parser("ingest", help="ingest data into DB (prototype)")
    p_ingest.add_argument("--mapping", required=True, help="path to data_mapping.json")
    p_ingest.add_argument(
        "--dry-run", action="store_true", help="parse only, no DB writes"
    )

    p_align = sub.add_parser(
        "align", help="align station data onto a time grid (prototype)"
    )
    p_align.add_argument("--station", required=True, help="station name")
    p_align.add_argument("--grid", default="auto", help="grid: auto|1s|5s|1min")

    args = parser.parse_args()
    if args.cmd == "ingest":
        mapping_path = Path(args.mapping)
        if not mapping_path.exists():
            print(f"mapping not found: {mapping_path}")
            return 1
        print(f"[INGEST] mapping={mapping_path} dry_run={args.dry_run}")
        return 0
    elif args.cmd == "align":
        print(f"[ALIGN] station={args.station} grid={args.grid}")
        return 0
    else:
        parser.print_help()
        return 2


if __name__ == "__main__":
    raise SystemExit(cli())
