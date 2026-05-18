from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .utils import clean_nullable, infer_arm_from_name


@dataclass(frozen=True)
class NormalizationSettings:
    data: dict

    @property
    def providers(self) -> dict:
        return self.data["providers"]

    @property
    def source_defaults(self) -> dict:
        return self.data["source_defaults"]

    def provider_release(self, entity_type: str) -> str:
        return str(self.providers[entity_type]["canonical_release"])

    def provider_name(self, entity_type: str) -> str:
        return str(self.providers[entity_type]["provider"])

    def source_default_release(self, source_repo: str, entity_type: str) -> str | None:
        mapping = self.source_defaults.get(source_repo, {})
        key = {
            "mirna": "mirna_release",
            "gene": "gene_release_default",
            "transcript": "transcript_release_default",
        }[entity_type]
        value = mapping.get(key)
        return str(value) if value else None


def load_normalization_settings() -> NormalizationSettings:
    path = Path(__file__).resolve().parents[2] / "config" / "normalization.json"
    with path.open("r", encoding="utf-8") as handle:
        return NormalizationSettings(json.load(handle))


def build_normalization_info() -> str:
    settings = load_normalization_settings()
    lines = ["DBmiRNA normalization policy"]
    for entity_type in ("mirna", "gene", "transcript"):
        lines.append(
            f"- {entity_type}: {settings.provider_name(entity_type)} {settings.provider_release(entity_type)}"
        )
    lines.append("")
    lines.append("Source defaults:")
    for source_repo, values in settings.source_defaults.items():
        lines.append(
            f"- {source_repo}: miRNA {values['mirna_release']}, gene {values['gene_release_default']}, transcript {values['transcript_release_default']}"
        )
    return "\n".join(lines)


def canonical_mirna_id(*, name: str, accession: str | None = None, source_repo: str | None = None) -> tuple[str, dict]:
    settings = load_normalization_settings()
    canonical_release = settings.provider_release("mirna")
    source_release = settings.source_default_release(source_repo or "", "mirna")
    accession = clean_nullable(accession)
    internal_id = f"mirna:mirbase_{canonical_release}:{name.strip()}"
    status = "canonical_accession" if accession else "fallback_name"
    return internal_id, {
        "provider": "miRBase",
        "canonical_release": canonical_release,
        "source_release": source_release,
        "source_name": name.strip(),
        "source_accession": accession,
        "status": status,
    }


def canonical_gene_id(*, accession: str, source_repo: str | None = None, source_release: str | None = None) -> tuple[str, dict]:
    settings = load_normalization_settings()
    canonical_release = settings.provider_release("gene")
    detected_source_release = source_release or settings.source_default_release(source_repo or "", "gene")
    status = "canonical_accession"
    if detected_source_release and detected_source_release != canonical_release:
        status = "source_accession_unmapped"
    internal_id = f"gene:ensembl_{canonical_release}:{accession.strip()}"
    return internal_id, {
        "provider": "Ensembl",
        "canonical_release": canonical_release,
        "source_release": detected_source_release,
        "source_accession": accession.strip(),
        "status": status,
    }


def canonical_transcript_id(*, accession: str, source_repo: str | None = None, source_release: str | None = None) -> tuple[str, dict]:
    settings = load_normalization_settings()
    canonical_release = settings.provider_release("transcript")
    detected_source_release = source_release or settings.source_default_release(source_repo or "", "transcript")
    status = "canonical_accession"
    if detected_source_release and detected_source_release != canonical_release:
        status = "source_accession_unmapped"
    internal_id = f"tx:ensembl_{canonical_release}:{accession.strip()}"
    return internal_id, {
        "provider": "Ensembl",
        "canonical_release": canonical_release,
        "source_release": detected_source_release,
        "source_accession": accession.strip(),
        "status": status,
    }


def canonical_mirna_document(*, name: str, species: str, sequence: str | None, accession: str | None = None, family: str | None = None, source_repo: str | None = None, source_ref: dict | None = None) -> dict:
    internal_id, normalization = canonical_mirna_id(name=name, accession=accession, source_repo=source_repo)
    aliases = [name.strip()]
    if accession:
        aliases.append(str(accession).strip())
    return {
        "_id": internal_id,
        "canonical_name": name.strip(),
        "species": species,
        "sequence": sequence,
        "id_namespace": f"mirbase_{normalization['canonical_release']}",
        "canonical_accession": clean_nullable(accession),
        "family": clean_nullable(family),
        "arm": infer_arm_from_name(name),
        "aliases": aliases,
        "normalization": normalization,
        "source_refs": [source_ref] if source_ref else [],
    }


def canonical_gene_document(*, accession: str, symbol: str | None, species: str, source_repo: str | None = None, source_release: str | None = None, source_ref: dict | None = None) -> dict:
    internal_id, normalization = canonical_gene_id(accession=accession, source_repo=source_repo, source_release=source_release)
    alias_values = [value for value in [clean_nullable(symbol), accession.strip()] if value]
    return {
        "_id": internal_id,
        "canonical_symbol": clean_nullable(symbol) or accession.strip(),
        "species": species,
        "id_namespace": f"ensembl_{normalization['canonical_release']}",
        "canonical_accession": accession.strip(),
        "aliases": alias_values,
        "normalization": normalization,
        "source_refs": [source_ref] if source_ref else [],
    }


def canonical_transcript_document(*, accession: str, gene_id: str, gene_symbol: str | None, species: str, genome_build: str | None, tx_start: int | None, tx_end: int | None, strand: str | None, source_repo: str | None = None, source_release: str | None = None, source_ref: dict | None = None) -> dict:
    internal_id, normalization = canonical_transcript_id(accession=accession, source_repo=source_repo, source_release=source_release)
    return {
        "_id": internal_id,
        "gene_id": gene_id,
        "id_namespace": f"ensembl_{normalization['canonical_release']}",
        "canonical_accession": accession.strip(),
        "gene_symbol": clean_nullable(gene_symbol),
        "species": species,
        "sequence": None,
        "sequence_scope": "unknown",
        "genome_build": genome_build,
        "tx_start": tx_start,
        "tx_end": tx_end,
        "strand": clean_nullable(strand),
        "normalization": normalization,
        "source_refs": [source_ref] if source_ref else [],
    }
