import json
import re
import sys
from typing import Any

from db.repositories import NPCRepo, PlayerRepo, RAGRepo
from prompt_builder import NPCProfile, PromptBuilder, PromptRequest, RAGContext
from rag.rendering import Rendering


class RAGPipelineServices:
    def __init__(self, driver: Any, embed_model: Any) -> None:
        self.rag_repo = RAGRepo(driver)
        self.npc_repo = NPCRepo(driver)
        self.player_repo = PlayerRepo(driver)
        self.embed_model = embed_model
        self.prompt_builder = PromptBuilder()
        self._group_support: bool | None = None

    def supports_group_membership(self) -> bool:
        if self._group_support is None:
            self._group_support = self.rag_repo.supports_group_membership()
        return self._group_support


def _is_english(locale: str | None) -> bool:
    return (locale or "sv").strip().lower() == "en"


def get_npc_data(services: RAGPipelineServices, npc_id: str, locale: str = "sv") -> dict[str, Any]:
    npc_data = services.npc_repo.get_profile_by_id(npc_id, locale=locale)
    if not npc_data:
        raise ValueError(f"NPC with ID '{npc_id}' not found.")
    return npc_data


def get_remembered_claim_hits(
    services: RAGPipelineServices,
    npc_id: str,
    conversation_claim_ids: list[str] | None,
    locale: str = "sv",
) -> list[dict[str, Any]]:
    return services.rag_repo.find_claims_by_claim_ids(
        npc_id=npc_id,
        claim_ids=conversation_claim_ids or [],
        locale=locale,
    )


def create_query_embedding(
    services: RAGPipelineServices,
    text: str,
) -> list[float]:
    return services.embed_model.embed_query(
        f"Represent this sentence for searching relevant passages: {text}"
    )


def _build_history_block(recent_exchanges: list[dict[str, Any]] | None) -> str:
    history_lines: list[str] = []
    for exchange in recent_exchanges or []:
        player_text = exchange.get("player_text") or ""
        npc_text = exchange.get("npc_text") or ""
        if player_text:
            history_lines.append(f"Spelare: {player_text}")
        if npc_text:
            history_lines.append(f"NPC: {npc_text}")
    return "\n".join(history_lines) if history_lines else "(ingen historik)"


def _build_history_block_for_locale(
    recent_exchanges: list[dict[str, Any]] | None,
    locale: str,
) -> str:
    history_lines: list[str] = []
    is_english = _is_english(locale)
    for exchange in recent_exchanges or []:
        player_text = exchange.get("player_text") or ""
        npc_text = exchange.get("npc_text") or ""
        if player_text:
            history_lines.append(f"{'Player' if is_english else 'Spelare'}: {player_text}")
        if npc_text:
            history_lines.append(f"NPC: {npc_text}")
    if history_lines:
        return "\n".join(history_lines)
    return "(no history)" if is_english else "(ingen historik)"


def _build_mentioned_block(mentioned_claims: list[dict[str, Any]] | None, locale: str = "sv") -> str:
    mentioned_lines = [
        claim["content"] for claim in mentioned_claims or [] if claim.get("content")
    ]
    if mentioned_lines:
        return "\n".join(f"- {line}" for line in mentioned_lines)
    return "(none)" if _is_english(locale) else "(inga)"


