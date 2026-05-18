from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path
from typing import Iterable, Iterator

from dbmirna.normalization import canonical_mirna_document, canonical_mirna_id
from dbmirna.utils import (
    JsonlBundleWriter,
    as_float,
    as_int,
    clean_nullable,
    compact_dict,
    now_utc_iso,
    stable_hash,
)

BASE_MRE_COLUMNS = {
    "gene",
    "noncodingRNA",
    "noncodingRNA_name",
    "noncodingRNA_fam",
    "feature",
    "label",
    "chr",
    "start",
    "end",
    "strand",
    "gene_cluster_ID",
}

NUCLEOTIDE_PROFILE_COLUMNS = {
    "gene_phyloP": "phyloP",
    "gene_phastCons": "phastCons",
}


PREDICTOR_METADATA = {
    "TargetScanCnn_McGeary2019": {
        "official_name": "TargetScanCnn McGeary 2019",
        "score_type": "MRE binding score",
        "score_direction": "higher_is_stronger",
    },
    "miRBenchCNN_Manakov": {
        "official_name": "miRBenchCNN Manakov",
        "score_type": "MRE binding probability",
        "score_direction": "higher_is_stronger",
    },
    "miRBind2": {
        "official_name": "miRBind2",
        "score_type": "MRE binding probability",
        "score_direction": "higher_is_stronger",
    },
}


