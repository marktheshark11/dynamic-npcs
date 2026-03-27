import json
import re

from rag.pipeline import RAGPipeline
from db.repositories import ConversationRepo, PlayerRepo


class ChatService:
    def __init__(self, driver, embed_model, default_model="llama-3.3-70b-versatile"):
        self.pipeline = RAGPipeline(driver, embed_model)
        self.conversation_repo = ConversationRepo(driver)
        self.player_repo = PlayerRepo(driver)
        self.default_model = default_model

    def build_prompt(
        self,
        npc_id,
        question,
        player_profile=None,
        recent_exchanges=None,
        player_id=None,
        conversation_claim_ids=None,
    ):
        return self.pipeline.run(
            npc_id,
            question,
            player_profile=player_profile,
            recent_exchanges=recent_exchanges,
            player_id=player_id,
            conversation_claim_ids=conversation_claim_ids,
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

    @staticmethod
    def _extract_available_claim_ids(chain_metadata: list[dict]) -> set[str]:
        available_ids: set[str] = set()
        for chain in chain_metadata or []:
            content = chain.get("content") or ""
            for match in re.findall(r"<\s*(C\d+)\s*>", content, flags=re.IGNORECASE):
                available_ids.add(match.upper())
        return available_ids

    @staticmethod
    def _normalize_claim_ids(raw_ids: list[str], allowed_ids: set[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()

        for raw in raw_ids:
            if not isinstance(raw, str):
                continue
            match = re.search(r"C\d+", raw.upper())
            if not match:
                continue
            claim_id = match.group(0)
            if claim_id in seen:
                continue
            if allowed_ids and claim_id not in allowed_ids:
                continue
            seen.add(claim_id)
            normalized.append(claim_id)

        return normalized

    @classmethod
    def _parse_llm_chat_payload(cls, raw_response: str, allowed_ids: set[str]) -> tuple[str, list[str]]:
        if not raw_response:
            return "", []

        text = raw_response.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text).strip()

        parsed: dict | None = None
        candidates = [text]
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            candidates.append(json_match.group(0))

        for candidate in candidates:
            try:
                obj = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                parsed = obj
                break

        if not parsed:
            return raw_response.strip(), []

        response_value = parsed.get("response")
        if isinstance(response_value, str):
            response_text = response_value.strip()
        else:
            response_text = ""
        raw_claim_ids = parsed.get("used_claim_ids")
        if not isinstance(raw_claim_ids, list):
            raw_claim_ids = []

        claim_ids = cls._normalize_claim_ids(raw_claim_ids, allowed_ids)
        if not response_text:
            return raw_response.strip(), claim_ids
        return response_text, claim_ids

    def ask_npc(self, npc_id, question, model=None, conversation_id=None, player_id=None):
        from llms.llm_groq import chat as groq_chat
        from llms.prompt_guard import is_malicious

        refusal_message = (
            "Jag kommer inte att svara på den typen av frågor."
        )

        resolved_conversation_id = self._resolve_conversation_id(
            npc_id=npc_id,
            conversation_id=conversation_id,
            player_id=player_id,
        )
        if not resolved_conversation_id:
            return None

        if is_malicious(question):
            self.conversation_repo.append_exchange(
                conversation_id=resolved_conversation_id,
                player_text=question,
                npc_text=refusal_message,
            )
            return {
                "npc_id": npc_id,
                "conversation_id": resolved_conversation_id,
                "response": refusal_message,
                "used_claims": [],
                "messages": [],
                "flat_prompt": "",
                "chain_metadata": [],
            }

        effective_player_id = player_id
        if not effective_player_id:
            conversation = self.conversation_repo.get_conversation(resolved_conversation_id)
            if conversation:
                effective_player_id = conversation.get("player_id")

        player_profile = None
        if effective_player_id:
            player_profile = self.player_repo.get_profile_by_id(effective_player_id)

        recent_exchanges = self.conversation_repo.list_exchanges(resolved_conversation_id, limit=5)
        conversation_claim_ids = self.conversation_repo.get_mentioned_claim_ids(resolved_conversation_id)

        prompt_result, chain_metadata = self.build_prompt(
            npc_id,
            question,
            player_profile=player_profile,
            recent_exchanges=recent_exchanges,
            player_id=effective_player_id,
            conversation_claim_ids=conversation_claim_ids,
        )
        if not prompt_result:
            return None

        raw_response_text = groq_chat(
            messages=prompt_result.messages,
            model=model or self.default_model,
        )
        available_claim_ids = self._extract_available_claim_ids(chain_metadata)
        response_text, used_claims = self._parse_llm_chat_payload(
            raw_response=raw_response_text,
            allowed_ids=available_claim_ids,
        )

        if used_claims:
            self.conversation_repo.add_mentioned_claim_ids(resolved_conversation_id, used_claims)

        if effective_player_id and used_claims:
            self.player_repo.mark_aware_of(effective_player_id, used_claims, npc_id=npc_id)

        self.conversation_repo.append_exchange(
            conversation_id=resolved_conversation_id,
            player_text=question,
            npc_text=response_text,
        )

        return {
            "npc_id": npc_id,
            "conversation_id": resolved_conversation_id,
            "response": response_text,
            "used_claims": used_claims,
            "messages": prompt_result.messages,
            "flat_prompt": prompt_result.flat_prompt,
            "chain_metadata": chain_metadata,
        }
