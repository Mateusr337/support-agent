import re

NATIVE_SECTION = "[Native]"
FIGURE_OCR_SECTION = "[Figure OCR]"


def normalize_whitespace(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def ocr_overlaps_native(native: str, ocr: str, *, min_overlap_ratio: float = 0.6) -> bool:
    if not native or not ocr:
        return False

    native_tokens = _token_set(native)
    ocr_tokens = _token_set(ocr)
    if not ocr_tokens:
        return False

    overlap = len(native_tokens & ocr_tokens) / len(ocr_tokens)
    return overlap >= min_overlap_ratio


def merge_page_text(
    *,
    page_number: int,
    native: str,
    figure_ocr_parts: list[str] | None = None,
    full_page_ocr: str = "",
) -> str:
    sections: list[str] = [f"[Page {page_number}]"]
    figures = figure_ocr_parts or []

    if native:
        sections.append(f"{NATIVE_SECTION}\n{native}")

    for index, ocr_text in enumerate(figures, start=1):
        label = FIGURE_OCR_SECTION if len(figures) == 1 else f"{FIGURE_OCR_SECTION} {index}"
        sections.append(f"{label}\n{ocr_text}")

    if full_page_ocr:
        sections.append(f"{FIGURE_OCR_SECTION} (full page)\n{full_page_ocr}")

    return "\n\n".join(sections)


def _token_set(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[a-z0-9]+", text) if len(token) > 2}
