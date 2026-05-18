# Identifier Normalization

## Purpose

DBmiRNA uses a dedicated normalization layer so canonical `miRNA`, `gene`, and `transcript` IDs do not have to be hard-coded inside each loader.

The active policy is stored in:

- [config/normalization.json](/homes/ezach01/DBmiRNA/config/normalization.json:1)

## Where We Stand Today

The current canonical position is:

- miRNAs: `miRBase v22`
- genes: `Ensembl v115`
- transcripts: `Ensembl v115`

This is the current BioGeMT DBmiRNA target namespace, not a claim that every source repository already uses those same releases internally.

## Source-Aware Reality

DBmiRNA keeps track of the fact that source repositories do not all live in the same release world.

Current examples:

- `FuNmiRBench`
  gene identifiers are currently configured with source release `v109`
- `genomic-region-annotator`
  genes and transcripts are currently configured with source release `v115`

That source-side release context is preserved in each entity's `normalization` block.

## How IDs Are Built

DBmiRNA separates:

1. canonical namespace choice
2. source release context
3. source identifier evidence
4. normalization status

Current internal ID patterns are:

- miRNAs: `mirna:mirbase_v22:<miRNA_name>`
- genes: `gene:ensembl_v115:<ENSG...>`
- transcripts: `tx:ensembl_v115:<ENST...>`

For miRNAs, DBmiRNA currently uses the active miRBase release plus the miRNA name as the internal stable join key. If a miRBase accession is present, it is preserved in the entity document and in the normalization metadata. This avoids splitting equivalent miRNAs across sources when one source provides only the name and another provides both name and accession.

For genes and transcripts, the accession remains the canonical anchor, while the source release is tracked separately from the DBmiRNA canonical release.

## What The Normalization Block Tells Us

Each normalized entity can carry:

- `provider`
- `canonical_release`
- `source_release`
- `source_name` or `source_accession`
- `status`

This lets BioGeMT answer three important questions at any time:

- what DBmiRNA considers canonical right now
- what release the source data came from
- how strong the identifier normalization was for that record

## How To Change Canonical Versions

Edit [config/normalization.json](/homes/ezach01/DBmiRNA/config/normalization.json:1).

The most important keys are:

- `providers.mirna.canonical_release`
- `providers.gene.canonical_release`
- `providers.transcript.canonical_release`
- `source_defaults.<module>.mirna_release`
- `source_defaults.<module>.gene_release_default`
- `source_defaults.<module>.transcript_release_default`

If BioGeMT later wants to move to a different release, such as `miRBase v23` or `Ensembl v116`, this config is the place to change the active target.

## Important Constraint

Changing the canonical release in config does not automatically remap historical data across releases.

It changes:

- what new exports consider canonical
- what namespace new IDs are written into

It does not yet do:

- Ensembl release-to-release remapping
- transcript coordinate liftovers
- miRBase accession history reconciliation across releases

Those need explicit bridge tables or external mapping resources.

## Recommended Operational Rule

Keep both of these for every imported entity:

1. canonical ID under the active DBmiRNA policy
2. source normalization metadata describing the original source world

That way BioGeMT always knows:

- where we stand now
- what source world the data came from
- what would need re-exporting or remapping if the canonical version changes later
