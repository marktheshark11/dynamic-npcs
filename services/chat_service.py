from rag.pipeline import RAGPipeline
from db.repositories import ConversationRepo


class ChatService:
    def __init__(self, driver, embed_model, default_model="llama-3.3-70b-versatile"):
        self.pipeline = RAGPipeline(driver, embed_model)
        self.conversation_repo = ConversationRepo(driver)
        self.default_model = default_model

    def build_prompt(self, npc_id, question):
        return self.pipeline.run(npc_id, question,)

    @staticmethod
    def _format_recent_exchanges(exchanges):
        if not exchanges:
            return ""

        lines = ["SENASTE SAMTAL I DENNA KONVERSATION:"]
        for exchange in exchanges:
            player_text = exchange.get("player_text") or ""
            npc_text = exchange.get("npc_text") or ""
            lines.append(f"- DETEKTIVEN: {player_text}")
            lines.append(f"- DU: {npc_text}")
        return "\n".join(lines)

    def _inject_recent_exchanges(self, messages, conversation_id):
        recent_exchanges = self.conversation_repo.list_exchanges(conversation_id, limit=3)
        recent_block = self._format_recent_exchanges(recent_exchanges)
        if not recent_block:
            return messages

        updated_messages = [dict(message) for message in messages]
        for message in updated_messages:
            if message.get("role") == "user":
                current = message.get("content") or ""
                message["content"] = f"{recent_block}\n\n{current}"
                break
        return updated_messages

    def _resolve_conversation_id(self, npc_id, conversation_id=None, new_conversation=False):
        if new_conversation or not conversation_id:
            return self.conversation_repo.create_conversation(npc_id)

        existing = self.conversation_repo.get_conversation(conversation_id)
        if not existing:
            return self.conversation_repo.create_conversation(npc_id)

        if existing["npc_id"] != npc_id:
            return self.conversation_repo.create_conversation(npc_id)

        return conversation_id

    def ask_npc(self, npc_id, question, model=None, conversation_id=None, new_conversation=False):
        from llms.llm_groq import chat as groq_chat

        resolved_conversation_id = self._resolve_conversation_id(
            npc_id=npc_id,
            conversation_id=conversation_id,
            new_conversation=new_conversation,
        )
        if not resolved_conversation_id:
            return None

        prompt_result, chain_metadata = self.build_prompt(
            npc_id,
            question,
        )
        if not prompt_result:
            return None

        messages_with_recent_context = self._inject_recent_exchanges(
            prompt_result.messages,
            resolved_conversation_id,
        )

        response_text = groq_chat(
            messages=messages_with_recent_context,
            model=model or self.default_model,
        )

        self.conversation_repo.append_exchange(
            conversation_id=resolved_conversation_id,
            player_text=question,
            npc_text=response_text,
        )

        return {
            "npc_id": npc_id,
            "conversation_id": resolved_conversation_id,
            "response": response_text,
            "messages": messages_with_recent_context,
            "flat_prompt": prompt_result.flat_prompt,
            "chain_metadata": chain_metadata,
        }
