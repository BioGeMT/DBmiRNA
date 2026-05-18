# DBmiRNA Architecture

## Why This Project Exists

The source repositories do not all operate at the same biological resolution.

- `FuNmiRBench` is mainly gene-level.
- `EstimAlign` is mainly site-observation and sequence-pair level.
- `genomic-region-annotator` is transcript-region and nucleotide-composition level.
- `PostGram` is transcript-context level.
- `TotalAnnotator` is literature-document and mention level.

The database therefore cannot be designed as only `miRNAs` and `genes` with miscellaneous attachments.

## Architectural Layers

### 1. Anchor Metadata Schemas

- `mirnas`
- `genes`

These are the left and right anchors of the database. They hold stable identifiers,
canonical names or symbols, accessions, aliases, species, family or arm metadata,
normalization state, and source references.

### 2. Middle Evidence Schemas

- `transcripts`
- `site_observations`
- `site_transcript_overlaps`
- `mre_sites`
- `nucleotide_profiles`
- `transcript_feature_tracks`

These collections sit between miRNAs and genes because most biological evidence is
not purely pair-level. Transcript choice controls region labels such as `UTR3`,
`CDS`, and `INTRON`. Read or MRE rows preserve the observed interval and selected
transcript context. Nucleotide profiles store dense per-position arrays or payload
references for sequence, conservation, alignment, and region-composition data.

### 3. Gene-Level Evidence Schema

- `mirna_gene_pairs`
- `experiments`
- `experiment_gene_effects`
- `predictors`
- `predictor_scores`

`mirna_gene_pairs` is the pair-level hub. Differential-expression effects,
predictor scores, site summaries, and literature assertions attach to that hub
without flattening away transcript, site, or nucleotide context.

### 4. Literature Schema

- `literature_documents`
- `literature_mentions`
- `literature_assertions`

### 5. Provenance Schema

- `ingestion_runs`

## Key Modeling Choice

`transcripts` are first-class entities.

That choice is mandatory because:

- region identity such as `UTR3`, `CDS`, and `INTRON` depends on transcript choice
- `PostGram` already stores transcript-centered records
- `genomic-region-annotator` explicitly separates union evidence from selected-transcript summaries

## Current Manifests

The project currently stores three machine-readable planning assets:

- `schemas/collection_registry.json`
- `integrations/module_registry.json`
- `integrations/dataset_catalog.json`

These are the starting point for future ETL code and validation logic.
