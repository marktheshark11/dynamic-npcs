from rag.pipeline import RAGPipeline
from db.repositories import ConversationRepo, PlayerRepo


class ChatService:
    def __init__(self, driver, embed_model, default_model="llama-3.3-70b-versatile"):
        self.pipeline = RAGPipeline(driver, embed_model)
        self.conversation_repo = ConversationRepo(driver)
        self.player_repo = PlayerRepo(driver)
        self.default_model = default_model

    def build_prompt(self, npc_id, question, player_profile=None, recent_exchanges=None):
        return self.pipeline.run(
            npc_id,
            question,
            player_profile=player_profile,
            recent_exchanges=recent_exchanges,
        )

    @staticmethod
    def _format_all_exchanges_for_summary(exchanges):
        if not exchanges:
            return "(Inga exchanges i konversationen)"

        lines = []
        for exchange in exchanges:
            turn_index = exchange.get("turn_index")
            player_text = exchange.get("player_text") or ""
            npc_text = exchange.get("npc_text") or ""
            lines.append(f"Turn {turn_index} - Detektiven: {player_text}")
            lines.append(f"Turn {turn_index} - NPC: {npc_text}")
        return "\n".join(lines)

    def summarize_conversation(self, conversation_id, model=None):
        from llms.llm_groq import chat as groq_chat

        conversation = self.conversation_repo.get_conversation(conversation_id)
        if not conversation:
            return None

        exchanges = self.conversation_repo.list_exchanges(conversation_id)
        transcript = self._format_all_exchanges_for_summary(exchanges)

        messages = [
            {
                "role": "system",
                "content": (
                    "Du summerar en konversation mellan en detektiv och dig själv. "
                    "Skriv en kort, tydlig sammanfattning på svenska i max 3 meningar från ditt perspektiv. "
                    "Ta med allt som skulle vara viktigt för karaktären. "
                    "Undvik fluff och upprepningar."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Konversation: {conversation_id}\n"
                    f"NPC ID: {conversation.get('npc_id')}\n\n"
                    f"{transcript}"
                ),
            },
        ]

        summary = groq_chat(
            messages=messages,
            model=model or self.default_model,
        ).strip()
        if not summary:
            summary = "Ingen sammanfattning kunde genereras."

        updated = self.conversation_repo.update_summary(conversation_id, summary)
        if not updated:
            return None

        return {
            "conversation_id": conversation_id,
            "summary": summary,
            "exchange_count": len(exchanges),
        }

    def _resolve_conversation_id(self, npc_id, conversation_id=None, player_id=None):
        if not conversation_id:
            return self.conversation_repo.create_conversation(npc_id, player_id=player_id)

        existing = self.conversation_repo.get_conversation(conversation_id)
        if not existing:
            return self.conversation_repo.create_conversation(npc_id, player_id=player_id)

        if existing["npc_id"] != npc_id:
            return self.conversation_repo.create_conversation(npc_id, player_id=player_id)

        if player_id and existing.get("player_id") and existing.get("player_id") != player_id:
            return self.conversation_repo.create_conversation(npc_id, player_id=player_id)

        if player_id and not existing.get("player_id"):
            self.conversation_repo.link_player(conversation_id, player_id)

        return conversation_id

    def ask_npc(self, npc_id, question, model=None, conversation_id=None, player_id=None):
        from llms.llm_groq import chat as groq_chat

        resolved_conversation_id = self._resolve_conversation_id(
            npc_id=npc_id,
            conversation_id=conversation_id,
            player_id=player_id,
        )
        if not resolved_conversation_id:
            return None

        effective_player_id = player_id
        if not effective_player_id:
            conversation = self.conversation_repo.get_conversation(resolved_conversation_id)
            if conversation:
                effective_player_id = conversation.get("player_id")

        player_profile = None
        if effective_player_id:
            player_profile = self.player_repo.get_profile_by_id(effective_player_id)

        recent_exchanges = self.conversation_repo.list_exchanges(resolved_conversation_id, limit=3)

        prompt_result, chain_metadata = self.build_prompt(
            npc_id,
            question,
            player_profile=player_profile,
            recent_exchanges=recent_exchanges,
        )
        if not prompt_result:
            return None

        response_text = groq_chat(
            messages=prompt_result.messages,
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
            "messages": prompt_result.messages,
            "flat_prompt": prompt_result.flat_prompt,
            "chain_metadata": chain_metadata,
        }
