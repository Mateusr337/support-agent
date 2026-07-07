from io import BytesIO
from unittest.mock import MagicMock, patch

from PIL import Image

from app.rag.loaders.ocr import ocr_image_bytes


def _png_bytes() -> bytes:
    image = Image.new("RGB", (120, 120), color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_ocr_image_bytes_returns_empty_string_on_import_error():
    import builtins

    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "pytesseract":
            raise ImportError("missing pytesseract")
        return real_import(name, globals, locals, fromlist, level)

    with patch("builtins.__import__", side_effect=fake_import):
        assert ocr_image_bytes(_png_bytes(), lang="eng") == ""


def test_ocr_image_bytes_returns_tesseract_output():
    mock_pytesseract = MagicMock()
    mock_pytesseract.image_to_string.return_value = "  USB port  "

    with patch.dict("sys.modules", {"pytesseract": mock_pytesseract}):
        text = ocr_image_bytes(_png_bytes(), lang="eng")

    assert text == "USB port"


def test_ocr_image_bytes_returns_empty_string_on_tesseract_failure():
    mock_pytesseract = MagicMock()
    mock_pytesseract.image_to_string.side_effect = RuntimeError("ocr failed")

    with patch.dict("sys.modules", {"pytesseract": mock_pytesseract}):
        assert ocr_image_bytes(_png_bytes(), lang="eng") == ""
