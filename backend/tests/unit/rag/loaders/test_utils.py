from app.rag.loaders.utils import (
    merge_page_text,
    normalize_whitespace,
    ocr_overlaps_native,
)


def test_normalize_whitespace_collapses_blank_lines_and_spaces():
    text = "Line one  \n\n\nLine two\t\tend"

    assert normalize_whitespace(text) == "Line one \n\nLine two end"


def test_merge_page_text_includes_page_marker_and_sections():
    merged = merge_page_text(
        page_number=4,
        native="Connect the USB cable.",
        figure_ocr_parts=["USB port rear panel"],
        full_page_ocr="",
    )

    assert merged.startswith("[Page 4]")
    assert "[Native]\nConnect the USB cable." in merged
    assert "[Figure OCR]\nUSB port rear panel" in merged


def test_ocr_overlaps_native_detects_duplicate_content():
    native = "Press the Power button to turn on the device."
    ocr = "Press the Power button to turn on"

    assert ocr_overlaps_native(native, ocr) is True


def test_ocr_overlaps_native_returns_false_for_distinct_text():
    native = "Connect the printer to Wi-Fi."
    ocr = "USB port rear panel left side"

    assert ocr_overlaps_native(native, ocr) is False