def rewrite_query(
    question: str,
    recent_exchanges: list[dict[str, Any]] | None,
    story_background: str | None = None,
    mentioned_claims: list[dict[str, Any]] | None = None,
    locale: str = "sv",
) -> str:
    from llms.llm_groq import chat as groq_chat

    is_english = _is_english(locale)
    history_block = _build_history_block_for_locale(recent_exchanges, locale)
    mentioned_block = _build_mentioned_block(mentioned_claims, locale)
    background_block = story_background.strip() if story_background else ("(no background)" if is_english else "(ingen bakgrund)")

    messages = [
        {
            "role": "system",
            "content": (
                "You are a question-rewriting tool for RAG (Retrieval-Augmented Generation).\n"
                "Your job is to rewrite the player's question into an information-rich search phrase optimized for vector database retrieval.\n"
                "You have access to the story background, previously mentioned information, and conversation history.\n"
                "Rules:\n"
                "- Replace all pronouns (he, she, it, there, etc.) with concrete names and places from the context.\n"
                "- The search phrase must include only information that maps exactly to what the player is asking for.\n"
                "- Write in English.\n"
                "- Return ONLY the search phrase as plain text, without explanation or comments."
            ) if is_english else (
                "Du är ett verktyg för frågeomskrivning för RAG (Retrieval-Augmented Generation).\n"
                "Din uppgift är att ta spelarens fråga och skriva om den till en informationsrik "
                "sökfras optimerad för vektordatabassökning.\n"
                "Du har tillgång till berättelsens bakgrund, tidigare nämnd information och konversationshistorik.\n"
                "Regler:\n"
                "- Ersätt alla pronomen (han, hon, det, där, etc.) med konkreta namn och platser från kontexten.\n"
                "- Sökfrasen ska endast innehålla information som anknyter exakt till vad spelaren frågar efter.\n"
                "- Skriv på svenska.\n"
                "- Returnera BARA sökfrasen som ren text, utan förklaring eller kommentarer."
            ),
        },
        {
            "role": "user",
            "content": (
                f"STORY BACKGROUND:\n{background_block}\n\n"
                f"PREVIOUSLY MENTIONED FACTS:\n{mentioned_block}\n\n"
                f"CONVERSATION HISTORY:\n{history_block}\n\n"
                f"PLAYER QUESTION: {question}\n\n"
                "SEARCH PHRASE:"
            ) if is_english else (
                f"BERÄTTELSENS BAKGRUND:\n{background_block}\n\n"
                f"TIDIGARE NÄMNDA FAKTA:\n{mentioned_block}\n\n"
                f"KONVERSATIONSHISTORIK:\n{history_block}\n\n"
                f"SPELARENS FRÅGA: {question}\n\n"
                "SÖKFRAS:"
            ),
        },
    ]

    rewritten = groq_chat(messages=messages, max_tokens=128).strip()
    if rewritten and rewritten != question:
        print(f"[Sökfras: {rewritten}]", file=sys.stderr)
    return rewritten or question


def build_search_query(
    question: str,
    recent_exchanges: list[dict[str, Any]] | None,
    story_background: str | None,
    remembered_claim_hits: list[dict[str, Any]],
    should_rewrite: bool,
    locale: str = "sv",
) -> str:
    if not should_rewrite:
        return question
    return rewrite_query(
        question=question,
        recent_exchanges=recent_exchanges,
        story_background=story_background,
        mentioned_claims=remembered_claim_hits,
        locale=locale,
    )


def get_top_claims(
    services: RAGPipelineServices,
    npc_id: str,
    query_embedding: list[float],
    top_k: int,
    locale: str = "sv",
) -> list[dict[str, Any]]:
    return services.rag_repo.find_top_claims(
        npc_id=npc_id,
        query_vector=query_embedding,
        top_k=top_k,
        locale=locale,
    )


