from rag.pipeline import RAGPipeline


class ChatService:
    def __init__(self, driver, embed_model, default_model="llama-3.3-70b-versatile"):
        self.pipeline = RAGPipeline(driver, embed_model)
        self.default_model = default_model

    def build_prompt(self, npc_id, question, top_k=3, min_refs=2):
        return self.pipeline.run(npc_id, question, top_k=top_k, min_refs=min_refs)

    def ask_npc(self, npc_id, question, model=None, top_k=3, min_refs=2):
        from llms.llm_groq import chat as groq_chat

        prompt_result, chain_metadata = self.build_prompt(
            npc_id,
            question,
            top_k=top_k,
            min_refs=min_refs,
        )
        if not prompt_result:
            return None

        response_text = groq_chat(
            messages=prompt_result.messages,
            model=model or self.default_model,
        )
        return {
            "npc_id": npc_id,
            "response": response_text,
            "messages": prompt_result.messages,
            "flat_prompt": prompt_result.flat_prompt,
            "chain_metadata": chain_metadata,
        }
