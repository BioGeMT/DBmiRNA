from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .registry import PROJECT_ROOT, load_schema_bundle


EXTRA_COLLECTION_SCHEMA_PATHS = {
    "mre_predictor_scores": PROJECT_ROOT / "schemas" / "mre_predictor_scores.schema.json",
}

RUN_ID_COLLECTIONS = (
    "transcript_feature_tracks",
    "experiments",
    "experiment_gene_effects",
    "predictor_scores",
    "site_observations",
    "mirna_recognition_elements",
    "mre_predictor_scores",
    "site_transcript_overlaps",
    "mre_sites",
    "nucleotide_profiles",
    "literature_documents",
    "literature_mentions",
    "literature_assertions",
)


def validate_output_bundle(
    out_dir: str | Path,
    *,
    require_data_collection: bool = False,
) -> list[str]:
    out_dir = Path(out_dir)
    errors: list[str] = []
    schema_bundle = load_schema_bundle()
    defs = _load_collection_defs(schema_bundle)

    if not out_dir.exists():
        return [f"Output directory does not exist: {out_dir}."]
    if not out_dir.is_dir():
        return [f"Output path is not a directory: {out_dir}."]

    jsonl_paths = sorted(out_dir.glob("*.jsonl"))
    if not jsonl_paths:
        errors.append(f"{out_dir}: no JSONL collection files found.")

    try:
        import jsonschema
    except ImportError:
        jsonschema = None
        errors.append("Install jsonschema to enable JSON Schema validation.")

    records_by_collection: dict[str, dict[str, dict]] = defaultdict(dict)
    record_counts_by_collection: dict[str, int] = defaultdict(int)

    for path in jsonl_paths:
        collection = path.stem
        if collection not in defs:
            errors.append(f"{path.name} does not match a known collection schema.")
            continue

        validator = None
        if jsonschema is not None:
            validator = jsonschema.Draft202012Validator(
                {"$ref": f"#/$defs/{collection}", "$defs": defs}
            )

        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                record_counts_by_collection[collection] += 1
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    errors.append(f"{path.name}:{line_number}: invalid JSON: {exc.msg}.")
                    continue

                record_id = record.get("_id")
                if not isinstance(record_id, str) or not record_id:
                    errors.append(f"{path.name}:{line_number}: missing non-empty _id.")
                elif record_id in records_by_collection[collection]:
                    errors.append(f"{path.name}:{line_number}: duplicate _id {record_id!r}.")
                else:
                    records_by_collection[collection][record_id] = record

                if validator is not None:
                    for schema_error in validator.iter_errors(record):
                        location = ".".join(str(part) for part in schema_error.path) or "<record>"
                        errors.append(
                            f"{path.name}:{line_number}: {schema_error.message} at {location}."
                        )
                        break

        if record_counts_by_collection[collection] == 0:
            errors.append(f"{path.name}: collection file is empty.")

    errors.extend(
        _validate_bundle_completeness(
            records_by_collection,
            require_data_collection=require_data_collection,
        )
    )
    errors.extend(_validate_relationships(records_by_collection))
    return errors


def _load_collection_defs(schema_bundle: dict) -> dict:
    defs = dict(schema_bundle.get("$defs", {}))
    shared_defs = dict(defs)
    for collection, path in EXTRA_COLLECTION_SCHEMA_PATHS.items():
        schema = json.loads(path.read_text(encoding="utf-8"))
        schema.setdefault("$defs", shared_defs)
        defs[collection] = schema
    return defs


def _validate_bundle_completeness(
    records_by_collection: dict[str, dict[str, dict]],
    *,
    require_data_collection: bool,
) -> list[str]:
    errors: list[str] = []
    present_collections = {collection for collection, records in records_by_collection.items() if records}
    data_collections = present_collections - {"ingestion_runs"}

    if require_data_collection and not data_collections:
        errors.append("Output bundle contains no data collections beyond ingestion_runs.")

    collections_with_run_ids = present_collections.intersection(RUN_ID_COLLECTIONS)
    if collections_with_run_ids and "ingestion_runs" not in present_collections:
        errors.append(
            "Output bundle contains run-scoped records but is missing ingestion_runs.jsonl."
        )

    return errors


