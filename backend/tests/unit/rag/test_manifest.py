import json
from pathlib import Path

import pytest

from app.rag.manifest import (
    MANIFEST_FILENAME,
    DocumentManifestEntry,
    find_manifest_entry,
    format_indexed_products,
    load_manifest,
    resolve_product_filters,
    resolve_product_name,
)


def _write_manifest(directory: Path, documents: list[dict]) -> None:
    (directory / MANIFEST_FILENAME).write_text(
        json.dumps({"documents": documents}),
        encoding="utf-8",
    )


def test_load_manifest_returns_entries(tmp_path: Path):
    _write_manifest(
        tmp_path,
        [
            {
                "filename": "manual.pdf",
                "product_name": "OMEN Laptop",
                "product_type": "laptop",
            }
        ],
    )

    entries = load_manifest(tmp_path)

    assert entries == (
        DocumentManifestEntry(
            filename="manual.pdf",
            product_name="OMEN Laptop",
            product_type="laptop",
        ),
    )
    assert entries[0].extension == ".pdf"


def test_load_manifest_raises_when_file_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match=MANIFEST_FILENAME):
        load_manifest(tmp_path)


def test_load_manifest_raises_when_documents_is_not_a_list(tmp_path: Path):
    (tmp_path / MANIFEST_FILENAME).write_text('{"documents": "bad"}', encoding="utf-8")

    with pytest.raises(ValueError, match="documents"):
        load_manifest(tmp_path)


def test_load_manifest_raises_when_entry_is_not_an_object(tmp_path: Path):
    _write_manifest(tmp_path, ["bad"])

    with pytest.raises(ValueError, match="must be an object"):
        load_manifest(tmp_path)


def test_load_manifest_raises_when_entry_is_missing_fields(tmp_path: Path):
    _write_manifest(tmp_path, [{"filename": "manual.pdf"}])

    with pytest.raises(ValueError, match="missing fields"):
        load_manifest(tmp_path)


def test_find_manifest_entry_returns_match():
    entries = (
        DocumentManifestEntry("a.pdf", "Product A", "laptop"),
        DocumentManifestEntry("b.pdf", "Product B", "printer"),
    )

    assert find_manifest_entry(entries, "b.pdf") == entries[1]
    assert find_manifest_entry(entries, "missing.pdf") is None


def test_document_manifest_entry_from_path():
    entry = DocumentManifestEntry.from_path(Path("/docs/manual.pdf"))

    assert entry.filename == "manual.pdf"
    assert entry.product_name == "manual"
    assert entry.product_type == "unknown"


LAPTOP_ENTRY = DocumentManifestEntry(
    "OMEN 17.3 inch Gaming Laptop PC.pdf",
    "OMEN 17.3 inch Gaming Laptop PC",
    "laptop",
)
PRINTER_ENTRY = DocumentManifestEntry(
    "HP ENVY 6000 All-in-One series.pdf",
    "HP ENVY 6000 All-in-One series",
    "printer",
)
CORPUS = (LAPTOP_ENTRY, PRINTER_ENTRY)


def test_resolve_product_name_matches_colloquial_omen_name():
    assert resolve_product_name("HP OMEN 17.3", CORPUS, product_type="laptop") == LAPTOP_ENTRY.product_name


def test_resolve_product_filters_fills_product_type_from_manifest():
    assert resolve_product_filters(
        product="OMEN 17.3",
        product_type=None,
        entries=CORPUS,
    ) == (LAPTOP_ENTRY.product_name, "laptop")


def test_resolve_product_filters_drops_unknown_product_name():
    assert resolve_product_filters(
        product="Unknown Product",
        product_type="laptop",
        entries=CORPUS,
    ) == (None, "laptop")


def test_format_indexed_products_lists_manifest_entries():
    text = format_indexed_products(CORPUS)

    assert LAPTOP_ENTRY.product_name in text
    assert PRINTER_ENTRY.product_name in text
