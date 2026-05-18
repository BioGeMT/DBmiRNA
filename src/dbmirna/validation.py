from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .registry import load_schema_bundle


def validate_output_bundle(out_dir: str | Path) -> list[str]:
    out_dir = Path(out_dir)
    errors: list[str] = []
    schema_bundle = load_schema_bundle()
    defs = schema_bundle.get("$defs", {})

    try:
        import jsonschema
    except ImportError:
        jsonschema = None
        errors.append("Install jsonschema to enable JSON Schema validation.")

    records_by_collection: dict[str, dict[str, dict]] = defaultdict(dict)

    for path in sorted(out_dir.glob("*.jsonl")):
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

    errors.extend(_validate_relationships(records_by_collection))
    return errors


def _validate_relationships(records_by_collection: dict[str, dict[str, dict]]) -> list[str]:
    errors: list[str] = []

    def has(collection: str, record_id: str | None) -> bool:
        return bool(record_id) and record_id in records_by_collection.get(collection, {})

    def require(collection: str, record: dict, field: str, target_collection: str) -> None:
        target_id = record.get(field)
        if target_id and not has(target_collection, target_id):
            errors.append(
                f"{collection}:{record.get('_id')}: {field} references missing "
                f"{target_collection} record {target_id!r}."
            )

    for collection in ("mirna_gene_pairs", "experiment_gene_effects", "predictor_scores", "mre_sites"):
        for record in records_by_collection.get(collection, {}).values():
            require(collection, record, "mirna_id", "mirnas")
            require(collection, record, "gene_id", "genes")

    for record in records_by_collection.get("transcripts", {}).values():
        require("transcripts", record, "gene_id", "genes")

    for record in records_by_collection.get("experiment_gene_effects", {}).values():
        require("experiment_gene_effects", record, "experiment_id", "experiments")
        require("experiment_gene_effects", record, "pair_id", "mirna_gene_pairs")

    for record in records_by_collection.get("predictor_scores", {}).values():
        require("predictor_scores", record, "predictor_id", "predictors")
        require("predictor_scores", record, "pair_id", "mirna_gene_pairs")

    for record in records_by_collection.get("mirna_recognition_elements", {}).values():
        require("mirna_recognition_elements", record, "mirna_id", "mirnas")
        require("mirna_recognition_elements", record, "gene_id", "genes")

    for record in records_by_collection.get("site_transcript_overlaps", {}).values():
        require("site_transcript_overlaps", record, "observation_id", "site_observations")
        require("site_transcript_overlaps", record, "transcript_id", "transcripts")
        require("site_transcript_overlaps", record, "gene_id", "genes")

    for record in records_by_collection.get("mre_sites", {}).values():
        require("mre_sites", record, "transcript_id", "transcripts")
        require("mre_sites", record, "observation_id", "site_observations")
        require("mre_sites", record, "pair_id", "mirna_gene_pairs")

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
