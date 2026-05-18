from __future__ import annotations

import argparse
import json
import sys

from .loaders.funmirbench import export_funmirbench
from .loaders.genomic_region_annotator import export_genomic_region_annotator
from .loaders.hejret_cache import export_hejret_cache
from .normalization import build_normalization_info
from .postgres import initialize_postgres, load_jsonl_bundle_to_postgres
from .registry import build_module_info, build_overview, validate_project
from .validation import validate_output_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect and run DBmiRNA loaders.")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("overview", help="Show the project overview.")
    subparsers.add_parser("validate", help="Validate manifest cross-references.")
    subparsers.add_parser("normalization-info", help="Show the active miRBase and Ensembl normalization policy.")

    validate_outputs_parser = subparsers.add_parser("validate-outputs", help="Validate an exported JSONL bundle.")
    validate_outputs_parser.add_argument("--out-dir", required=True, help="Output bundle directory to validate.")

    init_pg_parser = subparsers.add_parser("init-postgres", help="Create DBmiRNA PostgreSQL schemas and tables.")
    init_pg_parser.add_argument("--dsn", required=True, help="PostgreSQL connection string.")

    load_pg_parser = subparsers.add_parser("load-postgres", help="Load an exported JSONL bundle into PostgreSQL.")
    load_pg_parser.add_argument("--out-dir", required=True, help="Output bundle directory to load.")
    load_pg_parser.add_argument("--dsn", required=True, help="PostgreSQL connection string.")
    load_pg_parser.add_argument("--init-schema", action="store_true", help="Create schemas and tables before loading.")

    module_info_parser = subparsers.add_parser("module-info", help="Show one source module and its repo root.")
    module_info_parser.add_argument("module_id", help="Module id, for example funmirbench or genomic_region_annotator.")

    fun_parser = subparsers.add_parser("load-funmirbench", help="Export normalized FuNmiRBench records to JSONL.")
    fun_parser.add_argument("--out-dir", required=True, help="Output directory for JSONL bundle.")
    fun_parser.add_argument("--repo-root", required=True, help="FuNmiRBench repository root.")
    fun_parser.add_argument("--max-experiments", type=int, default=None, help="Optional cap on experiment rows.")
    fun_parser.add_argument("--skip-predictor-scores", action="store_true", help="Skip predictor score exports.")
    fun_parser.add_argument("--predictor-tool", action="append", dest="predictor_tools", default=None, help="Restrict to one or more predictor tool ids.")
    fun_parser.add_argument("--max-predictor-rows", type=int, default=None, help="Optional row cap per predictor file.")

    gra_parser = subparsers.add_parser("load-gra", help="Export normalized genomic-region-annotator records to JSONL.")
    gra_parser.add_argument("--out-dir", required=True, help="Output directory for JSONL bundle.")
    gra_parser.add_argument("--repo-root", required=True, help="genomic-region-annotator repository root.")
    gra_parser.add_argument("--dataset-stem", default="Hejret_2023", help="Dataset stem such as Hejret_2023.")
    gra_parser.add_argument("--max-sites", type=int, default=None, help="Optional cap on site rows.")

    hejret_parser = subparsers.add_parser("load-hejret-cache", help="Export cached Hejret AGO2 CLASH train/test MRE rows to JSONL.")
    hejret_parser.add_argument("--out-dir", required=True, help="Output directory for JSONL bundle.")
    hejret_parser.add_argument("--cache-root", required=True, help="Hejret cache root containing train/test dataset.tsv files.")
    hejret_parser.add_argument("--split", action="append", dest="splits", default=None, help="Split to export. Repeat for multiple splits. Defaults to train and test.")
    hejret_parser.add_argument("--max-rows-per-split", type=int, default=None, help="Optional row cap per split.")

    args = parser.parse_args()

    command = args.command or "overview"

    if command == "overview":
        print(build_overview())
        return 0

    if command == "module-info":
        print(build_module_info(args.module_id))
        return 0

    if command == "normalization-info":
        print(build_normalization_info())
        return 0

    if command == "validate-outputs":
        errors = validate_output_bundle(args.out_dir)
        if errors:
            print("DBmiRNA output validation failed:")
            for error in errors:
                print(f"- {error}")
            return 1
        print("DBmiRNA output validation passed.")
        return 0

    if command == "init-postgres":
        initialize_postgres(args.dsn)
        print("DBmiRNA PostgreSQL schema initialized.")
        return 0

    if command == "load-postgres":
        errors = validate_output_bundle(args.out_dir)
        if errors:
            print("DBmiRNA output validation failed:")
            for error in errors:
                print(f"- {error}")
            return 1
        counts = load_jsonl_bundle_to_postgres(
            args.out_dir,
            args.dsn,
            init_schema=args.init_schema,
        )
        print(json.dumps({"loaded": counts}, indent=2))
        return 0

    if command == "load-funmirbench":
        manifest = export_funmirbench(
            out_dir=args.out_dir,
            repo_root=args.repo_root,
            max_experiments=args.max_experiments,
            include_predictor_scores=not args.skip_predictor_scores,
            predictor_tools=args.predictor_tools,
            max_predictor_rows=args.max_predictor_rows,
        )
        print(json.dumps(manifest, indent=2))
        return 0

    if command == "load-gra":
        manifest = export_genomic_region_annotator(
            out_dir=args.out_dir,
            repo_root=args.repo_root,
            dataset_stem=args.dataset_stem,
            max_sites=args.max_sites,
        )
        print(json.dumps(manifest, indent=2))
        return 0

    if command == "load-hejret-cache":
        manifest = export_hejret_cache(
            out_dir=args.out_dir,
            cache_root=args.cache_root,
            splits=args.splits,
            max_rows_per_split=args.max_rows_per_split,
        )
        print(json.dumps(manifest, indent=2))
        return 0

    errors = validate_project()
    if errors:
        print("DBmiRNA validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("DBmiRNA validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())