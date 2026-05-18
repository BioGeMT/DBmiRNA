from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from dbmirna.normalization import (
    canonical_gene_document,
    canonical_gene_id,
    canonical_mirna_document,
    canonical_mirna_id,
    canonical_transcript_document,
    canonical_transcript_id,
)
from dbmirna.utils import (
    JsonlBundleWriter,
    as_int,
    clean_nullable,
    compact_dict,
    iter_tsv_rows,
    now_utc_iso,
    pair_id,
)


DEFAULT_REPO_ROOT = Path("/homes/ezach01/genomic-region-annotator")


def _source_ref(path: str | Path, *, source_repo: str, artifact_id: str, run_id: str) -> dict:
    return {
        "source_repo": source_repo,
        "source_path": str(path),
        "artifact_id": artifact_id,
        "run_id": run_id,
    }


def _obs_key(dataset_name: str, raw_id: str) -> str:
    return f"obs:gra:{dataset_name}:{raw_id}"


def export_genomic_region_annotator(
    *,
    out_dir: str | Path,
    repo_root: str | Path = DEFAULT_REPO_ROOT,
    dataset_stem: str = "Hejret_2023",
    max_sites: int | None = None,
) -> dict:
    repo_root = Path(repo_root)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    started_at = now_utc_iso()
    run_id = f"ingest:genomic_region_annotator:{started_at}"
    writer = JsonlBundleWriter(out_dir)

    raw_path = repo_root / "data" / "raw" / f"{dataset_stem}.tsv"
    step1_tx_path = repo_root / "data" / "processed" / "step1" / f"{dataset_stem}_annotated_transcripts.tsv"
    step1_matrix_path = repo_root / "data" / "processed" / "step1" / f"{dataset_stem}_annotated_matrix.tsv"
    step2_summary_path = repo_root / "data" / "processed" / "step2" / f"{dataset_stem}_annotated_site_summary.tsv"

    mirnas: dict[str, dict] = {}
    genes: dict[str, dict] = {}
    transcripts: dict[str, dict] = {}
    pair_rollups: dict[str, dict] = {}
    raw_lookup: dict[str, dict] = {}

    for index, row in enumerate(iter_tsv_rows(raw_path), start=1):
        if max_sites is not None and index > max_sites:
            break
        raw_id = f"{index:04d}"
        raw_lookup[raw_id] = row
        mirna_name = row["noncodingRNA_name"].strip()
        raw_source_ref = _source_ref(
            raw_path,
            source_repo="genomic-region-annotator",
            artifact_id="gra_raw_intervals",
            run_id=run_id,
        )
        mirna_id, _ = canonical_mirna_id(
            name=mirna_name,
            accession=None,
            source_repo="genomic-region-annotator",
        )
        if mirna_id not in mirnas:
            mirnas[mirna_id] = canonical_mirna_document(
                name=mirna_name,
                species="Homo sapiens",
                sequence=row["noncodingRNA"].strip(),
                accession=None,
                family=clean_nullable(row.get("noncodingRNA_fam")),
                source_repo="genomic-region-annotator",
                source_ref=raw_source_ref,
            )

        writer.write(
            "site_observations",
            compact_dict(
                {
                    "_id": _obs_key(dataset_stem, raw_id),
                    "source_dataset": f"gra:{dataset_stem}",
                    "source_repo": "genomic-region-annotator",
                    "mirna_id": mirna_id,
                    "mirna_name_raw": mirna_name,
                    "mirna_family_raw": clean_nullable(row.get("noncodingRNA_fam")),
                    "mirna_sequence_raw": row["noncodingRNA"].strip(),
                    "target_sequence_raw": row["gene"].strip(),
                    "feature_label_raw": clean_nullable(row.get("feature")),
                    "label": as_int(row.get("label")),
                    "chr": clean_nullable(row.get("chr")),
                    "start": as_int(row.get("start")),
                    "end": as_int(row.get("end")),
                    "strand": clean_nullable(row.get("strand")),
                    "read_len": as_int(row.get("end")) - as_int(row.get("start")) + 1 if as_int(row.get("start")) is not None and as_int(row.get("end")) is not None else None,
                    "gene_cluster_id": clean_nullable(row.get("gene_cluster_ID")),
                    "raw_row": row,
                    "run_id": run_id,
                }
            ),
        )

    for index, row in enumerate(iter_tsv_rows(step1_tx_path), start=1):
        raw_id = row["id"].strip()
        if max_sites is not None and as_int(raw_id) is not None and int(raw_id) > max_sites:
            continue
        gene_accession = row["gene_id"].strip()
        overlap_source_ref = _source_ref(
            step1_tx_path,
            source_repo="genomic-region-annotator",
            artifact_id="gra_step1_transcript_overlaps",
            run_id=run_id,
        )
        gene_id, _ = canonical_gene_id(
            accession=gene_accession,
            source_repo="genomic-region-annotator",
            source_release="v115",
        )
        if gene_id not in genes:
            gene_name = clean_nullable(row.get("gene_name")) or gene_accession
            genes[gene_id] = canonical_gene_document(
                accession=gene_accession,
                symbol=str(gene_name),
                species="Homo sapiens",
                source_repo="genomic-region-annotator",
                source_release="v115",
                source_ref=overlap_source_ref,
            )

        transcript_accession = row["transcript_id"].strip()
        transcript_id, _ = canonical_transcript_id(
            accession=transcript_accession,
            source_repo="genomic-region-annotator",
            source_release="v115",
        )
        if transcript_id not in transcripts:
            transcripts[transcript_id] = compact_dict(
                canonical_transcript_document(
                    accession=transcript_accession,
                    gene_id=gene_id,
                    gene_symbol=clean_nullable(row.get("gene_name")),
                    species="Homo sapiens",
                    genome_build="GRCh38",
                    tx_start=as_int(row.get("tx_start")),
                    tx_end=as_int(row.get("tx_end")),
                    strand=clean_nullable(row.get("transcript_strand")),
                    source_repo="genomic-region-annotator",
                    source_release="v115",
                    source_ref=overlap_source_ref,
                )
            )

        writer.write(
            "site_transcript_overlaps",
            compact_dict(
                {
                    "_id": f"ovl:{dataset_stem}:{raw_id}:{transcript_accession}",
                    "observation_id": _obs_key(dataset_stem, raw_id),
                    "transcript_id": transcript_id,
                    "gene_id": gene_id,
                    "gene_name_raw": clean_nullable(row.get("gene_name")),
                    "contained_100pct": str(row["contained_100pct"]).strip() == "1",
                    "overlap_tx_bp": as_int(row.get("overlap_tx_bp")) or 0,
                    "overlap_exon_bp": as_int(row.get("overlap_exon_bp")) or 0,
                    "overlap_cds_bp": as_int(row.get("overlap_cds_bp")) or 0,
                    "overlap_utr5_bp": as_int(row.get("overlap_utr5_bp")) or 0,
                    "overlap_utr3_bp": as_int(row.get("overlap_utr3_bp")) or 0,
                    "read_start_in_tx_1based": as_int(row.get("read_start_in_tx_1based")),
                    "read_end_in_tx_1based": as_int(row.get("read_end_in_tx_1based")),
                    "overlap_start_genome_1based": as_int(row.get("overlap_start_genome_1based")),
                    "overlap_end_genome_1based": as_int(row.get("overlap_end_genome_1based")),
                    "run_id": run_id,
                }
            ),
        )

    current_id: str | None = None
    current_rows: list[dict[str, str]] = []
    for row in iter_tsv_rows(step1_matrix_path):
        raw_id = row["id"].strip()
        if max_sites is not None and as_int(raw_id) is not None and int(raw_id) > max_sites:
            continue
        if current_id is None:
            current_id = raw_id
        if raw_id != current_id:
            writer.write("nucleotide_profiles", _matrix_profile(dataset_stem, current_id, current_rows, step1_matrix_path, run_id))
            current_id = raw_id
            current_rows = []
        current_rows.append(row)
    if current_id is not None and current_rows:
        writer.write("nucleotide_profiles", _matrix_profile(dataset_stem, current_id, current_rows, step1_matrix_path, run_id))

    for row in iter_tsv_rows(step2_summary_path):
        raw_id = row["id"].strip()
        if max_sites is not None and as_int(raw_id) is not None and int(raw_id) > max_sites:
            continue
        mirna_name = row["noncodingRNA_name"].strip()
        mirna_id, _ = canonical_mirna_id(
            name=mirna_name,
            accession=None,
            source_repo="genomic-region-annotator",
        )
        gene_accession = row["selected_gene_id"].strip()
        transcript_accession = row["selected_transcript_id"].strip()
        gene_id, _ = canonical_gene_id(
            accession=gene_accession,
            source_repo="genomic-region-annotator",
            source_release="v115",
        )
        transcript_id, _ = canonical_transcript_id(
            accession=transcript_accession,
            source_repo="genomic-region-annotator",
            source_release="v115",
        )
        pair = pair_id(mirna_id, gene_id)
        writer.write(
            "mre_sites",
            compact_dict(
                {
                    "_id": f"mre:{dataset_stem}:{raw_id}:{transcript_accession}",
                    "pair_id": pair,
                    "mirna_id": mirna_id,
                    "gene_id": gene_id,
                    "transcript_id": transcript_id,
                    "observation_id": _obs_key(dataset_stem, raw_id),
                    "chr": row["chr"].strip(),
                    "start": as_int(row.get("start")),
                    "end": as_int(row.get("end")),
                    "strand": row["strand"].strip(),
                    "read_len": as_int(row.get("read_len")),
                    "selection_policy": row["policy"].strip(),
                    "dominance_mode": row["dominance"].strip(),
                    "selected_gene_name": clean_nullable(row.get("selected_gene_name")),
                    "dominant_region_selected": row["dominant_region_selected"].strip(),
                    "regions_present_selected": row["regions_present_selected"].strip(),
                    "dominant_region_union": row["dominant_region_union"].strip(),
                    "regions_present_union": row["regions_present_union"].strip(),
                    "bp_utr3_selected": as_int(row.get("bp_utr3_selected")),
                    "bp_cds_selected": as_int(row.get("bp_cds_selected")),
                    "bp_utr5_selected": as_int(row.get("bp_utr5_selected")),
                    "bp_exon_other_selected": as_int(row.get("bp_exon_other_selected")),
                    "bp_intron_selected": as_int(row.get("bp_intron_selected")),
                    "bp_intergenic_selected": as_int(row.get("bp_intergenic_selected")),
                    "bp_utr3_union": as_int(row.get("bp_utr3_union")),
                    "bp_cds_union": as_int(row.get("bp_cds_union")),
                    "bp_utr5_union": as_int(row.get("bp_utr5_union")),
                    "bp_exon_other_union": as_int(row.get("bp_exon_other_union")),
                    "bp_intron_union": as_int(row.get("bp_intron_union")),
                    "bp_intergenic_union": as_int(row.get("bp_intergenic_union")),
                    "ambiguous_union_vs_selected": str(row["ambiguous_union_vs_selected"]).strip() == "1",
                    "n_passing_transcripts": as_int(row.get("n_passing_transcripts")) or 0,
                    "run_id": run_id,
                }
            ),
        )

        rollup = pair_rollups.setdefault(
            pair,
            {
                "_id": pair,
                "mirna_id": mirna_id,
                "gene_id": gene_id,
                "species": "Homo sapiens",
                "evidence_counts": defaultdict(int),
                "best_supported_transcript_ids": [],
                "support_summary": {
                    "has_experiment_support": False,
                    "has_predictor_support": False,
                    "has_site_support": False,
                    "has_literature_assertion": False,
                },
                "source_refs": [],
            },
        )
        rollup["evidence_counts"]["mre_sites"] += 1
        rollup["evidence_counts"]["site_observations"] += 1
        rollup["support_summary"]["has_site_support"] = True
        if transcript_id not in rollup["best_supported_transcript_ids"]:
            rollup["best_supported_transcript_ids"].append(transcript_id)
        rollup["source_refs"].append(
            _source_ref(
                step2_summary_path,
                source_repo="genomic-region-annotator",
                artifact_id="gra_step2_site_summary",
                run_id=run_id,
            )
        )

    writer.write_many("mirnas", mirnas.values())
    writer.write_many("genes", genes.values())
    writer.write_many("transcripts", transcripts.values())
    writer.write_many(
        "mirna_gene_pairs",
        [
            {
                "_id": doc["_id"],
                "mirna_id": doc["mirna_id"],
                "gene_id": doc["gene_id"],
                "species": doc["species"],
                "evidence_counts": dict(doc["evidence_counts"]),
                "best_supported_transcript_ids": doc["best_supported_transcript_ids"],
                "support_summary": doc["support_summary"],
                "source_refs": doc["source_refs"],
            }
            for doc in pair_rollups.values()
        ],
    )

    completed_at = now_utc_iso()
    writer.write(
        "ingestion_runs",
        {
            "_id": run_id,
            "source_repo": "genomic-region-annotator",
            "source_path": str(repo_root),
            "source_release": "repo_local",
            "started_at": started_at,
            "completed_at": completed_at,
            "transform_version": "0.1.0",
            "checksums": {},
            "row_counts": dict(writer.counts),
            "notes": f"GRA export for dataset {dataset_stem}.",
        },
    )
    writer.close()

    manifest = {
        "module": "genomic_region_annotator",
        "repo_root": str(repo_root),
        "dataset_stem": dataset_stem,
        "started_at": started_at,
        "completed_at": completed_at,
        "run_id": run_id,
        "out_dir": str(out_dir),
        "options": {
            "max_sites": max_sites
        },
        "row_counts": dict(writer.counts),
    }
    (out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def _matrix_profile(dataset_stem: str, raw_id: str, rows: list[dict[str, str]], source_path: Path, run_id: str) -> dict:
    read_len = as_int(rows[0].get("read_len")) or 0
    values = []
    for row in rows:
        nt_values = []
        for index in range(1, read_len + 1):
            nt_values.append(as_int(row.get(f"nt_{index}")) or 0)
        values.append(
            {
                "region": row["region"].strip(),
                "nt": nt_values,
            }
        )
    return {
        "_id": f"profile:{dataset_stem}:{raw_id}:region_union_matrix",
        "entity_type": "site_observation",
        "entity_id": _obs_key(dataset_stem, raw_id),
        "profile_type": "region_union_matrix",
        "length": read_len,
        "storage_mode": "inline",
        "values": values,
        "payload_ref": None,
        "metadata": {
            "source_repo": "genomic-region-annotator",
            "source_path": str(source_path),
            "dataset_stem": dataset_stem,
        },
        "run_id": run_id,
    }
