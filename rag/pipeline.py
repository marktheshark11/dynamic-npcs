from .core import RAGCore
from .rendering import Rendering
from .utils import remove_duplicates

class RAGPipeline:
    def __init__(self, driver, embed_model):
        self.core = RAGCore(driver, embed_model)
        self.rendering = Rendering()

    def run(self, npc_name, question, top_k=3, min_refs=2):
        # Steg 1: Semantisk sökning
        top_claims = self.core.find_top_claims(npc_name, question, top_k=top_k)
        if not top_claims:
            return None, []
        # Steg 2: Hitta konstanter och relation-claims
        claim_ids = [c["id"] for c in top_claims]
        constants = self.core.get_constants_from_claims(claim_ids)
        constant_ids = [c["id"] for c in constants]
        relation_claims = self.core.find_relation_claims(npc_name, constant_ids, min_refs=min_refs)
        # Steg 3: Kombinera och ta bort dubbletter
        all_claims = top_claims + relation_claims
        unique_claims = remove_duplicates(all_claims)
        # Steg 4: Gruppera i kedjor och rendera
        chain_metadata = self.core.build_claim_chains(unique_claims, npc_name)
        # Steg 5 & 6: Bygg prompt
        prompt = self.rendering.build_prompt(npc_name, chain_metadata, question)
        return prompt, chain_metadata
