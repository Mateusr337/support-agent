from unittest.mock import MagicMock, patch

from app.rag.loaders.pdf import _is_page_marker_only, _ocr_embedded_images


def test_is_page_marker_only_returns_true_for_marker_only_text():
    assert _is_page_marker_only("[Page 3]") is True


def test_is_page_marker_only_returns_false_when_content_exists():
    assert _is_page_marker_only("[Page 3]\n\n[Native]\nHello") is False


def test_ocr_embedded_images_skips_small_images():
    document = MagicMock()
    page = MagicMock()
    page.get_images.return_value = [(11,)]

    document.extract_image.return_value = {
        "width": 50,
        "height": 50,
        "image": b"image-bytes",
    }

    with patch("app.rag.loaders.pdf.ocr_image_bytes") as mock_ocr:
        parts = _ocr_embedded_images(
            document,
            page,
            min_image_px=100,
            tesseract_lang="eng",
        )

    assert parts == []
    mock_ocr.assert_not_called()


def test_ocr_embedded_images_collects_ocr_for_large_images():
    document = MagicMock()
    page = MagicMock()
    page.get_images.return_value = [(7,)]

    document.extract_image.return_value = {
        "width": 200,
        "height": 150,
        "image": b"image-bytes",
    }

    with patch(
        "app.rag.loaders.pdf.ocr_image_bytes",
        return_value="USB port rear panel",
    ):
        parts = _ocr_embedded_images(
            document,
            page,
            min_image_px=100,
            tesseract_lang="eng",
        )

    assert parts == ["USB port rear panel"]
