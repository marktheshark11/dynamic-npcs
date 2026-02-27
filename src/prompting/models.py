from dataclasses import dataclass, field
from typing import Any


ChatMessage = dict[str, str]


@dataclass
class NPCProfile:
    name: str
    personality: str | None = None
    backstory: str | None = None
    roleplay_as: str | None = None


@dataclass
class RAGContext:
    knowledge_claims: list[str] = field(default_factory=list)
    relation_claims: list[str] = field(default_factory=list)
    metadata: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class PromptRequest:
    question: str
    answer_prefix: str | None = None
    locale: str = "sv"


@dataclass
class PromptBuildResult:
    messages: list[ChatMessage]
    flat_prompt: str
    sections: dict[str, str]
