from dataclasses import dataclass, field
from typing import Any

from prompt_builder import PromptBuildResult


@dataclass
class PipelineRunResult:
    prompt_result: PromptBuildResult
    chain_metadata: list[dict[str, Any]] = field(default_factory=list)
    available_claim_ids: list[str] = field(default_factory=list)
