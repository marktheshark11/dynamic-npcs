from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Claim:
    claim_id: str
    content: str
    content_en: str | None = None
    type: Optional[str] = None
    important: bool = False
    embedding: Optional[list[float]] = field(default=None, repr=False)
    embedding_en: Optional[list[float]] = field(default=None, repr=False)

    def display_str(self) -> str:
        type_str = f" [{self.type}]" if self.type else ""
        important_str = " [viktig]" if self.important else ""
        content_preview = self.content[:60] + "..." if len(self.content) > 60 else self.content
        return f"{self.claim_id}{type_str}{important_str}: {content_preview}"

    def short_str(self) -> str:
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"{self.claim_id}: {content_preview}"
