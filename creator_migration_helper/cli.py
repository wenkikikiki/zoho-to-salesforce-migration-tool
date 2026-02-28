"""Command-line interface for creator-migration-helper."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Sequence

from .diffing import diff_schemas, render_diff_markdown
from .mapping import generate_mapping_rows, load_salesforce_objects, write_mapping_csv
from .schema import (
    build_schema_snapshot,
    load_schema_json,
    write_data_dictionary_markdown,
    write_schema_json,
)
from .zoho import ZohoAPIError, ZohoClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="creator-migration-helper",
        description="Generate Zoho Creator schema docs, diffs, and Salesforce mapping scaffolds.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot = subparsers.add_parser(
        "snapshot",
        help="Fetch Zoho metadata and generate schema/data dictionary artifacts.",
    )
    snapshot.add_argument("--base-url", required=True, help="Zoho API domain, e.g. www.zohoapis.com")
    snapshot.add_argument("--owner", required=True, help="Zoho account owner name")
    snapshot.add_argument("--app", required=True, help="Zoho Creator app link name")
    snapshot.add_argument(
        "--token",
        default=os.getenv("ZOHO_TOKEN"),
        help="Zoho OAuth token; falls back to ZOHO_TOKEN env var",
    )
    snapshot.add_argument(
        "--env",
        default="production",
        choices=["production", "development", "stage"],
        help="Zoho Creator environment header value",
    )
    snapshot.add_argument("--out-dir", default="out", help="Output directory")

    diff = subparsers.add_parser("diff", help="Diff two schema snapshots.")
    diff.add_argument("old_schema", help="Path to old schema JSON")
    diff.add_argument("new_schema", help="Path to new schema JSON")
    diff.add_argument("--out", default="out/schema_diff.md", help="Output markdown path")
    diff.add_argument(
        "--json-out",
        default="",
        help="Optional path to also write raw diff JSON",
    )

    mapping = subparsers.add_parser(
        "mapping",
        help="Generate Zoho-to-Salesforce mapping seed CSV from a schema snapshot.",
    )
    mapping.add_argument("--schema", required=True, help="Path to schema JSON")
    mapping.add_argument(
        "--salesforce-objects",
        required=True,
        help="Path to Salesforce object/field schema JSON",
    )
    mapping.add_argument("--out", default="out/sf_mapping_seed.csv", help="Output CSV path")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "snapshot":
            return run_snapshot(args)
        if args.command == "diff":
            return run_diff(args)
        if args.command == "mapping":
            return run_mapping(args)
    except (ValueError, OSError, ZohoAPIError) as exc:
        print(f"error: {exc}")
        return 1

    parser.print_help()
    return 1


def run_snapshot(args: argparse.Namespace) -> int:
    if not args.token:
        raise ValueError("missing token; pass --token or set ZOHO_TOKEN")

    client = ZohoClient(
        base_url=args.base_url,
        owner=args.owner,
        app=args.app,
        token=args.token,
        environment=args.env,
    )
    schema = build_schema_snapshot(client, environment=args.env)

    out_dir = Path(args.out_dir)
    schema_path = out_dir / f"schema.{args.env}.json"
    dictionary_path = out_dir / f"data_dictionary.{args.env}.md"
    write_schema_json(schema, schema_path)
    write_data_dictionary_markdown(schema, dictionary_path)

    print(f"Wrote schema snapshot: {schema_path}")
    print(f"Wrote data dictionary: {dictionary_path}")
    return 0


def run_diff(args: argparse.Namespace) -> int:
    old_schema_path = Path(args.old_schema)
    new_schema_path = Path(args.new_schema)

    old_schema = load_schema_json(old_schema_path)
    new_schema = load_schema_json(new_schema_path)
    diff = diff_schemas(old_schema, new_schema)
    report = render_diff_markdown(diff)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"Wrote diff report: {out_path}")

    if args.json_out:
        json_path = Path(args.json_out)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(diff, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Wrote raw diff JSON: {json_path}")

    return 0


def run_mapping(args: argparse.Namespace) -> int:
    schema_path = Path(args.schema)
    sf_path = Path(args.salesforce_objects)
    out_path = Path(args.out)

    schema = load_schema_json(schema_path)
    objects = load_salesforce_objects(sf_path)
    rows = generate_mapping_rows(schema, objects)
    write_mapping_csv(rows, out_path)

    print(f"Wrote Salesforce mapping scaffold: {out_path}")
    print(f"Rows generated: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
