from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable, Iterator
from urllib.parse import parse_qs, urlparse


def now_utc_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def stable_hash(*parts: object, length: int = 16) -> str:
    payload = "|".join("" if part is None else str(part) for part in parts)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:length]


def infer_arm_from_name(name: str | None) -> str | None:
    if not name:
        return None
    if name.endswith("-5p"):
        return "5p"
    if name.endswith("-3p"):
        return "3p"
    return None


def mirna_id_from_name(name: str) -> str:
    return f"mirna:name:{name.strip()}"


def gene_id_from_ensembl(accession: str) -> str:
    return f"gene:ensembl:{accession.strip()}"


def transcript_id_from_ensembl(accession: str) -> str:
    return f"tx:ensembl:{accession.strip()}"


def pair_id(mirna_id: str, gene_id: str) -> str:
    return f"pair:{stable_hash(mirna_id, gene_id)}"


def parse_pubmed_id(raw: str | None) -> str | None:
    if not raw:
        return None
    text = str(raw).strip()
    if not text:
        return None
    parsed = urlparse(text)
    if parsed.netloc:
        path_bits = [bit for bit in parsed.path.split("/") if bit]
        for bit in reversed(path_bits):
            if bit.isdigit():
                return bit
        return None
    return text if text.isdigit() else None


def parse_geo_accession(raw: str | None) -> str | None:
    if not raw:
        return None
    text = str(raw).strip()
    if not text:
        return None
    parsed = urlparse(text)
    query = parse_qs(parsed.query)
    acc = query.get("acc", [None])[0]
    if acc:
        return acc
    return text if text.startswith("GSE") else None


def effect_direction(logfc: float | None, *, epsilon: float = 1e-12) -> str:
    if logfc is None:
        return "unknown"
    if logfc > epsilon:
        return "up"
    if logfc < -epsilon:
        return "down"
    return "neutral"


def clean_nullable(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "" or stripped.lower() == "nan" or stripped == "NA":
            return None
        return stripped
    return value


def as_int(value: object) -> int | None:
    value = clean_nullable(value)
    if value is None:
        return None
    return int(value)


def as_float(value: object) -> float | None:
    value = clean_nullable(value)
    if value is None:
        return None
    return float(value)


def compact_dict(data: dict) -> dict:
    return {key: value for key, value in data.items() if value is not None}


def iter_tsv_rows(path: str | Path) -> Iterator[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            yield {str(key): value for key, value in row.items()}


class JsonlBundleWriter:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._handles: dict[str, object] = {}
        self.counts: Counter[str] = Counter()

    def write(self, collection: str, record: dict) -> None:
        handle = self._handles.get(collection)
        if handle is None:
            path = self.base_dir / f"{collection}.jsonl"
            handle = path.open("w", encoding="utf-8")
            self._handles[collection] = handle
        handle.write(json.dumps(record, sort_keys=True) + "\n")
        self.counts[collection] += 1

    def write_many(self, collection: str, records: Iterable[dict]) -> None:
        for record in records:
            self.write(collection, record)

    def close(self) -> None:
        for handle in self._handles.values():
            handle.close()
        self._handles.clear()

