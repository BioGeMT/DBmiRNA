# DBmiRNA

DBmiRNA is a transcript-aware miRNA knowledgebase. It integrates miRNA and gene metadata with transcript-level, miRNA-recognition-element-level, nucleotide-level, and gene-level evidence while preserving source context.

The central design choice is that miRNAs and genes are the two metadata anchors. Evidence can then be attached at three middle layers: transcript level, miRNA recognition element (MRE) level, and nucleotide level. Gene-level evidence from FuNmiRBench is kept separately from MRE-level evidence from MirBench/miRBench-style datasets and predictors.

## Integrated Projects

- PostGram
- TotalAnnotator
- EstimAlign
- FuNmiRBench
- genomic-region-annotator

## Data Model

DBmiRNA starts with two canonical metadata collections:

- `mirnas`: miRNA metadata annotated to `miRBase v22`
- `genes`: gene metadata annotated to `Ensembl v115`

The middle evidence layers are:

- transcript level: `transcripts`, `transcript_feature_tracks`, `site_transcript_overlaps`
- MRE level: `mirna_recognition_elements`, `mre_sites`, `mre_predictor_scores`
- nucleotide level: `nucleotide_profiles`

Gene-level FuNmiRBench evidence is represented separately:

- `experiment_gene_effects`: gene-level RNA-seq differential expression effects
- `predictor_scores`: gene-level miRNA-gene predictor scores

DBmiRNA is organized into four PostgreSQL schemas:

- `core`: miRNAs, genes, transcripts, miRNA-gene pairs, transcript feature tracks
- `evidence`: gene-level RNA-seq effects, gene-level predictor scores, MRE records, MRE-level predictor scores, site/transcript overlaps, MRE sites, nucleotide profiles
- `literature`: documents, mentions, curated assertions
- `provenance`: ingestion runs

The schema figure is available at [docs/db_schema_overview.svg](docs/db_schema_overview.svg).

The dbdiagram.io-style editable schema source is available at [docs/schema/dbmirna.dbml](docs/schema/dbmirna.dbml). Paste this file into dbdiagram.io to modify and re-export the figure.

The PostgreSQL DDL is available at [sql/schema.sql](sql/schema.sql).

## Canonical Identifier Policy

Current canonical namespaces:

- miRNA: `miRBase v22`
- gene: `Ensembl v115`
- transcript: `Ensembl v115`

The active policy lives in [config/normalization.json](config/normalization.json). DBmiRNA records both the canonical namespace and the source release for imported records.

When a source Ensembl release differs from the canonical release and no explicit release bridge has been applied, records are marked with normalization status `source_accession_unmapped`.

## Python Environment

Use `uv` for the DBmiRNA project environment.

```bash
cd DBmiRNA

uv venv
source .venv/bin/activate
uv pip install -e '.[postgres]'
```

## PostgreSQL

Create a PostgreSQL database and pass its DSN to the DBmiRNA CLI. For example, for a local PostgreSQL server:

```bash
createdb dbmirna
export DBMIRNA_DSN='postgresql:///dbmirna'
```

Initialize the DBmiRNA schema:

```bash
PYTHONPATH=src python -m dbmirna init-postgres --dsn "$DBMIRNA_DSN"
```

## Validation

Validate project manifests:

```bash
PYTHONPATH=src python -m dbmirna validate
```

Validate an exported JSONL bundle:

```bash
PYTHONPATH=src python -m dbmirna validate-outputs \
  --out-dir outputs/gra_sample
```

Use strict bundle validation when you want to confirm that a bundle is loadable as data, not just structurally valid:

```bash
PYTHONPATH=src python -m dbmirna validate-outputs \
  --out-dir outputs/gra_sample \
  --require-data-collection
```

Output validation checks JSON schema conformance, duplicate primary keys, known collection names, empty collection files, `run_id` references to ingestion runs, and core references between collections. Strict validation also requires at least one non-provenance data collection.

## Export JSONL Bundles

Export cached Hejret AGO2 CLASH train/test MRE reads:

```bash
PYTHONPATH=src python -m dbmirna load-hejret-cache \
  --out-dir outputs/hejret_cache \
  --cache-root /path/to/AGO2_CLASH_Hejret2023
```

Export a Zenodo MRE TSV or TSV.GZ file. Columns matching the base MRE layout are exported to `mirna_recognition_elements`; numeric predictor columns such as `TargetScanCnn_McGeary2019`, `miRBenchCNN_Manakov`, and `miRBind2` are exported to `mre_predictor_scores`; per-nucleotide conservation arrays such as `gene_phyloP` and `gene_phastCons` are exported to `nucleotide_profiles`.

```bash
PYTHONPATH=src python -m dbmirna load-zenodo-mre-tsv \
  --out-dir outputs/hejret_test_predictions \
  --input-path /path/to/AGO2_CLASH_Hejret2023_test_predictions.tsv \
  --dataset-id AGO2_CLASH_Hejret2023_test_predictions \
  --source-url https://zenodo.org/records/18682335 \
  --source-split test \
  --experiment-type AGO2_CLASH
```

```bash
PYTHONPATH=src python -m dbmirna load-zenodo-mre-tsv \
  --out-dir outputs/manakov_leftout \
  --input-path /path/to/AGO2_eCLIP_Manakov2022_leftout.tsv.gz \
  --dataset-id AGO2_eCLIP_Manakov2022_leftout \
  --source-url https://zenodo.org/records/14734014 \
  --source-split leftout \
  --experiment-type AGO2_eCLIP
```

Export a genomic-region-annotator sample:

```bash
PYTHONPATH=src python -m dbmirna load-gra \
  --out-dir outputs/gra_sample \
  --repo-root /path/to/genomic-region-annotator \
  --dataset-stem Hejret_2023 \
  --max-sites 5
```

Export a FuNmiRBench sample:

```bash
PYTHONPATH=src python -m dbmirna load-funmirbench \
  --out-dir outputs/funmirbench_sample \
  --repo-root /path/to/FuNmiRBench \
  --max-experiments 2 \
  --predictor-tool targetscan \
  --max-predictor-rows 20
```

## Load PostgreSQL

Load a validated JSONL bundle into PostgreSQL:

```bash
PYTHONPATH=src python -m dbmirna load-postgres \
  --out-dir outputs/hejret_cache \
  --dsn "$DBMIRNA_DSN"
```

The loader applies strict bundle validation first, then upserts records in dependency order.

## Useful Commands

```bash
PYTHONPATH=src python -m dbmirna overview
PYTHONPATH=src python -m dbmirna normalization-info
PYTHONPATH=src python -m dbmirna module-info genomic_region_annotator
```

## Repository Contents

- [src/dbmirna](src/dbmirna): Python package and CLI
- [sql/schema.sql](sql/schema.sql): PostgreSQL schema
- [schemas/collections.schema.json](schemas/collections.schema.json): JSONL collection schema bundle
- [schemas/mre_predictor_scores.schema.json](schemas/mre_predictor_scores.schema.json): MRE-level predictor score schema
- [schemas/collection_registry.json](schemas/collection_registry.json): collection registry
- [integrations/module_registry.json](integrations/module_registry.json): integration registry
- [integrations/dataset_catalog.json](integrations/dataset_catalog.json): dataset catalog
- [docs/architecture.md](docs/architecture.md): architecture notes
- [docs/db_schema_overview.svg](docs/db_schema_overview.svg): schema figure
- [docs/schema/dbmirna.dbml](docs/schema/dbmirna.dbml): editable dbdiagram.io schema source
- [docs/identifier_normalization.md](docs/identifier_normalization.md): identifier normalization notes