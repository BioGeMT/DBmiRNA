CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS evidence;
CREATE SCHEMA IF NOT EXISTS literature;
CREATE SCHEMA IF NOT EXISTS provenance;

CREATE TABLE IF NOT EXISTS provenance.ingestion_runs (
  id text PRIMARY KEY,
  source_repo text NOT NULL,
  source_path text NOT NULL,
  source_release text,
  started_at timestamptz,
  completed_at timestamptz,
  transform_version text NOT NULL,
  checksums jsonb NOT NULL DEFAULT '{}'::jsonb,
  row_counts jsonb NOT NULL DEFAULT '{}'::jsonb,
  notes text
);

CREATE TABLE IF NOT EXISTS core.mirnas (
  id text PRIMARY KEY,
  canonical_name text NOT NULL,
  species text NOT NULL,
  sequence text,
  id_namespace text NOT NULL,
  canonical_accession text,
  family text,
  arm text,
  aliases text[] NOT NULL DEFAULT ARRAY[]::text[],
  normalization jsonb NOT NULL DEFAULT '{}'::jsonb,
  source_refs jsonb NOT NULL DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS core.genes (
  id text PRIMARY KEY,
  canonical_symbol text NOT NULL,
  species text NOT NULL,
  id_namespace text NOT NULL,
  canonical_accession text NOT NULL,
  aliases text[] NOT NULL DEFAULT ARRAY[]::text[],
  normalization jsonb NOT NULL DEFAULT '{}'::jsonb,
  source_refs jsonb NOT NULL DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS core.transcripts (
  id text PRIMARY KEY,
  gene_id text NOT NULL REFERENCES core.genes(id),
  id_namespace text NOT NULL,
  canonical_accession text NOT NULL,
  gene_symbol text,
  species text NOT NULL,
  sequence text,
  sequence_scope text NOT NULL,
  genome_build text,
  tx_start bigint,
  tx_end bigint,
  strand text,
  localization_labels jsonb,
  feature_track_summary jsonb,
  sequence_length integer,
  normalization jsonb NOT NULL DEFAULT '{}'::jsonb,
  source_refs jsonb NOT NULL DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS core.mirna_gene_pairs (
  id text PRIMARY KEY,
  mirna_id text NOT NULL REFERENCES core.mirnas(id),
  gene_id text NOT NULL REFERENCES core.genes(id),
  species text NOT NULL,
  evidence_counts jsonb NOT NULL DEFAULT '{}'::jsonb,
  best_supported_transcript_ids text[] NOT NULL DEFAULT ARRAY[]::text[],
  support_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  source_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  UNIQUE (mirna_id, gene_id)
);

CREATE TABLE IF NOT EXISTS core.transcript_feature_tracks (
  id text PRIMARY KEY,
  transcript_id text NOT NULL REFERENCES core.transcripts(id),
  track_name text NOT NULL,
  source text NOT NULL,
  kind text NOT NULL,
  count integer NOT NULL CHECK (count >= 0),
  payload_ref jsonb,
  run_id text NOT NULL REFERENCES provenance.ingestion_runs(id)
);

CREATE TABLE IF NOT EXISTS evidence.experiments (
  id text PRIMARY KEY,
  dataset_id text NOT NULL,
  mirna_id text NOT NULL REFERENCES core.mirnas(id),
  mirna_name_raw text NOT NULL,
  mirna_sequence text NOT NULL,
  article_pubmed_id text,
  geo_accession text,
  organism text NOT NULL,
  tested_cell_line text,
  tissue text,
  method text,
  experiment_type text NOT NULL,
  treatment text,
  de_table_path text NOT NULL,
  source_repo text NOT NULL,
  run_id text NOT NULL REFERENCES provenance.ingestion_runs(id)
);

CREATE TABLE IF NOT EXISTS evidence.experiment_gene_effects (
  id text PRIMARY KEY,
  experiment_id text NOT NULL REFERENCES evidence.experiments(id),
  pair_id text NOT NULL REFERENCES core.mirna_gene_pairs(id),
  mirna_id text NOT NULL REFERENCES core.mirnas(id),
  gene_id text NOT NULL REFERENCES core.genes(id),
  logfc double precision,
  fdr double precision,
  pvalue double precision,
  logcpm double precision,
  f_statistic double precision,
  effect_direction text NOT NULL,
  passes_default_threshold boolean,
  raw_row jsonb NOT NULL DEFAULT '{}'::jsonb,
  run_id text NOT NULL REFERENCES provenance.ingestion_runs(id)
);

CREATE TABLE IF NOT EXISTS evidence.predictors (
  id text PRIMARY KEY,
  tool_id text NOT NULL,
  official_name text NOT NULL,
  organism text NOT NULL,
  score_type text NOT NULL,
  score_direction text NOT NULL,
  score_range text,
  input_id_gene_type text NOT NULL,
  canonical_id_gene_type text NOT NULL,
  input_id_mirna_type text NOT NULL,
  canonical_id_mirna_type text NOT NULL,
  predictor_output_path text NOT NULL,
  source_repo text NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence.predictor_scores (
  id text PRIMARY KEY,
  predictor_id text NOT NULL REFERENCES evidence.predictors(id),
  pair_id text NOT NULL REFERENCES core.mirna_gene_pairs(id),
  mirna_id text NOT NULL REFERENCES core.mirnas(id),
  gene_id text NOT NULL REFERENCES core.genes(id),
  score_raw double precision NOT NULL,
  score_direction text NOT NULL,
  score_rank_within_mirna integer,
  source_row jsonb NOT NULL DEFAULT '{}'::jsonb,
  run_id text NOT NULL REFERENCES provenance.ingestion_runs(id)
);

CREATE TABLE IF NOT EXISTS evidence.site_observations (
  id text PRIMARY KEY,
  source_dataset text NOT NULL,
  source_repo text NOT NULL,
  mirna_id text REFERENCES core.mirnas(id),
  mirna_name_raw text,
  mirna_family_raw text,
  mirna_sequence_raw text NOT NULL,
  target_sequence_raw text,
  feature_label_raw text,
  label integer,
  chr text,
  start_pos bigint,
  end_pos bigint,
  strand text,
  read_len integer,
  gene_cluster_id text,
  gene_phylop_ref jsonb,
  gene_phastcons_ref jsonb,
  raw_row jsonb NOT NULL DEFAULT '{}'::jsonb,
  run_id text NOT NULL REFERENCES provenance.ingestion_runs(id)
);

CREATE TABLE IF NOT EXISTS evidence.mirna_recognition_elements (
  id text PRIMARY KEY,
  source_dataset text NOT NULL,
  source_repo text NOT NULL,
  source_split text NOT NULL,
  source_row_index integer NOT NULL CHECK (source_row_index >= 1),
  label integer NOT NULL,
  mirna_id text NOT NULL REFERENCES core.mirnas(id),
  mirna_name_raw text NOT NULL,
  mirna_family_raw text,
  mirna_sequence_raw text NOT NULL,
  gene_id text REFERENCES core.genes(id),
  gene_name_raw text,
  gene_cluster_id text,
  target_sequence_raw text NOT NULL,
  feature_label_raw text,
  chr text,
  start_pos bigint,
  end_pos bigint,
  strand text,
  read_len integer,
  experiment_type text,
  organism text,
  raw_row jsonb NOT NULL DEFAULT '{}'::jsonb,
  run_id text NOT NULL REFERENCES provenance.ingestion_runs(id)
);

CREATE TABLE IF NOT EXISTS evidence.mre_predictor_scores (
  id text PRIMARY KEY,
  predictor_id text NOT NULL REFERENCES evidence.predictors(id),
  mre_id text NOT NULL REFERENCES evidence.mirna_recognition_elements(id),
  mirna_id text NOT NULL REFERENCES core.mirnas(id),
  gene_id text REFERENCES core.genes(id),
  score_raw double precision NOT NULL,
  score_direction text NOT NULL,
  score_rank_within_mre integer,
  label integer,
  source_dataset text,
  source_row jsonb NOT NULL DEFAULT '{}'::jsonb,
  run_id text NOT NULL REFERENCES provenance.ingestion_runs(id)
);

CREATE TABLE IF NOT EXISTS evidence.site_transcript_overlaps (
  id text PRIMARY KEY,
  observation_id text NOT NULL REFERENCES evidence.site_observations(id),
  transcript_id text NOT NULL REFERENCES core.transcripts(id),
  gene_id text NOT NULL REFERENCES core.genes(id),
  gene_name_raw text,
  contained_100pct boolean NOT NULL,
  overlap_tx_bp integer NOT NULL CHECK (overlap_tx_bp >= 0),
  overlap_exon_bp integer NOT NULL CHECK (overlap_exon_bp >= 0),
  overlap_cds_bp integer NOT NULL CHECK (overlap_cds_bp >= 0),
  overlap_utr5_bp integer NOT NULL CHECK (overlap_utr5_bp >= 0),
  overlap_utr3_bp integer NOT NULL CHECK (overlap_utr3_bp >= 0),
  read_start_in_tx_1based integer,
  read_end_in_tx_1based integer,
  overlap_start_genome_1based bigint,
  overlap_end_genome_1based bigint,
  run_id text NOT NULL REFERENCES provenance.ingestion_runs(id)
);

CREATE TABLE IF NOT EXISTS evidence.mre_sites (
  id text PRIMARY KEY,
  pair_id text NOT NULL REFERENCES core.mirna_gene_pairs(id),
  mirna_id text NOT NULL REFERENCES core.mirnas(id),
  gene_id text NOT NULL REFERENCES core.genes(id),
  transcript_id text NOT NULL REFERENCES core.transcripts(id),
  observation_id text NOT NULL REFERENCES evidence.site_observations(id),
  chr text NOT NULL,
  start_pos bigint NOT NULL,
  end_pos bigint NOT NULL,
  strand text NOT NULL,
  read_len integer NOT NULL CHECK (read_len >= 0),
  selection_policy text NOT NULL,
  dominance_mode text NOT NULL,
  selected_gene_name text,
  dominant_region_selected text NOT NULL,
  regions_present_selected text NOT NULL,
  dominant_region_union text NOT NULL,
  regions_present_union text NOT NULL,
  bp_utr3_selected integer,
  bp_cds_selected integer,
  bp_utr5_selected integer,
  bp_exon_other_selected integer,
  bp_intron_selected integer,
  bp_intergenic_selected integer,
  bp_utr3_union integer,
  bp_cds_union integer,
  bp_utr5_union integer,
  bp_exon_other_union integer,
  bp_intron_union integer,
  bp_intergenic_union integer,
  ambiguous_union_vs_selected boolean NOT NULL,
  n_passing_transcripts integer NOT NULL CHECK (n_passing_transcripts >= 0),
  run_id text NOT NULL REFERENCES provenance.ingestion_runs(id)
);

CREATE TABLE IF NOT EXISTS evidence.nucleotide_profiles (
  id text PRIMARY KEY,
  entity_type text NOT NULL,
  entity_id text NOT NULL,
  profile_type text NOT NULL,
  length integer NOT NULL CHECK (length >= 0),
  storage_mode text NOT NULL,
  values_json jsonb,
  payload_ref jsonb,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  run_id text NOT NULL REFERENCES provenance.ingestion_runs(id)
);

CREATE TABLE IF NOT EXISTS literature.literature_documents (
  id text PRIMARY KEY,
  document_id text NOT NULL,
  pmid text,
  title text NOT NULL,
  abstract text NOT NULL,
  full_text text,
  source text NOT NULL,
  year text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  run_id text NOT NULL REFERENCES provenance.ingestion_runs(id)
);

CREATE TABLE IF NOT EXISTS literature.literature_mentions (
  id text PRIMARY KEY,
  document_id text NOT NULL REFERENCES literature.literature_documents(id),
  annotation_id text NOT NULL,
  source text NOT NULL,
  span_text text NOT NULL,
  start_pos integer,
  end_pos integer,
  entity_type text NOT NULL,
  canonical_id_raw text,
  canonical_name_raw text,
  resolved_mirna_id text REFERENCES core.mirnas(id),
  resolved_gene_id text REFERENCES core.genes(id),
  confidence double precision,
  run_id text NOT NULL REFERENCES provenance.ingestion_runs(id)
);

CREATE TABLE IF NOT EXISTS literature.literature_assertions (
  id text PRIMARY KEY,
  document_id text NOT NULL REFERENCES literature.literature_documents(id),
  mirna_id text NOT NULL REFERENCES core.mirnas(id),
  gene_id text NOT NULL REFERENCES core.genes(id),
  assertion_type text NOT NULL,
  direction text,
  evidence_text text NOT NULL,
  curation_status text NOT NULL,
  curator text,
  run_id text NOT NULL REFERENCES provenance.ingestion_runs(id)
);

CREATE INDEX IF NOT EXISTS mirnas_name_idx ON core.mirnas (canonical_name);
CREATE INDEX IF NOT EXISTS mirnas_accession_idx ON core.mirnas (canonical_accession);
CREATE INDEX IF NOT EXISTS genes_symbol_idx ON core.genes (canonical_symbol);
CREATE INDEX IF NOT EXISTS genes_accession_idx ON core.genes (canonical_accession);
CREATE INDEX IF NOT EXISTS transcripts_gene_idx ON core.transcripts (gene_id);
CREATE INDEX IF NOT EXISTS pairs_mirna_idx ON core.mirna_gene_pairs (mirna_id);
CREATE INDEX IF NOT EXISTS pairs_gene_idx ON core.mirna_gene_pairs (gene_id);
CREATE INDEX IF NOT EXISTS effects_pair_idx ON evidence.experiment_gene_effects (pair_id);
CREATE INDEX IF NOT EXISTS scores_pair_idx ON evidence.predictor_scores (pair_id);
CREATE INDEX IF NOT EXISTS mre_scores_mre_idx ON evidence.mre_predictor_scores (mre_id);
CREATE INDEX IF NOT EXISTS mre_scores_predictor_idx ON evidence.mre_predictor_scores (predictor_id);
CREATE INDEX IF NOT EXISTS mre_scores_mirna_idx ON evidence.mre_predictor_scores (mirna_id);
CREATE INDEX IF NOT EXISTS observations_locus_idx ON evidence.site_observations (chr, start_pos, end_pos);
CREATE INDEX IF NOT EXISTS mre_reads_dataset_split_idx ON evidence.mirna_recognition_elements (source_dataset, source_split);
CREATE INDEX IF NOT EXISTS mre_reads_mirna_idx ON evidence.mirna_recognition_elements (mirna_id);
CREATE INDEX IF NOT EXISTS mre_reads_gene_idx ON evidence.mirna_recognition_elements (gene_id);
CREATE INDEX IF NOT EXISTS mre_reads_locus_idx ON evidence.mirna_recognition_elements (chr, start_pos, end_pos);
CREATE INDEX IF NOT EXISTS overlaps_observation_idx ON evidence.site_transcript_overlaps (observation_id);
CREATE INDEX IF NOT EXISTS overlaps_transcript_idx ON evidence.site_transcript_overlaps (transcript_id);
CREATE INDEX IF NOT EXISTS mre_pair_idx ON evidence.mre_sites (pair_id);
CREATE INDEX IF NOT EXISTS mre_transcript_idx ON evidence.mre_sites (transcript_id);
CREATE INDEX IF NOT EXISTS nucleotide_entity_idx ON evidence.nucleotide_profiles (entity_type, entity_id);
