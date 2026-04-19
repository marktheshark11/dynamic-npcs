from abc import ABC, abstractmethod
from typing import Any

from .models import PipelineRunResult


class ChatPipeline(ABC):
    pipeline_id: str

    @staticmethod
    def extract_available_claim_ids(chain_metadata: list[dict[str, Any]]) -> list[str]:
        claim_ids: list[str] = []
        seen: set[str] = set()

        for chain in chain_metadata or []:
            for claim_id in chain.get("claim_ids") or []:
                if not isinstance(claim_id, str) or claim_id in seen:
                    continue
                seen.add(claim_id)
                claim_ids.append(claim_id)

        return claim_ids

    @staticmethod
    def extract_claim_ids_from_claims(claims: list[dict[str, Any]]) -> list[str]:
        claim_ids: list[str] = []
        seen: set[str] = set()

        for claim in claims or []:
            claim_id = claim.get("claim_id")
            if not isinstance(claim_id, str) or not claim_id or claim_id in seen:
                continue
            seen.add(claim_id)
            claim_ids.append(claim_id)

        return claim_ids

    @abstractmethod
    def run(
        self,
        npc_id: str,
        question: str,
        top_k: int = 3,
        player_profile: dict[str, Any] | None = None,
        recent_exchanges: list[dict[str, Any]] | None = None,
        prior_conversation_summaries: list[dict[str, Any]] | None = None,
        player_id: str | None = None,
        conversation_claim_ids: list[str] | None = None,
        locale: str = "sv",
    ) -> PipelineRunResult:
        raise NotImplementedError

    @abstractmethod
    def run_start_dialog(
        self,
        npc_id: str,
        player_profile: dict[str, Any] | None = None,
        recent_exchanges: list[dict[str, Any]] | None = None,
        prior_conversation_summaries: list[dict[str, Any]] | None = None,
        locale: str = "sv",
    ) -> PipelineRunResult:
        raise NotImplementedError
