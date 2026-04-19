from dataclasses import dataclass, field
from typing import Any

from prompt_builder import PromptBuildResult


@dataclass
class ExchangeTrace:
    pipeline_id: str | None = None
    search_query: str | None = None
    candidate_claim_ids: list[str] = field(default_factory=list)
    selected_claim_ids: list[str] = field(default_factory=list)
    remembered_claim_count: int = 0
    selector_strategy: str | None = None
    search_top_k: int | None = None
    was_start_dialog: bool = False


@dataclass
class PipelineRunResult:
    prompt_result: PromptBuildResult
    chain_metadata: list[dict[str, Any]] = field(default_factory=list)
    available_claim_ids: list[str] = field(default_factory=list)
    selector_debug: dict[str, Any] | None = None
    exchange_trace: ExchangeTrace = field(default_factory=ExchangeTrace)
