from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class DocumentPage:
    text: str
    page_number: int
    source: str
    has_native_text: bool = False
    has_ocr_text: bool = False

    @property
    def content_type(self) -> str:
        if self.has_native_text and self.has_ocr_text:
            return "mixed"
        if self.has_ocr_text:
            return "ocr"
        return "native"


@dataclass(frozen=True)
class DocumentLoadResult:
    pages: tuple[DocumentPage, ...]
    total_pages: int

    @property
    def pages_indexed(self) -> int:
        return len(self.pages)

    @property
    def pages_skipped(self) -> int:
        return max(self.total_pages - self.pages_indexed, 0)

    @property
    def pages_native_only(self) -> int:
        return sum(1 for page in self.pages if page.content_type == "native")

    @property
    def pages_ocr_only(self) -> int:
        return sum(1 for page in self.pages if page.content_type == "ocr")

    @property
    def pages_mixed(self) -> int:
        return sum(1 for page in self.pages if page.content_type == "mixed")


class DocumentLoader(Protocol):
    @property
    def name(self) -> str: ...

    def load(self, path: str | Path) -> DocumentLoadResult: ...