def combine_claim_hits(
    top_claims: list[dict[str, Any]],
    remembered_claim_hits: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return top_claims + remembered_claim_hits


def expand_candidate_claims(
    services: RAGPipelineServices,
    npc_id: str,
    combined_hits: list[dict[str, Any]],
    locale: str = "sv",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    initial_ids = [claim["id"] for claim in combined_hits]
    all_expanded_claims, constants = services.rag_repo.expand_from_claims(initial_ids, locale=locale)
    constant_ids = [constant["id"] for constant in constants if constant.get("id")]
    mystery_ids = [
        constant["id"]
        for constant in constants
        if constant.get("id") and constant.get("type") == "MYSTERY"
    ]
    mystery_claims = (
        services.rag_repo.find_mystery_claims(mystery_ids, npc_id, locale=locale) if mystery_ids else []
    )
    relational_candidates = services.rag_repo.find_relational_candidates(
        npc_id=npc_id,
        constant_ids=constant_ids,
        locale=locale,
    )
    return all_expanded_claims, constants, mystery_claims + relational_candidates


def merge_unique_claims(*claim_groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    all_unique: dict[str, dict[str, Any]] = {}
    for group in claim_groups:
        for claim in group:
            all_unique[claim["id"]] = claim
    return list(all_unique.values())


def get_already_mentioned_claim_ids(
    services: RAGPipelineServices,
    player_id: str | None,
    npc_id: str,
) -> set[str]:
    if not player_id:
        return set()
    return services.player_repo.get_aware_claim_ids_from_npc(player_id, npc_id)


def _get_reference_chain(
    services: RAGPipelineServices,
    claim_id: str,
    npc_id: str,
    up_steps: int,
    locale: str,
) -> list[dict[str, Any]]:
    include_group = services.supports_group_membership()
    downstream_claims = services.rag_repo.get_reference_chain(
        claim_id=claim_id,
        npc_id=npc_id,
        include_group=include_group,
        locale=locale,
    )
    upstream_claims = (
        services.rag_repo.get_upstream_claims(
            claim_id=claim_id,
            npc_id=npc_id,
            up_steps=up_steps,
            include_group=include_group,
            locale=locale,
        )
        if up_steps > 0
        else []
    )
    return _dedupe_claims_by_depth(upstream_claims + downstream_claims)


def _dedupe_claims_by_depth(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique_claims: list[dict[str, Any]] = []
    for claim in sorted(claims, key=lambda item: item["depth"]):
        if claim["id"] in seen:
            continue
        seen.add(claim["id"])
        unique_claims.append(claim)
    return unique_claims


def _collect_chain_graph(
    services: RAGPipelineServices,
    claims: list[dict[str, Any]],
    npc_id: str,
    up_steps: int,
    locale: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, list[str]], set[str]]:
    all_nodes: dict[str, dict[str, Any]] = {}
    adjacency: dict[str, list[str]] = {}
    potential_roots: set[str] = set()

    for claim in claims:
        chain = _get_reference_chain(services, claim["id"], npc_id, up_steps, locale)
        if not chain:
            continue
        _add_chain_nodes(chain, all_nodes, adjacency, potential_roots)
        _add_chain_edges(chain, adjacency, potential_roots)

    return all_nodes, adjacency, potential_roots


def _add_chain_nodes(
    chain: list[dict[str, Any]],
    all_nodes: dict[str, dict[str, Any]],
    adjacency: dict[str, list[str]],
    potential_roots: set[str],
) -> None:
    for chain_claim in chain:
        all_nodes[chain_claim["id"]] = chain_claim
        adjacency.setdefault(chain_claim["id"], [])
        potential_roots.add(chain_claim["id"])


def _add_chain_edges(
    chain: list[dict[str, Any]],
    adjacency: dict[str, list[str]],
    potential_roots: set[str],
) -> None:
    for index in range(len(chain) - 1, 0, -1):
        parent = chain[index]
        child = chain[index - 1]
        if child["id"] not in adjacency[parent["id"]]:
            adjacency[parent["id"]].append(child["id"])
        potential_roots.discard(child["id"])


def _walk_chain(
    node_id: str,
    all_nodes: dict[str, dict[str, Any]],
    adjacency: dict[str, list[str]],
    visited: set[str],
) -> list[dict[str, Any]]:
    if node_id in visited:
        return []
    visited.add(node_id)

    chain_nodes = [all_nodes[node_id]]
    for child_id in adjacency.get(node_id, []):
        chain_nodes.extend(_walk_chain(child_id, all_nodes, adjacency, visited))
    return chain_nodes


def _render_chain_content(
    chain_nodes: list[dict[str, Any]],
    already_mentioned: set[str] | None,
    locale: str,
) -> str:
    rendered_claims = [
        Rendering.render_claim_static(
            chain_claim.get("claim_id"),
            chain_claim["content"],
            prefix=chain_claim.get("prefix"),
            suffix=_resolve_chain_suffix(chain_claim, already_mentioned, locale),
        )
        for chain_claim in chain_nodes
    ]
    return " ".join(rendered_claims)


def _resolve_chain_suffix(
    chain_claim: dict[str, Any],
    already_mentioned: set[str] | None,
    locale: str,
) -> str | None:
    claim_id = chain_claim.get("claim_id")
    if already_mentioned and claim_id in already_mentioned:
        return chain_claim.get("overwrite_suffix") or (
            "and you have already mentioned this" if locale == "en" else "och detta har du redan nämnt"
        )
    return chain_claim.get("suffix")


def _build_chain_payload(
    chain_nodes: list[dict[str, Any]],
    already_mentioned: set[str] | None,
    locale: str,
) -> dict[str, Any]:
    claim_entries = [
        {
            "id": chain_claim["id"],
            "claim_id": chain_claim.get("claim_id"),
            "content": chain_claim["content"],
            "prefix": chain_claim.get("prefix"),
            "suffix": chain_claim.get("suffix"),
            "overwrite_suffix": chain_claim.get("overwrite_suffix"),
            "type": chain_claim.get("type"),
        }
        for chain_claim in chain_nodes
    ]
    return {
        "content": _render_chain_content(chain_nodes, already_mentioned, locale),
        "ids": [chain_claim["id"] for chain_claim in chain_nodes],
        "claim_ids": [
            chain_claim["claim_id"]
            for chain_claim in chain_nodes
            if chain_claim.get("claim_id")
        ],
        "chain_length": len(chain_nodes),
        "has_relation_type": any(
            chain_claim.get("type") == "relation" for chain_claim in chain_nodes
        ),
        "claims": claim_entries,
    }


def build_claim_chains(
    services: RAGPipelineServices,
    claims: list[dict[str, Any]],
    npc_id: str,
    already_mentioned: set[str] | None = None,
    up_steps: int = 3,
    locale: str = "sv",
) -> list[dict[str, Any]]:
    if not claims:
        return []

    all_nodes, adjacency, potential_roots = _collect_chain_graph(
        services=services,
        claims=claims,
        npc_id=npc_id,
        up_steps=up_steps,
        locale=locale,
    )

    final_chains: list[dict[str, Any]] = []
    visited: set[str] = set()
    for root_id in list(potential_roots):
        if root_id in visited:
            continue
        chain_nodes = _walk_chain(root_id, all_nodes, adjacency, visited)
        if not chain_nodes:
            continue
        final_chains.append(_build_chain_payload(chain_nodes, already_mentioned, locale))
    return final_chains


def split_chain_content(
    chains: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    knowledge_claims: list[str] = []
    relation_claims: list[str] = []

    for chain in chains:
        if chain["chain_length"] > 1:
            knowledge_claims.append(chain["content"])
        elif chain.get("has_relation_type") is True:
            relation_claims.append(chain["content"])
        else:
            knowledge_claims.append(chain["content"])

    return knowledge_claims, relation_claims


def _build_selector_history_block(recent_exchanges: list[dict[str, Any]] | None) -> str:
    history_lines: list[str] = []
    for exchange in recent_exchanges or []:
        player_text = (exchange.get("player_text") or "").strip()
        npc_text = (exchange.get("npc_text") or "").strip()
        if player_text:
            history_lines.append(f"- DETEKTIVEN: {player_text}")
        if npc_text:
            history_lines.append(f"- NPC: {npc_text}")
    return "\n".join(history_lines) if history_lines else "(ingen historik)"


def _build_selector_history_block_for_locale(
    recent_exchanges: list[dict[str, Any]] | None,
    locale: str,
) -> str:
    history_lines: list[str] = []
    is_english = _is_english(locale)
    for exchange in recent_exchanges or []:
        player_text = (exchange.get("player_text") or "").strip()
        npc_text = (exchange.get("npc_text") or "").strip()
        if player_text:
            history_lines.append(f"- {'DETECTIVE' if is_english else 'DETEKTIVEN'}: {player_text}")
        if npc_text:
            history_lines.append(f"- NPC: {npc_text}")
    if history_lines:
        return "\n".join(history_lines)
    return "(no history)" if is_english else "(ingen historik)"


def _build_selector_candidates(chains: list[dict[str, Any]]) -> str:
    candidate_lines: list[str] = []
    for chain_index, chain in enumerate(chains, start=1):
        candidate_lines.append(f"KEDJA {chain_index}:")
        for claim in chain.get("claims") or []:
            claim_id = claim.get("claim_id") or "(utan claim-id)"
            candidate_lines.append(f"- {claim_id}: {claim.get('content', '')}")
    return "\n".join(candidate_lines) if candidate_lines else "(inga kandidater)"


def _extract_json_object(raw_response: str) -> dict[str, Any] | None:
    if not raw_response:
        return None

    text = raw_response.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text).strip()

    candidates = [text]
    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        candidates.append(json_match.group(0))

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    return None


def _normalize_selected_claim_ids(raw_ids: Any, allowed_ids: set[str]) -> list[str]:
    if not isinstance(raw_ids, list):
        return []

    selected: list[str] = []
    seen: set[str] = set()
    for raw_id in raw_ids:
        if not isinstance(raw_id, str):
            continue
        match = re.search(r"C\d+", raw_id.upper())
        if not match:
            continue
        claim_id = match.group(0)
        if claim_id in seen or claim_id not in allowed_ids:
            continue
        seen.add(claim_id)
        selected.append(claim_id)
    return selected


def select_relevant_claim_ids(
    question: str,
    recent_exchanges: list[dict[str, Any]] | None,
    story_background: str | None,
    chains: list[dict[str, Any]],
    locale: str = "sv",
) -> list[str]:
    from llms.llm_groq import chat as groq_chat

    is_english = _is_english(locale)
    allowed_ids = {
        claim_id.upper()
        for chain in chains
        for claim_id in (chain.get("claim_ids") or [])
        if isinstance(claim_id, str)
    }
    if not allowed_ids:
        return []

    selector_messages = [
        {
            "role": "system",
            "content": (
                "You choose which facts should be sent to another LLM that answers in character.\n"
                "The goal is high recall in retrieval but narrow relevance in the final prompt.\n"
                "Select only the claim IDs that are truly needed to answer the detective's latest question.\n"
                "Rules:\n"
                "- Return ONLY valid JSON with exactly the key 'selected_claim_ids'.\n"
                "- Format: {\"selected_claim_ids\": [\"C7\", \"C52\"]}\n"
                "- Select only claim IDs from the candidate list.\n"
                "- Include facts that directly answer the question or are needed to understand the answer.\n"
                "- Exclude side tracks, duplicates, and background that is not needed for this question.\n"
                "- If none of the candidate material is relevant, return an empty list []."
            ) if is_english else (
                "Du väljer vilka fakta som ska skickas vidare till en annan LLM som svarar i karaktär.\n"
                "Målet är hög recall i retrieval men snäv relevans i slutprompten.\n"
                "Välj bara claim-IDn som verkligen behövs för att besvara detektivens senaste fråga.\n"
                "Regler:\n"
                "- Returnera ENDAST giltig JSON med exakt nyckeln 'selected_claim_ids'.\n"
                "- Format: {\"selected_claim_ids\": [\"C7\", \"C52\"]}\n"
                "- Välj bara claim-IDn från kandidatlistan.\n"
                "- Ta med fakta som direkt besvarar frågan eller behövs för att förstå svaret.\n"
                "- Uteslut sidospår, dubletter och bakgrund som inte behövs för just frågan.\n"
                "- Om inget av kandidatmaterialet är relevant, returnera en tom lista []."
            ),
        },
        {
            "role": "user",
            "content": (
                f"STORY BACKGROUND:\n{(story_background or '(no background)').strip()}\n\n"
                f"LATEST CONVERSATION:\n{_build_selector_history_block_for_locale(recent_exchanges, locale)}\n\n"
                f"DETECTIVE'S LATEST QUESTION:\n{question}\n\n"
                f"CANDIDATE FACTS:\n{_build_selector_candidates(chains)}\n\n"
                "Return the JSON now."
            ) if is_english else (
                f"BERÄTTELSEBAKGRUND:\n{(story_background or '(ingen bakgrund)').strip()}\n\n"
                f"SENASTE KONVERSATION:\n{_build_selector_history_block_for_locale(recent_exchanges, locale)}\n\n"
                f"DETEKTIVENS SENASTE FRÅGA:\n{question}\n\n"
                f"KANDIDATFAKTA:\n{_build_selector_candidates(chains)}\n\n"
                "Returnera nu JSON."
            ),
        },
    ]

    raw_response = groq_chat(messages=selector_messages, max_tokens=256)
    parsed = _extract_json_object(raw_response)
    if not parsed:
        return []
    return _normalize_selected_claim_ids(parsed.get("selected_claim_ids"), allowed_ids)


def filter_claim_chains_by_selected_claim_ids(
    chains: list[dict[str, Any]],
    selected_claim_ids: list[str],
    already_mentioned: set[str] | None = None,
    locale: str = "sv",
) -> list[dict[str, Any]]:
    selected_lookup = {claim_id.upper() for claim_id in selected_claim_ids if isinstance(claim_id, str)}
    if not selected_lookup:
        return []

    filtered_chains: list[dict[str, Any]] = []
    for chain in chains:
        filtered_claims = [
            claim
            for claim in chain.get("claims") or []
            if isinstance(claim.get("claim_id"), str)
            and claim["claim_id"].upper() in selected_lookup
        ]
        if not filtered_claims:
            continue
        filtered_chains.append(
            _build_chain_payload(filtered_claims, already_mentioned, locale)
        )

    return filtered_chains


def build_rag_context(
    chains: list[dict[str, Any]],
    constants: list[dict[str, Any]],
) -> RAGContext:
    knowledge_claims, relation_claims = split_chain_content(chains)
    return RAGContext(
        knowledge_claims=knowledge_claims,
        relation_claims=relation_claims,
        metadata=constants,
    )


def build_npc_profile(npc_data: dict[str, Any]) -> NPCProfile:
    return NPCProfile(
        name=npc_data["name"],
        personality=npc_data.get("personality", ""),
        backstory=npc_data.get("backstory", ""),
        story_background=npc_data.get("story_background", ""),
    )


def build_prompt_request(
    question: str,
    locale: str = "sv",
    player_profile: dict[str, Any] | None = None,
    recent_exchanges: list[dict[str, Any]] | None = None,
    prior_conversation_summaries: list[dict[str, Any]] | None = None,
    scene_event: str | None = None,
) -> PromptRequest:
    return PromptRequest(
        question=question,
        scene_event=scene_event,
        locale=locale,
        player_name=(player_profile or {}).get("name"),
        player_appearance=(player_profile or {}).get("appearance"),
        recent_exchanges=recent_exchanges or [],
        prior_conversation_summaries=prior_conversation_summaries or [],
    )


def build_prompt_result(
    services: RAGPipelineServices,
    npc_data: dict[str, Any],
    rag_context: RAGContext,
    request: PromptRequest,
):
    return services.prompt_builder.build(
        profile=build_npc_profile(npc_data),
        rag_context=rag_context,
        request=request,
    )
