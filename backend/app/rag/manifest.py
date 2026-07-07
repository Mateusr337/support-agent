from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

MANIFEST_FILENAME = "_manifest.json"
_REQUIRED_FIELDS = ("filename", "product_name", "product_type")


@dataclass(frozen=True)
class DocumentManifestEntry:
    filename: str
    product_name: str
    product_type: str

    @property
    def extension(self) -> str:
        return Path(self.filename).suffix.lower()

    @classmethod
    def from_path(cls, path: Path) -> DocumentManifestEntry:
        return cls(
            filename=path.name,
            product_name=path.stem,
            product_type="unknown",
        )


def load_manifest(directory: Path) -> tuple[DocumentManifestEntry, ...]:
    manifest_path = directory / MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"Manifest not found: {manifest_path}. "
            f"Add {MANIFEST_FILENAME} with a documents list."
        )

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_documents = data.get("documents")
    if not isinstance(raw_documents, list):
        raise ValueError(f"Invalid manifest: 'documents' must be a list in {manifest_path}")

    entries: list[DocumentManifestEntry] = []
    for index, item in enumerate(raw_documents):
        if not isinstance(item, dict):
            raise ValueError(f"Invalid manifest: documents[{index}] must be an object")

        missing = [field for field in _REQUIRED_FIELDS if not item.get(field)]
        if missing:
            raise ValueError(
                f"Invalid manifest: documents[{index}] missing fields: {', '.join(missing)}"
            )

        entries.append(
            DocumentManifestEntry(
                filename=str(item["filename"]),
                product_name=str(item["product_name"]),
                product_type=str(item["product_type"]),
            )
        )

    return tuple(entries)


def find_manifest_entry(
    entries: tuple[DocumentManifestEntry, ...],
    filename: str,
) -> DocumentManifestEntry | None:
    for entry in entries:
        if entry.filename == filename:
            return entry
    return None


def _normalize_product_text(text: str) -> str:
    return " ".join(text.lower().split())


def _product_tokens(text: str) -> set[str]:
    return {token for token in _normalize_product_text(text).split() if len(token) > 1}


def resolve_product_name(
    hint: str,
    entries: tuple[DocumentManifestEntry, ...],
    *,
    product_type: str | None = None,
) -> str | None:
    normalized_hint = _normalize_product_text(hint)
    if not normalized_hint or not entries:
        return None

    candidates = list(entries)
    if product_type:
        normalized_type = _normalize_product_text(product_type)
        typed = [entry for entry in candidates if _normalize_product_text(entry.product_type) == normalized_type]
        if typed:
            candidates = typed

    for entry in candidates:
        if _normalize_product_text(entry.product_name) == normalized_hint:
            return entry.product_name

    for entry in candidates:
        product_name = _normalize_product_text(entry.product_name)
        if normalized_hint in product_name or product_name in normalized_hint:
            return entry.product_name

    hint_tokens = _product_tokens(normalized_hint)
    if not hint_tokens:
        return None

    best_name: str | None = None
    best_score = 0
    for entry in candidates:
        overlap = len(hint_tokens & _product_tokens(entry.product_name))
        if overlap > best_score:
            best_score = overlap
            best_name = entry.product_name

    min_overlap = 1 if len(hint_tokens) <= 2 else 2
    if best_score >= min_overlap:
        return best_name
    return None


def resolve_product_filters(
    *,
    product: str | None,
    product_type: str | None,
    entries: tuple[DocumentManifestEntry, ...],
) -> tuple[str | None, str | None]:
    resolved_type = product_type.strip() if product_type else None
    if not product:
        return None, resolved_type or None

    resolved_name = resolve_product_name(product, entries, product_type=resolved_type)
    if resolved_name is None:
        return None, resolved_type or None

    if resolved_type is None:
        for entry in entries:
            if entry.product_name == resolved_name:
                resolved_type = entry.product_type
                break

    return resolved_name, resolved_type or None


def format_indexed_products(entries: tuple[DocumentManifestEntry, ...]) -> str:
    if not entries:
        return ""
    lines = [f"- {entry.product_name} ({entry.product_type})" for entry in entries]
    return "Indexed products (use exact product filter values):\n" + "\n".join(lines)
