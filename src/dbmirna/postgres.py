from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "sql" / "schema.sql"


LOAD_ORDER = [
    "ingestion_runs",
    "mirnas",
    "genes",
    "transcripts",
    "mirna_gene_pairs",
    "transcript_feature_tracks",
    "experiments",
    "experiment_gene_effects",
    "predictors",
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
]


TABLES: dict[str, tuple[str, str, dict[str, str]]] = {
    "ingestion_runs": ("provenance", "ingestion_runs", {
        "_id": "id", "source_repo": "source_repo", "source_path": "source_path",
        "source_release": "source_release", "started_at": "started_at",
        "completed_at": "completed_at", "transform_version": "transform_version",
        "checksums": "checksums", "row_counts": "row_counts", "notes": "notes",
    }),
    "mirnas": ("core", "mirnas", {
        "_id": "id", "canonical_name": "canonical_name", "species": "species",
        "sequence": "sequence", "id_namespace": "id_namespace",
        "canonical_accession": "canonical_accession", "family": "family", "arm": "arm",
        "aliases": "aliases", "normalization": "normalization", "source_refs": "source_refs",
    }),
    "genes": ("core", "genes", {
        "_id": "id", "canonical_symbol": "canonical_symbol", "species": "species",
        "id_namespace": "id_namespace", "canonical_accession": "canonical_accession",
        "aliases": "aliases", "normalization": "normalization", "source_refs": "source_refs",
    }),
    "transcripts": ("core", "transcripts", {
        "_id": "id", "gene_id": "gene_id", "id_namespace": "id_namespace",
        "canonical_accession": "canonical_accession", "gene_symbol": "gene_symbol",
        "species": "species", "sequence": "sequence", "sequence_scope": "sequence_scope",
        "genome_build": "genome_build", "tx_start": "tx_start", "tx_end": "tx_end",
        "strand": "strand", "localization_labels": "localization_labels",
        "feature_track_summary": "feature_track_summary", "sequence_length": "sequence_length",
        "normalization": "normalization", "source_refs": "source_refs",
    }),
    "mirna_gene_pairs": ("core", "mirna_gene_pairs", {
        "_id": "id", "mirna_id": "mirna_id", "gene_id": "gene_id", "species": "species",
        "evidence_counts": "evidence_counts",
        "best_supported_transcript_ids": "best_supported_transcript_ids",
        "support_summary": "support_summary", "source_refs": "source_refs",
    }),
    "transcript_feature_tracks": ("core", "transcript_feature_tracks", {
        "_id": "id", "transcript_id": "transcript_id", "track_name": "track_name",
        "source": "source", "kind": "kind", "count": "count",
        "payload_ref": "payload_ref", "run_id": "run_id",
    }),
    "experiments": ("evidence", "experiments", {
        "_id": "id", "dataset_id": "dataset_id", "mirna_id": "mirna_id",
        "mirna_name_raw": "mirna_name_raw", "mirna_sequence": "mirna_sequence",
        "article_pubmed_id": "article_pubmed_id", "geo_accession": "geo_accession",
        "organism": "organism", "tested_cell_line": "tested_cell_line",
        "tissue": "tissue", "method": "method", "experiment_type": "experiment_type",
        "treatment": "treatment", "de_table_path": "de_table_path",
        "source_repo": "source_repo", "run_id": "run_id",
    }),
    "experiment_gene_effects": ("evidence", "experiment_gene_effects", {
        "_id": "id", "experiment_id": "experiment_id", "pair_id": "pair_id",
        "mirna_id": "mirna_id", "gene_id": "gene_id", "logFC": "logfc",
        "FDR": "fdr", "PValue": "pvalue", "logCPM": "logcpm",
        "F_statistic": "f_statistic", "effect_direction": "effect_direction",
        "passes_default_threshold": "passes_default_threshold", "raw_row": "raw_row",
        "run_id": "run_id",
    }),
    "predictors": ("evidence", "predictors", {
        "_id": "id", "tool_id": "tool_id", "official_name": "official_name",
        "organism": "organism", "score_type": "score_type",
        "score_direction": "score_direction", "score_range": "score_range",
        "input_id_gene_type": "input_id_gene_type",
        "canonical_id_gene_type": "canonical_id_gene_type",
        "input_id_mirna_type": "input_id_mirna_type",
        "canonical_id_mirna_type": "canonical_id_mirna_type",
        "predictor_output_path": "predictor_output_path", "source_repo": "source_repo",
    }),
    "predictor_scores": ("evidence", "predictor_scores", {
        "_id": "id", "predictor_id": "predictor_id", "pair_id": "pair_id",
        "mirna_id": "mirna_id", "gene_id": "gene_id", "score_raw": "score_raw",
        "score_direction": "score_direction",
        "score_rank_within_mirna": "score_rank_within_mirna",
        "source_row": "source_row", "run_id": "run_id",
    }),
    "site_observations": ("evidence", "site_observations", {
        "_id": "id", "source_dataset": "source_dataset", "source_repo": "source_repo",
        "mirna_id": "mirna_id", "mirna_name_raw": "mirna_name_raw",
        "mirna_family_raw": "mirna_family_raw", "mirna_sequence_raw": "mirna_sequence_raw",
        "target_sequence_raw": "target_sequence_raw", "feature_label_raw": "feature_label_raw",
        "label": "label", "chr": "chr", "start": "start_pos", "end": "end_pos",
        "strand": "strand", "read_len": "read_len", "gene_cluster_id": "gene_cluster_id",
        "gene_phyloP_ref": "gene_phylop_ref", "gene_phastCons_ref": "gene_phastcons_ref",
        "raw_row": "raw_row", "run_id": "run_id",
    }),
    "mirna_recognition_elements": ("evidence", "mirna_recognition_elements", {
        "_id": "id", "source_dataset": "source_dataset", "source_repo": "source_repo",
        "source_split": "source_split", "source_row_index": "source_row_index",
        "label": "label", "mirna_id": "mirna_id", "mirna_name_raw": "mirna_name_raw",
        "mirna_family_raw": "mirna_family_raw", "mirna_sequence_raw": "mirna_sequence_raw",
        "gene_id": "gene_id", "gene_name_raw": "gene_name_raw",
        "gene_cluster_id": "gene_cluster_id", "target_sequence_raw": "target_sequence_raw",
        "feature_label_raw": "feature_label_raw", "chr": "chr", "start": "start_pos",
        "end": "end_pos", "strand": "strand", "read_len": "read_len",
        "experiment_type": "experiment_type", "organism": "organism",
        "raw_row": "raw_row", "run_id": "run_id",
    }),
    "mre_predictor_scores": ("evidence", "mre_predictor_scores", {
        "_id": "id", "predictor_id": "predictor_id", "mre_id": "mre_id",
        "mirna_id": "mirna_id", "gene_id": "gene_id", "score_raw": "score_raw",
        "score_direction": "score_direction", "score_rank_within_mre": "score_rank_within_mre",
        "label": "label", "source_dataset": "source_dataset", "source_row": "source_row",
        "run_id": "run_id",
    }),
    "site_transcript_overlaps": ("evidence", "site_transcript_overlaps", {
        "_id": "id", "observation_id": "observation_id", "transcript_id": "transcript_id",
        "gene_id": "gene_id", "gene_name_raw": "gene_name_raw",
        "contained_100pct": "contained_100pct", "overlap_tx_bp": "overlap_tx_bp",
        "overlap_exon_bp": "overlap_exon_bp", "overlap_cds_bp": "overlap_cds_bp",
        "overlap_utr5_bp": "overlap_utr5_bp", "overlap_utr3_bp": "overlap_utr3_bp",
        "read_start_in_tx_1based": "read_start_in_tx_1based",
        "read_end_in_tx_1based": "read_end_in_tx_1based",
        "overlap_start_genome_1based": "overlap_start_genome_1based",
        "overlap_end_genome_1based": "overlap_end_genome_1based",
        "run_id": "run_id",
    }),
    "mre_sites": ("evidence", "mre_sites", {
        "_id": "id", "pair_id": "pair_id", "mirna_id": "mirna_id", "gene_id": "gene_id",
        "transcript_id": "transcript_id", "observation_id": "observation_id",
        "chr": "chr", "start": "start_pos", "end": "end_pos", "strand": "strand",
        "read_len": "read_len", "selection_policy": "selection_policy",
        "dominance_mode": "dominance_mode", "selected_gene_name": "selected_gene_name",
        "dominant_region_selected": "dominant_region_selected",
        "regions_present_selected": "regions_present_selected",
        "dominant_region_union": "dominant_region_union",
        "regions_present_union": "regions_present_union",
        "bp_utr3_selected": "bp_utr3_selected", "bp_cds_selected": "bp_cds_selected",
        "bp_utr5_selected": "bp_utr5_selected",
        "bp_exon_other_selected": "bp_exon_other_selected",
        "bp_intron_selected": "bp_intron_selected",
        "bp_intergenic_selected": "bp_intergenic_selected",
        "bp_utr3_union": "bp_utr3_union", "bp_cds_union": "bp_cds_union",
        "bp_utr5_union": "bp_utr5_union",
        "bp_exon_other_union": "bp_exon_other_union",
        "bp_intron_union": "bp_intron_union",
        "bp_intergenic_union": "bp_intergenic_union",
        "ambiguous_union_vs_selected": "ambiguous_union_vs_selected",
        "n_passing_transcripts": "n_passing_transcripts", "run_id": "run_id",
    }),
    "nucleotide_profiles": ("evidence", "nucleotide_profiles", {
        "_id": "id", "entity_type": "entity_type", "entity_id": "entity_id",
        "profile_type": "profile_type", "length": "length", "storage_mode": "storage_mode",
        "values": "values_json", "payload_ref": "payload_ref", "metadata": "metadata",
        "run_id": "run_id",
    }),
    "literature_documents": ("literature", "literature_documents", {
        "_id": "id", "document_id": "document_id", "pmid": "pmid", "title": "title",
        "abstract": "abstract", "full_text": "full_text", "source": "source",
        "year": "year", "metadata": "metadata", "run_id": "run_id",
    }),
    "literature_mentions": ("literature", "literature_mentions", {
        "_id": "id", "document_id": "document_id", "annotation_id": "annotation_id",
        "source": "source", "span_text": "span_text", "start": "start_pos",
        "end": "end_pos", "entity_type": "entity_type",
        "canonical_id_raw": "canonical_id_raw", "canonical_name_raw": "canonical_name_raw",
        "resolved_mirna_id": "resolved_mirna_id", "resolved_gene_id": "resolved_gene_id",
        "confidence": "confidence", "run_id": "run_id",
    }),
    "literature_assertions": ("literature", "literature_assertions", {
        "_id": "id", "document_id": "document_id", "mirna_id": "mirna_id",
        "gene_id": "gene_id", "assertion_type": "assertion_type",
        "direction": "direction", "evidence_text": "evidence_text",
        "curation_status": "curation_status", "curator": "curator", "run_id": "run_id",
    }),
}


