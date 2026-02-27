from .core import RAGCore
from prompt_builder import NPCProfile, PromptBuilder, PromptRequest, RAGContext


class RAGPipeline:
    def __init__(self, driver, embed_model):
        self.core = RAGCore(driver, embed_model)
        self.prompt_builder = PromptBuilder() 

    def run(self, npc_id, question, top_k=7):
        # 1. Grundsökning (Semantisk)
        top_claims = self.core.find_top_claims(npc_id, question, top_k=top_k)
        
        # 2. Expandera för att hitta konstanter (PLACE, OBJECT, NPC, MYSTERY)
        initial_ids = [c["id"] for c in top_claims]
        all_expanded_claims, constants = self.core.expand_from_claims(initial_ids)
        constant_ids = [c["id"] for c in constants if c["id"]]
        
        # 3. Hitta alla "kandidater" för relationer utifrån dina 4 kriterier:
        rel_candidates = self.core.find_relational_candidates(npc_id, constant_ids)
        rel_candidate_ids = {c["id"] for c in rel_candidates}
        
        # 4. Slå ihop allt och bygg kedjor (Logisk pussling)
        all_unique = {c["id"]: c for c in (top_claims + all_expanded_claims + rel_candidates)}
        chains = self.core.build_claim_chains(list(all_unique.values()), npc_id)
        
        # 5. Sortera: Kedjor > 1 eller fakta -> knowledge. Enstaka relationer -> relation_claims.
        knowledge_final = []
        relation_final = []
        
        for chain in chains:
            # REGEL 1: Serier (längd > 1) går ALLTID till knowledge för kontext
            if chain["chain_length"] > 1:
                knowledge_final.append(chain["content"])
            else:
                # REGEL 2: Endast fristående claims där typen är exakt "relation" 
                # går till relation_claims. Allt annat hamnar i knowledge.
                if chain.get("has_relation_type") == True:
                    relation_final.append(chain["content"])
                else:
                    knowledge_final.append(chain["content"])

        # 6. Paketera för LLM-prompten
        context = RAGContext(
            knowledge_claims=knowledge_final,
            relation_claims=relation_final,
            metadata=constants
        )
        
        npc_data = self.core.get_npc_profile(npc_id)
        if not npc_data:
            raise ValueError(f"NPC with ID '{npc_id}' not found.")

        profile = NPCProfile(
            name=npc_data["name"],
            personality=npc_data.get("personality", ""),
            backstory=npc_data.get("backstory", ""),
            story_background=npc_data.get("story_background", "")
        )

        request = PromptRequest(question=question)

        prompt_result = self.prompt_builder.build(
            profile=profile,
            rag_context=context,
            request=request
        )

        return prompt_result, chains