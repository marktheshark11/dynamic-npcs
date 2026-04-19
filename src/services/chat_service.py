import json
import re
from time import perf_counter

from db.repositories import ConversationRepo, NPCRepo, PlayerRepo, UserRepo
from pipelines import ChatPipeline


class ChatService:
    def __init__(
        self,
        driver,
        embed_model,
        pipeline: ChatPipeline,
        default_model="llama-3.3-70b-versatile",
    ):
        self.pipeline = pipeline
        self.conversation_repo = ConversationRepo(driver)
        self.npc_repo = NPCRepo(driver)
        self.player_repo = PlayerRepo(driver)
        self.user_repo = UserRepo(driver)
        self.default_model = default_model

    def _get_pipeline(self) -> ChatPipeline:
        return self.pipeline

    @staticmethod
    def _duration_ms(start_time: float, end_time: float) -> int:
        return max(0, int((end_time - start_time) * 1000))

    @staticmethod
    def _build_exchange_trace(
        *,
        pipeline_result=None,
        used_claims=None,
        retrieval_latency_ms=None,
        llm_latency_ms=None,
        total_latency_ms=None,
        model=None,
        response_blocked=False,
    ) -> dict:
        trace = getattr(pipeline_result, "exchange_trace", None)
        candidate_claim_ids = list((getattr(trace, "candidate_claim_ids", None) or []))
        selected_claim_ids = list((getattr(trace, "selected_claim_ids", None) or []))
        normalized_used_claims = list(used_claims or [])

        return {
            "pipeline_id": getattr(trace, "pipeline_id", None),
            "search_query": getattr(trace, "search_query", None),
            "candidate_claim_count": len(candidate_claim_ids),
            "selected_claim_count": len(selected_claim_ids),
            "used_claim_count": len(normalized_used_claims),
            "candidate_claim_ids": candidate_claim_ids,
            "selected_claim_ids": selected_claim_ids,
            "used_claim_ids": normalized_used_claims,
            "remembered_claim_count": getattr(trace, "remembered_claim_count", 0) or 0,
            "selector_strategy": getattr(trace, "selector_strategy", None),
            "retrieval_latency_ms": retrieval_latency_ms,
            "llm_latency_ms": llm_latency_ms,
            "total_latency_ms": total_latency_ms,
            "search_top_k": getattr(trace, "search_top_k", None),
            "was_start_dialog": bool(getattr(trace, "was_start_dialog", False)),
            "model": model,
            "response_blocked": response_blocked,
        }

    def build_prompt(
        self,
        npc_id,
        question,
        player_profile=None,
        recent_exchanges=None,
        prior_conversation_summaries=None,
        player_id=None,
        conversation_claim_ids=None,
        locale="sv",
    ):
        return self._get_pipeline().run(
            npc_id,
            question,
            player_profile=player_profile,
            recent_exchanges=recent_exchanges,
            prior_conversation_summaries=prior_conversation_summaries,
            player_id=player_id,
            conversation_claim_ids=conversation_claim_ids,
            locale=locale,
        )

    def _resolve_locale(self, player_id: str | None) -> str:
        if not player_id:
            return "sv"
        return self.user_repo.get_locale_by_player_id(player_id)

    def _get_prior_conversation_summaries(self, npc_id, player_id, conversation_id):
        if not player_id:
            return []

        return self.conversation_repo.list_recent_summaries_for_npc_and_player(
            npc_id=npc_id,
            player_id=player_id,
            exclude_conversation_id=conversation_id,
            limit=2,
        )

    @staticmethod
    def _is_english(locale: str | None) -> bool:
        return (locale or "sv").strip().lower() == "en"

    @staticmethod
    def _format_all_exchanges_for_summary(exchanges, locale="sv"):
        is_english = ChatService._is_english(locale)
        if not exchanges:
            return "(No messages in the conversation)" if is_english else "(Inga meddelanden i konversationen)"

        lines = []
        for exchange in exchanges:
            turn_index = exchange.get("turn_index")
            player_text = exchange.get("player_text") or ""
            npc_text = exchange.get("npc_text") or ""
            if player_text:
                prefix = "Turn" if is_english else "Tur"
                speaker = "DETECTIVE" if is_english else "DETEKTIVEN"
                lines.append(f"{prefix} {turn_index} - {speaker}: {player_text}")
            if npc_text:
                prefix = "Turn" if is_english else "Tur"
                speaker = "YOU" if is_english else "DU"
                lines.append(f"{prefix} {turn_index} - {speaker}: {npc_text}")
        return "\n".join(lines)

    def summarize_conversation(self, conversation_id, model=None):
        from llms.llm_groq import chat as groq_chat

        conversation = self.conversation_repo.get_conversation(conversation_id)
        if not conversation:
            return None

        locale = self._resolve_locale(conversation.get("player_id"))
        is_english = self._is_english(locale)
        npc_profile = self.npc_repo.get_profile_by_id(conversation.get("npc_id"), locale=locale)
        exchanges = self.conversation_repo.list_exchanges(conversation_id)
        transcript = self._format_all_exchanges_for_summary(exchanges, locale=locale)
        npc_name = (npc_profile or {}).get("name") or conversation.get("npc_id") or ("the NPC" if is_english else "NPC:n")
        personality = (npc_profile or {}).get("personality") or ("Unknown" if is_english else "Okänd")
        backstory = (npc_profile or {}).get("backstory") or ("Unknown" if is_english else "Okänd")
        story_background = (npc_profile or {}).get("story_background") or ("Unknown" if is_english else "Okänt")

        messages = [
            {
                "role": "system",
                "content": (
                    "You are writing a conversation summary as the NPC themself, in first person.\n\n"
                    f"You are {npc_name}.\n"
                    f"Personality: {personality}\n"
                    f"Background: {backstory}\n"
                    f"What has happened in the story: {story_background}\n\n"
                    "Instructions:\n"
                    "- The only language you understand is English. If you receive input in another language, say you don't understand it.\n"
                    "- Write in first person, from your own perspective.\n"
                    "- Describe what I learned, what I told them, what I avoided, what I suspect, and how I perceived the detective if relevant.\n"
                    "- Refer to the detective as 'the detective', never as 'I'.\n"
                    "- Never write about me in third person or with my name as if I were someone else.\n"
                    "- Be concise but concrete enough to be useful as a memory note for future conversations. About 1-2 sentences is good.\n"
                    "- Include what is important for the character to remember, and leave out unimportant fluff."
                ) if is_english else (
                    "Du skriver en konversationssammanfattning som NPC:n själv, i jag-form.\n\n"
                    f"Du är {npc_name}.\n"
                    f"Personlighet: {personality}\n"
                    f"Bakgrund: {backstory}\n"
                    f"Vad som har hänt i berättelsen: {story_background}\n\n"
                    "Instruktioner:\n"
                    "- Det enda språket du förstår är svenska. Om du får indata på ett annat språk, säg att du inte förstår det.\n"
                    "- Skriv i första person, ur ditt eget perspektiv.\n"
                    "- Beskriv vad jag fick veta, vad jag berättade, vad jag undvek, vad jag misstänker, och hur jag uppfattade detektiven om det är relevant.\n"
                    "- Nämn detektiven som 'detektiven', aldrig som 'jag'.\n"
                    "- Skriv aldrig om mig själv i tredje person eller med mitt namn som om jag vore någon annan.\n"
                    "- Var kortfattad men tillräckligt konkret för att vara användbar som minnesanteckning inför framtida samtal. Ca 1-2 meningar är bra.\n"
                    "- Ta med sådant som är viktigt för karaktären att minnas, och utelämna ointressant fluff."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Here is the full conversation to summarize.\n\n"
                    f"Conversation ID: {conversation_id}\n"
                    f"NPC ID: {conversation.get('npc_id')}\n\n"
                    f"Conversation:\n{transcript}\n\n"
                    "Now write the summary in first person from the NPC's perspective."
                ) if is_english else (
                    "Här är hela samtalet som ska sammanfattas.\n\n"
                    f"Konversations-ID: {conversation_id}\n"
                    f"NPC ID: {conversation.get('npc_id')}\n\n"
                    f"Samtal:\n{transcript}\n\n"
                    "Skriv nu sammanfattningen i jag-form ur NPC:ns perspektiv."
                ),
            },
        ]

        summary = groq_chat(
            messages=messages,
            model=model or self.default_model,
        ).strip()
        if not summary:
            summary = "No summary could be generated." if is_english else "Ingen sammanfattning kunde genereras."

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

    @staticmethod
    def _normalize_response_text(raw_text: str) -> str:
        text = (raw_text or "").strip()
        if not text:
            return ""

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return text

        if isinstance(parsed, str):
            return parsed.strip()

        return text

    @classmethod
    def _fallback_response_text(cls, locale: str | None, is_start_dialog: bool) -> str:
        if is_start_dialog:
            return "Good morning, detective." if cls._is_english(locale) else "God morgon, detektiven."
        return (
            "I am not sure how to answer that."
            if cls._is_english(locale)
            else "Jag är inte säker på hur jag ska svara på det."
        )

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
            return cls._normalize_response_text(raw_response), []

        response_value = parsed.get("response")
        if isinstance(response_value, str):
            response_text = cls._normalize_response_text(response_value)
        else:
            response_text = ""
        raw_claim_ids = parsed.get("used_claim_ids")
        if not isinstance(raw_claim_ids, list):
            raw_claim_ids = []

        claim_ids = cls._normalize_claim_ids(raw_claim_ids, allowed_ids)
        if not response_text:
            return "", claim_ids
        return response_text, claim_ids

    def ask_npc(self, npc_id, question, model=None, conversation_id=None, player_id=None):
        from llms.llm_groq import chat as groq_chat
        from llms.prompt_guard import is_malicious

        total_start = perf_counter()
        resolved_conversation_id = self._resolve_conversation_id(
            npc_id=npc_id,
            conversation_id=conversation_id,
            player_id=player_id,
        )
        if not resolved_conversation_id:
            return None

        normalized_question = (question or "").strip()

        effective_player_id = player_id
        if not effective_player_id:
            conversation = self.conversation_repo.get_conversation(resolved_conversation_id)
            if conversation:
                effective_player_id = conversation.get("player_id")

        locale = self._resolve_locale(effective_player_id)
        resolved_model = model or self.default_model
        refusal_message = (
            "I will not answer that kind of question."
            if self._is_english(locale)
            else "Jag kommer inte att svara på den typen av frågor."
        )

        if normalized_question and is_malicious(normalized_question):
            npc_profile = self.npc_repo.get_profile_by_id(npc_id, locale=locale)
            blocked_total_latency_ms = self._duration_ms(total_start, perf_counter())
            self.conversation_repo.append_exchange(
                conversation_id=resolved_conversation_id,
                player_text=normalized_question,
                npc_text=refusal_message,
                trace=self._build_exchange_trace(
                    used_claims=[],
                    total_latency_ms=blocked_total_latency_ms,
                    response_blocked=True,
                ),
            )
            return {
                "npc_id": npc_id,
                "npc_name": (npc_profile or {}).get("name") or "",
                "conversation_id": resolved_conversation_id,
                "response": refusal_message,
                "used_claims": [],
                "messages": [],
                "flat_prompt": "",
                "chain_metadata": [],
            }

        player_profile = None
        if effective_player_id:
            player_profile = self.player_repo.get_profile_by_id(effective_player_id)

        recent_exchanges = self.conversation_repo.list_exchanges(resolved_conversation_id, limit=3)
        conversation_claim_ids = self.conversation_repo.get_mentioned_claim_ids(resolved_conversation_id)
        prior_conversation_summaries = self._get_prior_conversation_summaries(
            npc_id=npc_id,
            player_id=effective_player_id,
            conversation_id=resolved_conversation_id,
        )

        retrieval_start = perf_counter()
        if not normalized_question:
            pipeline_result = self._get_pipeline().run_start_dialog(
                npc_id,
                player_profile=player_profile,
                recent_exchanges=recent_exchanges,
                prior_conversation_summaries=prior_conversation_summaries,
                locale=locale,
            )
        else:
            pipeline_result = self.build_prompt(
                npc_id,
                normalized_question,
                player_profile=player_profile,
                recent_exchanges=recent_exchanges,
                prior_conversation_summaries=prior_conversation_summaries,
                player_id=effective_player_id,
                conversation_claim_ids=conversation_claim_ids,
                locale=locale,
            )
        retrieval_end = perf_counter()
        retrieval_latency_ms = self._duration_ms(retrieval_start, retrieval_end)
        prompt_result = pipeline_result.prompt_result
        chain_metadata = pipeline_result.chain_metadata
        if not prompt_result:
            return None

        npc_profile = self.npc_repo.get_profile_by_id(npc_id, locale=locale)
        localized_npc_name = (npc_profile or {}).get("name") or ""

        llm_start = perf_counter()
        raw_response_text = groq_chat(
            messages=prompt_result.messages,
            model=resolved_model,
        )
        llm_end = perf_counter()
        llm_latency_ms = self._duration_ms(llm_start, llm_end)
        available_claim_ids = {claim_id.upper() for claim_id in pipeline_result.available_claim_ids}
        response_text, used_claims = self._parse_llm_chat_payload(
            raw_response=raw_response_text,
            allowed_ids=available_claim_ids,
        )
        if not response_text:
            response_text = self._fallback_response_text(
                locale=locale,
                is_start_dialog=not normalized_question,
            )
        total_latency_ms = self._duration_ms(total_start, perf_counter())

        if used_claims:
            self.conversation_repo.add_mentioned_claim_ids(resolved_conversation_id, used_claims)

        if effective_player_id and used_claims:
            self.player_repo.mark_aware_of(effective_player_id, used_claims, npc_id=npc_id)

        self.conversation_repo.append_exchange(
            conversation_id=resolved_conversation_id,
            player_text=normalized_question,
            npc_text=response_text,
            trace=self._build_exchange_trace(
                pipeline_result=pipeline_result,
                used_claims=used_claims,
                retrieval_latency_ms=retrieval_latency_ms,
                llm_latency_ms=llm_latency_ms,
                total_latency_ms=total_latency_ms,
                model=resolved_model,
                response_blocked=False,
            ),
        )

        return {
            "npc_id": npc_id,
            "npc_name": localized_npc_name,
            "conversation_id": resolved_conversation_id,
            "response": response_text,
            "used_claims": used_claims,
            "messages": prompt_result.messages,
            "flat_prompt": prompt_result.flat_prompt,
            "chain_metadata": chain_metadata,
            "selector_debug": pipeline_result.selector_debug,
        }
