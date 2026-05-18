# DBmiRNA

DBmiRNA is a transcript-aware miRNA knowledgebase. It integrates miRNA, gene, transcript, read/MRE, nucleotide-profile, experiment, predictor, literature, and provenance records into one PostgreSQL-backed schema while preserving source context.

The central design choice is that a miRNA-gene relationship is not treated as only a flat pair. DBmiRNA keeps transcript, site, and nucleotide-level evidence between the miRNA and gene anchors so region labels such as `UTR3`, `CDS`, and `INTRON` remain traceable.

## Integrated Projects

- PostGram
- TotalAnnotator
- EstimAlign
- FuNmiRBench
- genomic-region-annotator

## Data Model

DBmiRNA is organized into four PostgreSQL schemas:

- `core`: miRNAs, genes, transcripts, miRNA-gene pairs, transcript feature tracks
- `evidence`: experiments, experiment gene effects, predictors, predictor scores, miRNA recognition elements, site observations, transcript overlaps, MRE sites, nucleotide profiles
- `literature`: documents, mentions, curated assertions
- `provenance`: ingestion runs

The schema figure is available at [docs/db_schema_overview.svg](/homes/ezach01/DBmiRNA/docs/db_schema_overview.svg).

The dbdiagram.io-style editable schema source is available at [docs/schema/dbmirna.dbml](/homes/ezach01/DBmiRNA/docs/schema/dbmirna.dbml). Paste this file into dbdiagram.io to modify and re-export the figure.

The PostgreSQL DDL is available at [sql/schema.sql](/homes/ezach01/DBmiRNA/sql/schema.sql).

## Canonical Identifier Policy

Current canonical namespaces:

- miRNA: `miRBase v22`
- gene: `Ensembl v115`
- transcript: `Ensembl v115`

The active policy lives in [config/normalization.json](/homes/ezach01/DBmiRNA/config/normalization.json). DBmiRNA records both the canonical namespace and the source release for imported records.

When a source Ensembl release differs from the canonical release and no explicit release bridge has been applied, records are marked with normalization status `source_accession_unmapped`.

## Python Environment

Use `uv` for the DBmiRNA project environment.

```bash
cd /homes/ezach01/DBmiRNA

uv venv
source .venv/bin/activate
uv pip install -e '.[postgres]'
```

## PostgreSQL

A local user-owned PostgreSQL cluster can be used with this DSN:

```bash
postgresql://ezach01@/dbmirna?host=/homes/ezach01/.local/var/dbmirna-postgres&port=5433
```

Start the local PostgreSQL cluster:

```bash
/usr/lib/postgresql/16/bin/pg_ctl \
  -D /homes/ezach01/.local/var/dbmirna-postgres \
  -l /homes/ezach01/.local/var/log/dbmirna-postgres.log \
  start
```

Stop it:

```bash
/usr/lib/postgresql/16/bin/pg_ctl \
  -D /homes/ezach01/.local/var/dbmirna-postgres \
  stop
```

Open `psql`:

```bash
psql \
  -h /homes/ezach01/.local/var/dbmirna-postgres \
  -p 5433 \
  -U ezach01 \
  -d dbmirna
```

Initialize the DBmiRNA schema:

```bash
PYTHONPATH=src python -m dbmirna init-postgres \
  --dsn 'postgresql://ezach01@/dbmirna?host=/homes/ezach01/.local/var/dbmirna-postgres&port=5433'
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

Output validation checks JSON schema conformance, duplicate primary keys, and core references between collections.

## Export JSONL Bundles

Export cached Hejret AGO2 CLASH train/test MRE reads:

```bash
PYTHONPATH=src python -m dbmirna load-hejret-cache \
  --out-dir outputs/hejret_cache
```

Export a genomic-region-annotator sample:

```bash
PYTHONPATH=src python -m dbmirna load-gra \
  --out-dir outputs/gra_sample \
  --repo-root /homes/ezach01/genomic-region-annotator \
  --dataset-stem Hejret_2023 \
  --max-sites 5
```

Export a FuNmiRBench sample:

```bash
PYTHONPATH=src python -m dbmirna load-funmirbench \
  --out-dir outputs/funmirbench_sample \
  --repo-root /homes/ezach01/FuNmiRBench \
  --max-experiments 2 \
  --predictor-tool targetscan \
  --max-predictor-rows 20
```

## Load PostgreSQL

Load a validated JSONL bundle into PostgreSQL:

```bash
PYTHONPATH=src python -m dbmirna load-postgres \
  --out-dir outputs/hejret_cache \
  --dsn 'postgresql://ezach01@/dbmirna?host=/homes/ezach01/.local/var/dbmirna-postgres&port=5433'
```

The loader validates the bundle first, then upserts records in dependency order.

## Useful Commands

```bash
PYTHONPATH=src python -m dbmirna overview
PYTHONPATH=src python -m dbmirna normalization-info
PYTHONPATH=src python -m dbmirna module-info genomic_region_annotator
```

## Repository Contents

- [src/dbmirna](/homes/ezach01/DBmiRNA/src/dbmirna): Python package and CLI
- [sql/schema.sql](/homes/ezach01/DBmiRNA/sql/schema.sql): PostgreSQL schema
- [schemas/collections.schema.json](/homes/ezach01/DBmiRNA/schemas/collections.schema.json): JSONL collection schema bundle
- [schemas/collection_registry.json](/homes/ezach01/DBmiRNA/schemas/collection_registry.json): collection registry
- [integrations/module_registry.json](/homes/ezach01/DBmiRNA/integrations/module_registry.json): integration registry
- [integrations/dataset_catalog.json](/homes/ezach01/DBmiRNA/integrations/dataset_catalog.json): dataset catalog
- [docs/architecture.md](/homes/ezach01/DBmiRNA/docs/architecture.md): architecture notes
- [docs/db_schema_overview.svg](/homes/ezach01/DBmiRNA/docs/db_schema_overview.svg): schema figure
- [docs/schema/dbmirna.dbml](/homes/ezach01/DBmiRNA/docs/schema/dbmirna.dbml): editable dbdiagram.io schema source
- [docs/identifier_normalization.md](/homes/ezach01/DBmiRNA/docs/identifier_normalization.md): identifier normalization notes