def _validate_relationships(records_by_collection: dict[str, dict[str, dict]]) -> list[str]:
    errors: list[str] = []

    def has(collection: str, record_id: str | None) -> bool:
        return bool(record_id) and record_id in records_by_collection.get(collection, {})

    def require(
        collection: str,
        record: dict,
        field: str,
        target_collection: str,
        *,
        required: bool = False,
    ) -> None:
        target_id = record.get(field)
        if not target_id:
            if required:
                errors.append(
                    f"{collection}:{record.get('_id')}: missing required reference field {field}."
                )
            return
        if not has(target_collection, target_id):
            errors.append(
                f"{collection}:{record.get('_id')}: {field} references missing "
                f"{target_collection} record {target_id!r}."
            )

    for collection in RUN_ID_COLLECTIONS:
        for record in records_by_collection.get(collection, {}).values():
            require(collection, record, "run_id", "ingestion_runs", required=True)

    for collection in ("mirna_gene_pairs", "experiment_gene_effects", "predictor_scores", "mre_sites"):
        for record in records_by_collection.get(collection, {}).values():
            require(collection, record, "mirna_id", "mirnas", required=True)
            require(collection, record, "gene_id", "genes", required=True)

    for record in records_by_collection.get("transcripts", {}).values():
        require("transcripts", record, "gene_id", "genes", required=True)

    for record in records_by_collection.get("experiment_gene_effects", {}).values():
        require("experiment_gene_effects", record, "experiment_id", "experiments", required=True)
        require("experiment_gene_effects", record, "pair_id", "mirna_gene_pairs", required=True)

    for record in records_by_collection.get("predictor_scores", {}).values():
        require("predictor_scores", record, "predictor_id", "predictors", required=True)
        require("predictor_scores", record, "pair_id", "mirna_gene_pairs", required=True)

    for record in records_by_collection.get("mirna_recognition_elements", {}).values():
        require("mirna_recognition_elements", record, "mirna_id", "mirnas", required=True)
        require("mirna_recognition_elements", record, "gene_id", "genes")

    for record in records_by_collection.get("mre_predictor_scores", {}).values():
        require("mre_predictor_scores", record, "predictor_id", "predictors", required=True)
        require("mre_predictor_scores", record, "mre_id", "mirna_recognition_elements", required=True)
        require("mre_predictor_scores", record, "mirna_id", "mirnas", required=True)
        require("mre_predictor_scores", record, "gene_id", "genes")

    for record in records_by_collection.get("site_transcript_overlaps", {}).values():
        require("site_transcript_overlaps", record, "observation_id", "site_observations", required=True)
        require("site_transcript_overlaps", record, "transcript_id", "transcripts", required=True)
        require("site_transcript_overlaps", record, "gene_id", "genes", required=True)

    for record in records_by_collection.get("mre_sites", {}).values():
        require("mre_sites", record, "transcript_id", "transcripts", required=True)
        require("mre_sites", record, "observation_id", "site_observations", required=True)
        require("mre_sites", record, "pair_id", "mirna_gene_pairs", required=True)

    for record in records_by_collection.get("nucleotide_profiles", {}).values():
        entity_type = record.get("entity_type")
        entity_id = record.get("entity_id")
        target_collection = {
            "site_observation": "site_observations",
            "mre_site": "mre_sites",
            "transcript": "transcripts",
        }.get(entity_type)
        if target_collection and not has(target_collection, entity_id):
            errors.append(
                f"nucleotide_profiles:{record.get('_id')}: entity_id references missing "
                f"{target_collection} record {entity_id!r}."
            )

    return errors