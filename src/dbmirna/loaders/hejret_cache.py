from __future__ import annotations

import json
from pathlib import Path

from dbmirna.normalization import canonical_mirna_document, canonical_mirna_id
from dbmirna.utils import (
    JsonlBundleWriter,
    as_int,
    clean_nullable,
    compact_dict,
    iter_tsv_rows,
    now_utc_iso,
    stable_hash,
)


DEFAULT_CACHE_ROOT = Path("/homes/ezach01/.miRBench/datasets/14501607/AGO2_CLASH_Hejret2023")


def export_hejret_cache(
    *,
    out_dir: str | Path,
    cache_root: str | Path = DEFAULT_CACHE_ROOT,
    splits: list[str] | None = None,
    max_rows_per_split: int | None = None,
) -> dict:
    cache_root = Path(cache_root)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    selected_splits = splits or ["train", "test"]
    started_at = now_utc_iso()
    run_id = f"ingest:hejret_cache:{started_at}"
    writer = JsonlBundleWriter(out_dir)

    mirnas: dict[str, dict] = {}

    for split in selected_splits:
        dataset_path = cache_root / split / "dataset.tsv"
        source_ref = {
            "source_repo": "EstimAlign",
            "source_path": str(dataset_path),
            "artifact_id": "hejret_cache_dataset",
            "run_id": run_id,
        }
        for row_index, row in enumerate(iter_tsv_rows(dataset_path), start=1):
            if max_rows_per_split is not None and row_index > max_rows_per_split:
                break

            mirna_name = row["noncodingRNA_name"].strip()
            mirna_id, _ = canonical_mirna_id(
                name=mirna_name,
                accession=None,
                source_repo="EstimAlign",
            )
            if mirna_id not in mirnas:
                mirnas[mirna_id] = canonical_mirna_document(
                    name=mirna_name,
                    species="Homo sapiens",
                    sequence=row["noncodingRNA"].strip(),
                    accession=None,
                    family=clean_nullable(row.get("noncodingRNA_fam")),
                    source_repo="EstimAlign",
                    source_ref=source_ref,
                )

            start = as_int(row.get("start"))
            end = as_int(row.get("end"))
            read_len = end - start + 1 if start is not None and end is not None else None
            mre_id = f"mre:hejret:{split}:{stable_hash(row_index, row)}"
            writer.write(
                "mirna_recognition_elements",
                compact_dict(
                    {
                        "_id": mre_id,
                        "source_dataset": "AGO2_CLASH_Hejret2023",
                        "source_repo": "EstimAlign",
                        "source_split": split,
                        "source_row_index": row_index,
                        "label": as_int(row.get("label")),
                        "mirna_id": mirna_id,
                        "mirna_name_raw": mirna_name,
                        "mirna_family_raw": clean_nullable(row.get("noncodingRNA_fam")),
                        "mirna_sequence_raw": row["noncodingRNA"].strip(),
                        "gene_id": None,
                        "gene_name_raw": None,
                        "gene_cluster_id": clean_nullable(row.get("gene_cluster_ID")),
                        "target_sequence_raw": row["gene"].strip(),
                        "feature_label_raw": clean_nullable(row.get("feature")),
                        "chr": clean_nullable(row.get("chr")),
                        "start": start,
                        "end": end,
                        "strand": clean_nullable(row.get("strand")),
                        "read_len": read_len,
                        "experiment_type": "AGO2_CLASH",
                        "organism": "Homo sapiens",
                        "raw_row": row,
                        "run_id": run_id,
                    }
                ),
            )

    writer.write_many("mirnas", mirnas.values())
    completed_at = now_utc_iso()
    writer.write(
        "ingestion_runs",
        {
            "_id": run_id,
            "source_repo": "EstimAlign",
            "source_path": str(cache_root),
            "source_release": "cache_local",
            "started_at": started_at,
            "completed_at": completed_at,
            "transform_version": "0.1.0",
            "checksums": {},
            "row_counts": dict(writer.counts),
            "notes": "Hejret AGO2 CLASH train/test cache export.",
        },
    )
    writer.close()

    manifest = {
        "module": "hejret_cache",
        "cache_root": str(cache_root),
        "started_at": started_at,
        "completed_at": completed_at,
        "run_id": run_id,
        "out_dir": str(out_dir),
        "options": {
            "splits": selected_splits,
            "max_rows_per_split": max_rows_per_split,
        },
        "row_counts": dict(writer.counts),
    }
    (out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
