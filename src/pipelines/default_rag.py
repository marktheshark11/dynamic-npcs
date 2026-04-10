from typing import Any

from .base import ChatPipeline
from .models import PipelineRunResult
from .rag_helpers import (
    RAGPipelineServices,
    build_claim_chains,
    build_prompt_request,
    build_prompt_result,
    build_rag_context,
    build_search_query,
    combine_claim_hits,
    create_query_embedding,
    expand_candidate_claims,
    get_already_mentioned_claim_ids,
    get_npc_data,
    get_remembered_claim_hits,
    get_top_claims,
    merge_unique_claims,
)


class DefaultRAGPipeline(ChatPipeline):
    pipeline_id = "default_rag"
    should_rewrite_query = True

    def __init__(self, driver: Any, embed_model: Any) -> None:
        self._services = RAGPipelineServices(driver, embed_model)
        self._up_steps = 3

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
        npc_data = get_npc_data(self._services, npc_id)
        remembered_claim_hits = get_remembered_claim_hits(
            self._services,
            npc_id=npc_id,
            conversation_claim_ids=conversation_claim_ids,
        )
        search_query = build_search_query(
            question=question,
            recent_exchanges=recent_exchanges,
            story_background=npc_data.get("story_background"),
            remembered_claim_hits=remembered_claim_hits,
            should_rewrite=self.should_rewrite_query,
            locale=locale,
        )
        query_embedding = create_query_embedding(self._services, search_query)
        top_claims = get_top_claims(
            self._services,
            npc_id=npc_id,
            query_embedding=query_embedding,
            top_k=top_k,
        )
        combined_hits = combine_claim_hits(top_claims, remembered_claim_hits)
        expanded_claims, constants, extra_claims = expand_candidate_claims(
            self._services,
            npc_id=npc_id,
            combined_hits=combined_hits,
        )
        available_claims = merge_unique_claims(combined_hits, expanded_claims, extra_claims)
        already_mentioned = get_already_mentioned_claim_ids(
            self._services,
            player_id=player_id,
            npc_id=npc_id,
        )
        chain_metadata = build_claim_chains(
            self._services,
            claims=available_claims,
            npc_id=npc_id,
            already_mentioned=already_mentioned,
            up_steps=self._up_steps,
        )
        rag_context = build_rag_context(chain_metadata, constants)
        prompt_request = build_prompt_request(
            question=question,
            locale=locale,
            player_profile=player_profile,
            recent_exchanges=recent_exchanges,
            prior_conversation_summaries=prior_conversation_summaries,
        )
        prompt_result = build_prompt_result(
            self._services,
            npc_data=npc_data,
            rag_context=rag_context,
            request=prompt_request,
        )
        return PipelineRunResult(
            prompt_result=prompt_result,
            chain_metadata=chain_metadata,
            available_claim_ids=self.extract_available_claim_ids(chain_metadata),
        )

    def run_start_dialog(
        self,
        npc_id: str,
        player_profile: dict[str, Any] | None = None,
        recent_exchanges: list[dict[str, Any]] | None = None,
        prior_conversation_summaries: list[dict[str, Any]] | None = None,
        locale: str = "sv",
    ) -> PipelineRunResult:
        npc_data = get_npc_data(self._services, npc_id)
        prompt_request = build_prompt_request(
            question="",
            locale=locale,
            player_profile=player_profile,
            recent_exchanges=recent_exchanges,
            prior_conversation_summaries=prior_conversation_summaries,
            scene_event="detective_enters_room",
        )
        prompt_result = build_prompt_result(
            self._services,
            npc_data=npc_data,
            rag_context=build_rag_context([], []),
            request=prompt_request,
        )
        chain_metadata: list[dict[str, Any]] = []
        return PipelineRunResult(
            prompt_result=prompt_result,
            chain_metadata=chain_metadata,
            available_claim_ids=self.extract_available_claim_ids(chain_metadata),
        )
