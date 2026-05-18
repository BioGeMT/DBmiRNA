from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
import csv

from dbmirna.normalization import canonical_gene_document, canonical_gene_id, canonical_mirna_document, canonical_mirna_id
from dbmirna.utils import (
    JsonlBundleWriter,
    as_float,
    clean_nullable,
    compact_dict,
    effect_direction,
    iter_tsv_rows,
    now_utc_iso,
    pair_id,
    parse_geo_accession,
    parse_pubmed_id,
    stable_hash,
)


DEFAULT_REPO_ROOT = Path("/homes/ezach01/FuNmiRBench")


def _release_from_namespace(value: object) -> str | None:
    text = clean_nullable(value)
    if text is None:
        return None
    text = str(text)
    if "_" in text:
        return text.rsplit("_", 1)[-1]
    return text


def _source_ref(path: str | Path, *, source_repo: str, artifact_id: str, run_id: str) -> dict:
    return {
        "source_repo": source_repo,
        "source_path": str(path),
        "artifact_id": artifact_id,
        "run_id": run_id,
    }


def export_funmirbench(
    *,
    out_dir: str | Path,
    repo_root: str | Path = DEFAULT_REPO_ROOT,
    max_experiments: int | None = None,
    include_predictor_scores: bool = True,
    predictor_tools: list[str] | None = None,
    max_predictor_rows: int | None = None,
) -> dict:
    repo_root = Path(repo_root)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    started_at = now_utc_iso()
    run_id = f"ingest:funmirbench:{started_at}"
    writer = JsonlBundleWriter(out_dir)

    mirnas: dict[str, dict] = {}
    genes: dict[str, dict] = {}
    experiments: list[dict] = []
    predictors: list[dict] = []
    pair_rollups: dict[str, dict] = {}

    experiment_registry_path = repo_root / "metadata" / "mirna_experiment_info.tsv"
    predictor_registry_path = repo_root / "metadata" / "predictions_info.tsv"

    experiment_rows = list(iter_tsv_rows(experiment_registry_path))
    if max_experiments is not None:
        experiment_rows = experiment_rows[:max_experiments]

    for row in experiment_rows:
        mirna_name = row["mirna_name"].strip()
        mirna_id, _ = canonical_mirna_id(
            name=mirna_name,
            accession=None,
            source_repo="FuNmiRBench",
        )
        experiment_source_ref = _source_ref(
            experiment_registry_path,
            source_repo="FuNmiRBench",
            artifact_id="funmirbench_experiment_registry",
            run_id=run_id,
        )
        mirna = mirnas.get(mirna_id)
        if mirna is None:
            mirna = canonical_mirna_document(
                name=mirna_name,
                species=row["organism"].strip(),
                sequence=row["mirna_sequence"].strip(),
                accession=None,
                family=None,
                source_repo="FuNmiRBench",
                source_ref=experiment_source_ref,
            )
            mirnas[mirna_id] = mirna
        else:
            mirna["source_refs"].append(experiment_source_ref)

        dataset_id = row["id"].strip()
        experiment_id = f"experiment:{dataset_id}"
        de_path = (repo_root / row["de_table_path"].strip()).resolve()
        experiment_doc = {
            "_id": experiment_id,
            "dataset_id": dataset_id,
            "mirna_id": mirna_id,
            "mirna_name_raw": mirna_name,
            "mirna_sequence": row["mirna_sequence"].strip(),
            "article_pubmed_id": parse_pubmed_id(row.get("article_pubmed_id")),
            "geo_accession": parse_geo_accession(row.get("gse_url")),
            "organism": row["organism"].strip(),
            "tested_cell_line": clean_nullable(row.get("tested_cell_line")),
            "tissue": clean_nullable(row.get("tissue")),
            "method": clean_nullable(row.get("method")),
            "experiment_type": row["experiment_type"].strip(),
            "treatment": clean_nullable(row.get("treatment")),
            "de_table_path": str(de_path),
            "source_repo": "FuNmiRBench",
            "run_id": run_id,
        }
        experiments.append(compact_dict(experiment_doc))

        for de_index, de_row in enumerate(_iter_funmirbench_de_rows(de_path), start=1):
            raw_gene_id = clean_nullable(de_row.get("gene_id"))
            if raw_gene_id is None:
                continue
            gene_id, _ = canonical_gene_id(
                accession=str(raw_gene_id),
                source_repo="FuNmiRBench",
                source_release="v109",
            )
            if gene_id not in genes:
                genes[gene_id] = canonical_gene_document(
                    accession=str(raw_gene_id),
                    symbol=str(raw_gene_id),
                    species=row["organism"].strip(),
                    source_repo="FuNmiRBench",
                    source_release="v109",
                    source_ref=_source_ref(
                        de_path,
                        source_repo="FuNmiRBench",
                        artifact_id="funmirbench_de_table",
                        run_id=run_id,
                    ),
                )
            pair = pair_id(mirna_id, gene_id)
            effect_doc = {
                "_id": f"effect:{dataset_id}:{raw_gene_id}:{stable_hash(de_index, de_row)}",
                "experiment_id": experiment_id,
                "pair_id": pair,
                "mirna_id": mirna_id,
                "gene_id": gene_id,
                "logFC": as_float(de_row.get("logFC")),
                "FDR": as_float(de_row.get("FDR")),
                "PValue": as_float(de_row.get("PValue")),
                "logCPM": as_float(de_row.get("logCPM")),
                "F_statistic": as_float(de_row.get("F")),
                "effect_direction": effect_direction(as_float(de_row.get("logFC"))),
                "passes_default_threshold": None,
                "raw_row": de_row,
                "run_id": run_id,
            }
            writer.write("experiment_gene_effects", compact_dict(effect_doc))

            rollup = pair_rollups.setdefault(
                pair,
                {
                    "_id": pair,
                    "mirna_id": mirna_id,
                    "gene_id": gene_id,
                    "species": row["organism"].strip(),
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
            rollup["evidence_counts"]["experiment_gene_effects"] += 1
            rollup["support_summary"]["has_experiment_support"] = True
            rollup["source_refs"].append(
                _source_ref(
                    de_path,
                    source_repo="FuNmiRBench",
                    artifact_id="funmirbench_de_table",
                    run_id=run_id,
                )
            )

    predictor_rows = list(iter_tsv_rows(predictor_registry_path))
    selected_predictor_tools = set(predictor_tools or [])
    if selected_predictor_tools:
        predictor_rows = [row for row in predictor_rows if row["tool_id"] in selected_predictor_tools]

    for row in predictor_rows:
        predictor_id = f"predictor:{row['tool_id'].strip()}"
        predictors.append(
            compact_dict(
                {
                    "_id": predictor_id,
                    "tool_id": row["tool_id"].strip(),
                    "official_name": row["official_name"].strip(),
                    "organism": row["organism"].strip(),
                    "score_type": row["score_type"].strip(),
                    "score_direction": row["score_direction"].strip(),
                    "score_range": clean_nullable(row.get("score_range")),
                    "input_id_gene_type": row["input_id_gene_type"].strip(),
                    "canonical_id_gene_type": row["canonical_id_gene_type"].strip(),
                    "input_id_mirna_type": row["input_id_mirna_type"].strip(),
                    "canonical_id_mirna_type": row["canonical_id_mirna_type"].strip(),
                    "predictor_output_path": str((repo_root / row["predictor_output_path"].strip()).resolve()),
                    "source_repo": "FuNmiRBench",
                }
            )
        )

        if not include_predictor_scores:
            continue

        predictor_path = (repo_root / row["predictor_output_path"].strip()).resolve()
        for index, score_row in enumerate(iter_tsv_rows(predictor_path), start=1):
            if max_predictor_rows is not None and index > max_predictor_rows:
                break
            mirna_name = clean_nullable(score_row.get("miRNA_Name"))
            gene_accession = clean_nullable(score_row.get("Ensembl_ID"))
            if mirna_name is None or gene_accession is None:
                continue

            mirna_id, _ = canonical_mirna_id(
                name=str(mirna_name),
                accession=clean_nullable(score_row.get("miRNA_ID")),
                source_repo="FuNmiRBench",
            )
            gene_id, _ = canonical_gene_id(
                accession=str(gene_accession),
                source_repo="FuNmiRBench",
                source_release=_release_from_namespace(row.get("canonical_id_gene_type")),
            )

            mirna = mirnas.get(mirna_id)
            if mirna is None:
                mirna = canonical_mirna_document(
                    name=str(mirna_name),
                    species=row["organism"].strip(),
                    sequence=None,
                    accession=clean_nullable(score_row.get("miRNA_ID")),
                    family=None,
                    source_repo="FuNmiRBench",
                    source_ref=_source_ref(
                        predictor_path,
                        source_repo="FuNmiRBench",
                        artifact_id="funmirbench_predictor_scores",
                        run_id=run_id,
                    ),
                )
                mirnas[mirna_id] = mirna
            if clean_nullable(score_row.get("miRNA_ID")) and not mirna.get("canonical_accession"):
                mirna["canonical_accession"] = str(score_row["miRNA_ID"]).strip()
                mirna["normalization"]["source_accession"] = str(score_row["miRNA_ID"]).strip()
                mirna["normalization"]["status"] = "canonical_accession"
            mirna["source_refs"].append(
                _source_ref(
                    predictor_path,
                    source_repo="FuNmiRBench",
                    artifact_id="funmirbench_predictor_scores",
                    run_id=run_id,
                )
            )

            if gene_id not in genes:
                symbol = clean_nullable(score_row.get("Gene_Name")) or str(gene_accession)
                genes[gene_id] = canonical_gene_document(
                    accession=str(gene_accession),
                    symbol=str(symbol),
                    species=row["organism"].strip(),
                    source_repo="FuNmiRBench",
                    source_release=_release_from_namespace(row.get("canonical_id_gene_type")),
                    source_ref=_source_ref(
                        predictor_path,
                        source_repo="FuNmiRBench",
                        artifact_id="funmirbench_predictor_scores",
                        run_id=run_id,
                    ),
                )

            pair = pair_id(mirna_id, gene_id)
            writer.write(
                "predictor_scores",
                compact_dict(
                    {
                        "_id": f"score:{row['tool_id']}:{mirna_name}:{gene_accession}:{stable_hash(index, score_row)}",
                        "predictor_id": predictor_id,
                        "pair_id": pair,
                        "mirna_id": mirna_id,
                        "gene_id": gene_id,
                        "score_raw": as_float(score_row.get("Score")),
                        "score_direction": row["score_direction"].strip(),
                        "score_rank_within_mirna": None,
                        "source_row": score_row,
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
                    "species": row["organism"].strip(),
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
            rollup["evidence_counts"]["predictor_scores"] += 1
            rollup["support_summary"]["has_predictor_support"] = True
            rollup["source_refs"].append(
                _source_ref(
                    predictor_path,
                    source_repo="FuNmiRBench",
                    artifact_id="funmirbench_predictor_scores",
                    run_id=run_id,
                )
            )

    writer.write_many("mirnas", mirnas.values())
    writer.write_many("genes", genes.values())
    writer.write_many("experiments", experiments)
    writer.write_many("predictors", predictors)

    pair_docs = []
    for doc in pair_rollups.values():
        pair_docs.append(
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
        )
    writer.write_many("mirna_gene_pairs", pair_docs)

    completed_at = now_utc_iso()
    run_doc = {
        "_id": run_id,
        "source_repo": "FuNmiRBench",
        "source_path": str(repo_root),
        "source_release": None,
        "started_at": started_at,
        "completed_at": completed_at,
        "transform_version": "0.1.0",
        "checksums": {},
        "row_counts": dict(writer.counts),
        "notes": "FunMiRBench export to DBmiRNA JSONL bundle.",
    }
    writer.write("ingestion_runs", run_doc)
    writer.close()

    manifest = {
        "module": "funmirbench",
        "repo_root": str(repo_root),
        "started_at": started_at,
        "completed_at": completed_at,
        "run_id": run_id,
        "out_dir": str(out_dir),
        "options": {
            "max_experiments": max_experiments,
            "include_predictor_scores": include_predictor_scores,
            "predictor_tools": predictor_tools or [],
            "max_predictor_rows": max_predictor_rows,
        },
        "row_counts": dict(writer.counts),
    }
    (out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def _iter_funmirbench_de_rows(path: Path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        header = next(reader)
        for row in reader:
            if not row:
                continue
            if len(row) == len(header) + 1:
                values = {"gene_id": row[0]}
                values.update({header[idx]: row[idx + 1] for idx in range(len(header))})
                yield values
                continue
            if len(row) == len(header):
                values = {header[idx]: row[idx] for idx in range(len(header))}
                values["gene_id"] = values.get("gene_id")
                yield values
