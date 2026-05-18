from __future__ import annotations

import json
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> dict | list:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_schema_bundle() -> dict:
    return _load_json(project_root() / "schemas" / "collections.schema.json")


def load_collection_registry() -> dict:
    return _load_json(project_root() / "schemas" / "collection_registry.json")


def load_module_registry() -> dict:
    return _load_json(project_root() / "integrations" / "module_registry.json")


def load_dataset_catalog() -> dict:
    return _load_json(project_root() / "integrations" / "dataset_catalog.json")


def load_load_plan() -> dict:
    return _load_json(project_root() / "integrations" / "load_plan.json")


def validate_project() -> list[str]:
    errors: list[str] = []

    schema_bundle = load_schema_bundle()
    collection_registry = load_collection_registry()
    module_registry = load_module_registry()
    dataset_catalog = load_dataset_catalog()

    schema_defs = set(schema_bundle.get("$defs", {}).keys())
    collections = collection_registry.get("collections", [])
    collection_names = {item["name"] for item in collections}

    for item in collections:
        name = item["name"]
        schema_def = item["schema_def"]
        if schema_def not in schema_defs:
            errors.append(
                f"Collection {name!r} references missing schema def {schema_def!r}."
            )

    for module in module_registry.get("modules", []):
        for artifact in module.get("source_artifacts", []):
            for target in artifact.get("target_collections", []):
                if target not in collection_names:
                    errors.append(
                        f"Module {module['module_id']!r} targets unknown collection {target!r}."
                    )

    for dataset in dataset_catalog.get("datasets", []):
        for target in dataset.get("target_collections", []):
            if target not in collection_names:
                errors.append(
                    f"Dataset {dataset['dataset_id']!r} targets unknown collection {target!r}."
                )

    return errors


def build_overview() -> str:
    collection_registry = load_collection_registry()
    module_registry = load_module_registry()
    dataset_catalog = load_dataset_catalog()

    lines = [
        "DBmiRNA overview",
        f"Project root: {project_root()}",
        f"Collections: {len(collection_registry.get('collections', []))}",
        f"Source modules: {len(module_registry.get('modules', []))}",
        f"Cataloged datasets/artifacts: {len(dataset_catalog.get('datasets', []))}",
        "",
        "Collections:",
    ]
    for item in collection_registry.get("collections", []):
        lines.append(f"- {item['name']}: {item['purpose']}")

    lines.append("")
    lines.append("Modules:")
    for module in module_registry.get("modules", []):
        lines.append(
            f"- {module['module_id']}: {module['description']} ({module['repo_root']})"
        )

    return "\n".join(lines)


def build_module_info(module_id: str) -> str:
    module_registry = load_module_registry()
    for module in module_registry.get("modules", []):
        if module["module_id"] != module_id:
            continue
        lines = [
            f"Module: {module['module_id']}",
            f"Repo root: {module['repo_root']}",
            f"Description: {module['description']}",
            f"Ingest priority: {module['ingest_priority']}",
            "Artifacts:",
        ]
        for artifact in module.get("source_artifacts", []):
            lines.append(
                f"- {artifact['artifact_id']}: {artifact['path']} -> {', '.join(artifact['target_collections'])}"
            )
        return "\n".join(lines)
    raise ValueError(f"Unknown module_id: {module_id}")