def export_zenodo_mre_tsv(
    *,
    out_dir: str | Path,
    input_path: str | Path,
    dataset_id: str,
    source_url: str | None = None,
    source_repo: str = "Zenodo",
    source_split: str = "unspecified",
    experiment_type: str | None = None,
    organism: str = "Homo sapiens",
    max_rows: int | None = None,
) -> dict:
    input_path = Path(input_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    started_at = now_utc_iso()
    run_id = f"ingest:zenodo_mre_tsv:{dataset_id}:{started_at}"
    writer = JsonlBundleWriter(out_dir)

    mirnas: dict[str, dict] = {}
    predictor_columns: list[str] | None = None
    predictor_docs: dict[str, dict] = {}

    source_ref = {
        "source_repo": source_repo,
        "source_path": str(input_path),
        "source_release": source_url,
        "artifact_id": dataset_id,
        "run_id": run_id,
    }

    for row_index, row in enumerate(_iter_tsv_rows_auto(input_path), start=1):
        if max_rows is not None and row_index > max_rows:
            break
        if predictor_columns is None:
            predictor_columns = _predictor_columns(row.keys())
            predictor_docs = {
                column: _predictor_doc(column, input_path=input_path, source_repo=source_repo)
                for column in predictor_columns
            }

        mirna_name = str(row["noncodingRNA_name"]).strip()
        mirna_id, _ = canonical_mirna_id(
            name=mirna_name,
            accession=None,
            source_repo=source_repo,
        )
        if mirna_id not in mirnas:
            mirnas[mirna_id] = canonical_mirna_document(
                name=mirna_name,
                species=organism,
                sequence=clean_nullable(row.get("noncodingRNA")),
                accession=None,
                family=clean_nullable(row.get("noncodingRNA_fam")),
                source_repo=source_repo,
                source_ref=source_ref,
            )

        mre_id = f"mre:{dataset_id}:{source_split}:{stable_hash(row_index, row)}"
        label = as_int(row.get("label"))
        writer.write(
            "mirna_recognition_elements",
            compact_dict(
                {
                    "_id": mre_id,
                    "source_dataset": dataset_id,
                    "source_repo": source_repo,
                    "source_split": source_split,
                    "source_row_index": row_index,
                    "label": label,
                    "mirna_id": mirna_id,
                    "mirna_name_raw": mirna_name,
                    "mirna_family_raw": clean_nullable(row.get("noncodingRNA_fam")),
                    "mirna_sequence_raw": clean_nullable(row.get("noncodingRNA")),
                    "gene_id": None,
                    "gene_name_raw": None,
                    "gene_cluster_id": clean_nullable(row.get("gene_cluster_ID")),
                    "target_sequence_raw": clean_nullable(row.get("gene")),
                    "feature_label_raw": clean_nullable(row.get("feature")),
                    "chr": clean_nullable(row.get("chr")),
                    "start": as_int(row.get("start")),
                    "end": as_int(row.get("end")),
                    "strand": clean_nullable(row.get("strand")),
                    "read_len": _read_len(row),
                    "experiment_type": experiment_type,
                    "organism": organism,
                    "raw_row": row,
                    "run_id": run_id,
                }
            ),
        )

        for source_column, profile_type in NUCLEOTIDE_PROFILE_COLUMNS.items():
            values = _parse_numeric_array(row.get(source_column))
            if values is None:
                continue
            writer.write(
                "nucleotide_profiles",
                {
                    "_id": f"profile:{dataset_id}:{source_split}:{row_index}:{profile_type}",
                    "entity_type": "mre",
                    "entity_id": mre_id,
                    "profile_type": profile_type,
                    "length": len(values),
                    "storage_mode": "inline",
                    "values": values,
                    "payload_ref": None,
                    "metadata": {
                        "source_column": source_column,
                        "source_dataset": dataset_id,
                        "source_url": source_url,
                    },
                    "run_id": run_id,
                },
            )

        for predictor_column in predictor_columns or []:
            score = as_float(row.get(predictor_column))
            if score is None:
                continue
            predictor_id = f"predictor:{predictor_column}"
            writer.write(
                "mre_predictor_scores",
                compact_dict(
                    {
                        "_id": f"mre-score:{dataset_id}:{source_split}:{predictor_column}:{stable_hash(row_index, row)}",
                        "predictor_id": predictor_id,
                        "mre_id": mre_id,
                        "mirna_id": mirna_id,
                        "gene_id": None,
                        "score_raw": score,
                        "score_direction": predictor_docs[predictor_column]["score_direction"],
                        "score_rank_within_mre": None,
                        "label": label,
                        "source_dataset": dataset_id,
                        "source_row": row,
                        "run_id": run_id,
                    }
                ),
            )

    writer.write_many("mirnas", mirnas.values())
    writer.write_many("predictors", predictor_docs.values())

    completed_at = now_utc_iso()
    writer.write(
        "ingestion_runs",
        {
            "_id": run_id,
            "source_repo": source_repo,
            "source_path": str(input_path),
            "source_release": source_url,
            "started_at": started_at,
            "completed_at": completed_at,
            "transform_version": "0.1.0",
            "checksums": {},
            "row_counts": dict(writer.counts),
            "notes": f"Zenodo MRE TSV export for {dataset_id}.",
        },
    )
    writer.close()

    manifest = {
        "module": "zenodo_mre_tsv",
        "input_path": str(input_path),
        "dataset_id": dataset_id,
        "source_url": source_url,
        "source_split": source_split,
        "started_at": started_at,
        "completed_at": completed_at,
        "run_id": run_id,
        "out_dir": str(out_dir),
        "row_counts": dict(writer.counts),
    }
    (out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def _iter_tsv_rows_auto(path: Path) -> Iterator[dict[str, str]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            yield {str(key): value for key, value in row.items()}


def _predictor_columns(columns: Iterable[str]) -> list[str]:
    return [
        column
        for column in columns
        if column not in BASE_MRE_COLUMNS and column not in NUCLEOTIDE_PROFILE_COLUMNS
    ]


def _predictor_doc(column: str, *, input_path: Path, source_repo: str) -> dict:
    metadata = PREDICTOR_METADATA.get(column, {})
    return {
        "_id": f"predictor:{column}",
        "tool_id": column,
        "official_name": metadata.get("official_name", column),
        "organism": "Homo sapiens",
        "score_type": metadata.get("score_type", "MRE-level predictor score"),
        "score_direction": metadata.get("score_direction", "higher_is_stronger"),
        "score_range": None,
        "input_id_gene_type": "none",
        "canonical_id_gene_type": "ensembl_v115_optional",
        "input_id_mirna_type": "miRNA name",
        "canonical_id_mirna_type": "mirbase_v22",
        "predictor_output_path": str(input_path),
        "source_repo": source_repo,
    }


def _read_len(row: dict[str, str]) -> int | None:
    start = as_int(row.get("start"))
    end = as_int(row.get("end"))
    if start is not None and end is not None:
        return end - start + 1
    sequence = clean_nullable(row.get("gene"))
    return len(str(sequence)) if sequence is not None else None


def _parse_numeric_array(value: object) -> list[float] | None:
    text = clean_nullable(value)
    if text is None:
        return None
    if isinstance(text, list):
        return [float(item) for item in text]
    stripped = str(text).strip()
    if not stripped.startswith("[") or not stripped.endswith("]"):
        return None
    return [float(item.strip()) for item in stripped[1:-1].split(",") if item.strip()]
