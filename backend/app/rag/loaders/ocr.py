from io import BytesIO

from PIL import Image


def ocr_image_bytes(image_bytes: bytes, *, lang: str) -> str:
    try:
        import pytesseract
    except ImportError:
        return ""

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            rgb = image.convert("RGB")
            text = pytesseract.image_to_string(rgb, lang=lang)
    except Exception:
        return ""

    return text.strip()