JSONB_COLUMNS = {
    "normalization", "source_refs", "evidence_counts", "support_summary", "payload_ref",
    "checksums", "row_counts", "localization_labels", "feature_track_summary", "raw_row",
    "source_row", "gene_phylop_ref", "gene_phastcons_ref", "values_json", "metadata",
}


def initialize_postgres(dsn: str) -> None:
    psycopg, _ = _load_psycopg()
    with psycopg.connect(dsn) as conn:
        conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))


def load_jsonl_bundle_to_postgres(out_dir: str | Path, dsn: str, *, init_schema: bool = False) -> dict[str, int]:
    psycopg, Jsonb = _load_psycopg()
    out_dir = Path(out_dir)
    if init_schema:
        initialize_postgres(dsn)

    counts: dict[str, int] = {}
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            for collection in LOAD_ORDER:
                path = out_dir / f"{collection}.jsonl"
                if not path.exists() or collection not in TABLES:
                    continue
                schema_name, table_name, field_map = TABLES[collection]
                sql_text = _upsert_sql(schema_name, table_name, list(field_map.values()))
                row_count = 0
                with path.open("r", encoding="utf-8") as handle:
                    for line in handle:
                        record = json.loads(line)
                        values = [
                            _sql_value(record.get(source_field), target_column, Jsonb)
                            for source_field, target_column in field_map.items()
                        ]
                        cur.execute(sql_text, values)
                        row_count += 1
                counts[collection] = row_count
    return counts


def _load_psycopg():
    try:
        import psycopg
        from psycopg.types.json import Jsonb
    except ImportError as exc:
        raise RuntimeError(
            "PostgreSQL loading requires psycopg. Install the project with the postgres "
            "extra, for example: python3 -m pip install -e '.[postgres]'"
        ) from exc
    return psycopg, Jsonb


def _sql_value(value: Any, target_column: str, Jsonb):
    if target_column in JSONB_COLUMNS:
        return Jsonb({} if value is None and target_column not in {"source_refs", "payload_ref", "values_json"} else value)
    return value


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _upsert_sql(schema_name: str, table_name: str, columns: list[str]) -> str:
    qualified_table = f"{_quote_identifier(schema_name)}.{_quote_identifier(table_name)}"
    column_list = ", ".join(_quote_identifier(column) for column in columns)
    placeholders = ", ".join(["%s"] * len(columns))
    updates = ", ".join(
        f"{_quote_identifier(column)} = EXCLUDED.{_quote_identifier(column)}"
        for column in columns
        if column != "id"
    )
    return (
        f"INSERT INTO {qualified_table} ({column_list}) VALUES ({placeholders}) "
        f"ON CONFLICT (id) DO UPDATE SET {updates}"
    )