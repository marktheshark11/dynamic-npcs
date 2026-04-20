from typing import Any

from .base import ChatPipeline
from .models import ExchangeTrace, PipelineRunResult
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
    filter_claim_chains_by_selected_claim_ids,
    get_already_mentioned_claim_ids,
    get_npc_data,
    get_remembered_claim_hits,
    get_top_claims,
    merge_unique_claims,
    select_relevant_claims,
)


class WideSelectRAGPipeline(ChatPipeline):
    pipeline_id = "wide_select_rag"
    should_rewrite_query = False

    def __init__(self, driver: Any, embed_model: Any) -> None:
        self._services = RAGPipelineServices(driver, embed_model)
        self._up_steps = 3
        self._wide_top_k = 12
        self._selector_candidate_limit = 40

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
        npc_data = get_npc_data(self._services, npc_id, locale=locale)
        remembered_claim_hits = get_remembered_claim_hits(
            self._services,
            npc_id=npc_id,
            conversation_claim_ids=conversation_claim_ids,
            locale=locale,
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
            top_k=max(top_k, self._wide_top_k),
            locale=locale,
        )
        combined_hits = combine_claim_hits(top_claims, remembered_claim_hits)
        expanded_claims, constants, extra_claims = expand_candidate_claims(
            self._services,
            npc_id=npc_id,
            combined_hits=combined_hits,
            locale=locale,
        )
        uncapped_available_claims = merge_unique_claims(
            combined_hits,
            expanded_claims,
            extra_claims,
        )
        available_claims = uncapped_available_claims[:self._selector_candidate_limit]
        print("Available claims:", available_claims)
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
            locale=locale,
        )
        selector_debug = select_relevant_claims(
            question=question,
            recent_exchanges=recent_exchanges,
            story_background=npc_data.get("story_background"),
            chains=chain_metadata,
            locale=locale,
            prefer_important_claims=True,
            include_debug=True,
        )
        selector_debug["candidate_limit"] = self._selector_candidate_limit
        selector_debug["candidate_count_before_cap"] = len(uncapped_available_claims)
        selector_debug["candidate_count_after_cap"] = len(available_claims)
        selected_claim_ids = selector_debug.get("selected_claim_ids") or []
        print("Selected claim IDs for RAG context:", selected_claim_ids)
        filtered_chain_metadata = filter_claim_chains_by_selected_claim_ids(
            chains=chain_metadata,
            selected_claim_ids=selected_claim_ids,
            already_mentioned=already_mentioned,
            locale=locale,
        )
        final_chain_metadata = filtered_chain_metadata or chain_metadata
        rag_context = build_rag_context(final_chain_metadata, constants)
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
            chain_metadata=final_chain_metadata,
            available_claim_ids=self.extract_available_claim_ids(final_chain_metadata),
            selector_debug=selector_debug,
            exchange_trace=ExchangeTrace(
                pipeline_id=self.pipeline_id,
                search_query=search_query,
                candidate_claim_ids=self.extract_claim_ids_from_claims(available_claims),
                candidate_important_claim_ids=self.extract_important_claim_ids_from_claims(available_claims),
                selected_claim_ids=self.extract_available_claim_ids(final_chain_metadata),
                selected_important_claim_ids=self.extract_available_important_claim_ids(final_chain_metadata),
                remembered_claim_count=len(remembered_claim_hits),
                selector_strategy="wide_select",
                search_top_k=max(top_k, self._wide_top_k),
                was_start_dialog=False,
            ),
        )

    def run_start_dialog(
        self,
        npc_id: str,
        player_profile: dict[str, Any] | None = None,
        recent_exchanges: list[dict[str, Any]] | None = None,
        prior_conversation_summaries: list[dict[str, Any]] | None = None,
        locale: str = "sv",
    ) -> PipelineRunResult:
        npc_data = get_npc_data(self._services, npc_id, locale=locale)
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
            selector_debug=None,
            exchange_trace=ExchangeTrace(
                pipeline_id=self.pipeline_id,
                selector_strategy="wide_select",
                search_top_k=0,
                was_start_dialog=True,
            ),
        )
