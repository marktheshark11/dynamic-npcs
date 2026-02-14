from .core import RAGCore
from .utils import remove_duplicates
from prompting import NPCProfile, PromptBuilder, PromptRequest, RAGContext

class RAGPipeline:
    def __init__(self, driver, embed_model):
        self.core = RAGCore(driver, embed_model)
        self.prompt_builder = PromptBuilder()

    def run(self, npc_id, question, top_k=3, min_refs=2):
        npc_row = self.core.get_npc_profile(npc_id)
        if not npc_row:
            return None, []
        npc_name = npc_row.get("name") or npc_id

        # Steg 1: Semantisk sökning
        top_claims = self.core.find_top_claims(npc_id, question, top_k=top_k)
        # Steg 2: Hitta konstanter och relation-claims
        claim_ids = [c["id"] for c in top_claims]
        constants = self.core.get_constants_from_claims(claim_ids)
        constant_ids = [c["id"] for c in constants]
        relation_claims = self.core.find_relation_claims(npc_id, constant_ids, min_refs=min_refs)
        # Steg 3: Kombinera och ta bort dubbletter
        all_claims = top_claims + relation_claims
        unique_claims = remove_duplicates(all_claims)
        # Steg 4: Gruppera i kedjor och rendera
        chain_metadata = self.core.build_claim_chains(unique_claims, npc_id)
        # Steg 5 & 6: Bygg strukturerad prompt (messages-first)
        non_relation = [c["content"] for c in chain_metadata if not c["is_relation"]]
        relation = [c["content"] for c in chain_metadata if c["is_relation"]]

        profile = NPCProfile(
            name=npc_name,
            roleplay_as=npc_name,
            personality=npc_row.get("personality"),
            backstory=npc_row.get("backstory"),
        )
        rag_context = RAGContext(
            knowledge_claims=non_relation,
            relation_claims=relation,
            metadata=chain_metadata,
        )
        request = PromptRequest(question=question, answer_prefix=f"{npc_name.upper()}:")
        prompt_result = self.prompt_builder.build(profile, rag_context, request)
        return prompt_result, chain_metadata
