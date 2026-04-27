import json
import re
import sys
from time import perf_counter

from db.repositories import ConversationRepo, NPCRepo, PlayerRepo, UserRepo
from llms.config import (
    DEFAULT_CHAT_MODEL,
    DEFAULT_CHAT_TEMPERATURE,
    DEFAULT_SUMMARY_TEMPERATURE,
)
from pipelines import ChatPipeline


class ChatService:
    def __init__(
        self,
        driver,
        embed_model,
        pipeline: ChatPipeline,
        default_model: str = DEFAULT_CHAT_MODEL,
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
        temperature=None,
        response_blocked=False,
    ) -> dict:
        trace = getattr(pipeline_result, "exchange_trace", None)
        candidate_claim_ids = list((getattr(trace, "candidate_claim_ids", None) or []))
        candidate_important_claim_ids = list((getattr(trace, "candidate_important_claim_ids", None) or []))
        selected_claim_ids = list((getattr(trace, "selected_claim_ids", None) or []))
        selected_important_claim_ids = list((getattr(trace, "selected_important_claim_ids", None) or []))
        normalized_used_claims = list(used_claims or [])
        important_lookup = {
            claim_id
            for claim_id in (selected_important_claim_ids or candidate_important_claim_ids)
            if isinstance(claim_id, str)
        }
        used_important_claim_ids = [
            claim_id for claim_id in normalized_used_claims if claim_id in important_lookup
        ]

        return {
            "pipeline_id": getattr(trace, "pipeline_id", None),
            "search_query": getattr(trace, "search_query", None),
            "candidate_claim_count": len(candidate_claim_ids),
            "selected_claim_count": len(selected_claim_ids),
            "used_claim_count": len(normalized_used_claims),
            "candidate_claim_ids": candidate_claim_ids,
            "candidate_important_claim_ids": candidate_important_claim_ids,
            "selected_claim_ids": selected_claim_ids,
            "selected_important_claim_ids": selected_important_claim_ids,
            "used_claim_ids": normalized_used_claims,
            "used_important_claim_ids": used_important_claim_ids,
            "remembered_claim_count": getattr(trace, "remembered_claim_count", 0) or 0,
            "selector_strategy": getattr(trace, "selector_strategy", None),
            "retrieval_latency_ms": retrieval_latency_ms,
            "llm_latency_ms": llm_latency_ms,
            "total_latency_ms": total_latency_ms,
            "search_top_k": getattr(trace, "search_top_k", None),
            "was_start_dialog": bool(getattr(trace, "was_start_dialog", False)),
            "model": model,
            "temperature": temperature,
            "response_blocked": response_blocked,
        }

    @staticmethod
    def _resolve_player_temperature(player_profile: dict | None) -> float:
        raw_temperature = (player_profile or {}).get("temperature")
        if raw_temperature is None:
            return DEFAULT_CHAT_TEMPERATURE
        return float(raw_temperature)

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
        from llms.chat import chat as llm_chat

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
                    "- Do not invent suspicions, theories, or new facts. Only summarize what was actually said or clearly established in the conversation.\n"
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
                    "- Uppfinn inte misstankar, teorier eller nya fakta. Sammanfatta endast vad som faktiskt sades eller tydligt fastställdes i samtalet.\n"
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

        summary = llm_chat(
            messages=messages,
            model=model or self.default_model,
            temperature=DEFAULT_SUMMARY_TEMPERATURE,
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
    def _filter_important_claim_ids(claim_ids: list[str], important_claim_ids: list[str]) -> list[str]:
        important_lookup = {claim_id.upper() for claim_id in important_claim_ids if isinstance(claim_id, str)}
        if not important_lookup:
            return []

        filtered: list[str] = []
        seen: set[str] = set()
        for claim_id in claim_ids or []:
            normalized_claim_id = claim_id.upper() if isinstance(claim_id, str) else ""
            if not normalized_claim_id or normalized_claim_id in seen:
                continue
            if normalized_claim_id not in important_lookup:
                continue
            seen.add(normalized_claim_id)
            filtered.append(normalized_claim_id)
        return filtered

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

    @staticmethod
    def _build_claim_content_lookup(chain_metadata: list[dict]) -> dict[str, str]:
        claim_content_by_id: dict[str, str] = {}
        for chain in chain_metadata or []:
            for claim in chain.get("claims") or []:
                claim_id = claim.get("claim_id")
                content = claim.get("content")
                if not isinstance(claim_id, str) or not isinstance(content, str):
                    continue
                normalized_claim_id = claim_id.upper()
                if (
                    normalized_claim_id
                    and content.strip()
                    and normalized_claim_id not in claim_content_by_id
                ):
                    claim_content_by_id[normalized_claim_id] = content.strip()
        return claim_content_by_id

    @staticmethod
    def _format_claims_for_repair(
        used_claims: list[str],
        claim_content_by_id: dict[str, str],
    ) -> str:
        lines: list[str] = []
        for claim_id in used_claims:
            normalized_claim_id = claim_id.upper() if isinstance(claim_id, str) else ""
            content = claim_content_by_id.get(normalized_claim_id)
            if normalized_claim_id and content:
                lines.append(f"- {normalized_claim_id}: {content}")
        return "\n".join(lines)

    @staticmethod
    def _extract_json_object(raw_text: str) -> dict | None:
        text = (raw_text or "").strip()
        if not text:
            return None

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

        parsed = cls._extract_json_object(raw_response)
        if not parsed:
            return "", []

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

    @classmethod
    def _repair_llm_chat_payload(
        cls,
        *,
        raw_response: str,
        model: str,
        locale: str,
    ) -> str:
        from llms.chat import chat as llm_chat

        if cls._is_english(locale):
            instruction = (
                "Return ONLY valid JSON with exactly the keys 'response' and 'used_claim_ids'.\n"
                "Preserve the same meaning as the original answer.\n"
                "Do not add new facts.\n"
                "Only keep claim IDs whose full concrete fact is explicitly expressed in the answer.\n"
                "If the answer only hints at, generalizes, or partially overlaps with a claim, remove that claim ID.\n"
                "If the original answer is uncertain or cannot be grounded, use an empty list for 'used_claim_ids'."
            )
        else:
            instruction = (
                "Returnera ENDAST giltig JSON med exakt nycklarna 'response' och 'used_claim_ids'.\n"
                "Bevara exakt samma innebörd som originalsvarat.\n"
                "Lägg inte till några nya fakta.\n"
                "Behåll bara claim-IDn vars hela konkreta fakta uttrycks tydligt i svaret.\n"
                "Om svaret bara antyder, generaliserar eller delvis överlappar en claim, ta bort det claim-ID:t.\n"
                "Om originalsvarat är osäkert eller inte kan grundas, använd en tom lista för 'used_claim_ids'."
            )

        return llm_chat(
            messages=[
                {"role": "system", "content": instruction},
                {"role": "user", "content": raw_response},
            ],
            model=model,
            temperature=0,
            max_tokens=256,
        )

    @classmethod
    def _repair_claim_usage_payload(
        cls,
        *,
        question: str,
        response_text: str,
        used_claims: list[str],
        claim_content_by_id: dict[str, str],
        model: str,
        locale: str,
    ) -> str | None:
        from llms.chat import chat as llm_chat

        claims_text = cls._format_claims_for_repair(used_claims, claim_content_by_id)
        if not claims_text:
            return None

        if cls._is_english(locale):
            instruction = (
                "You repair claim usage tracking for an NPC dialogue response.\n"
                "Return ONLY valid JSON with exactly the keys 'response' and 'used_claim_ids'.\n"
                "The response must stay brief, in character, and directly answer the detective's question.\n"
                "For every claim ID you keep, the response itself must explicitly express "
                "the full concrete information in that claim, including actors, objects, "
                "qualifiers, negations, and timing.\n"
                "If a claim is relevant and socially natural to say, revise the response "
                "so it says the full claim content.\n"
                "If a claim is not relevant or would make the answer unnatural, remove that claim ID instead.\n"
                "Do not add facts that are not in the listed claims or original response."
            )
            user_text = (
                f"DETECTIVE QUESTION:\n{question or '(start of conversation)'}\n\n"
                f"CURRENT RESPONSE:\n{response_text}\n\n"
                f"CLAIMS CURRENTLY MARKED AS USED:\n{claims_text}\n\n"
                "Return repaired JSON now."
            )
        else:
            instruction = (
                "Du reparerar claim-användning för ett NPC-dialogsvar.\n"
                "Returnera ENDAST giltig JSON med exakt nycklarna 'response' och 'used_claim_ids'.\n"
                "Svaret ska fortsätta vara kort, i karaktär och direkt besvara detektivens fråga.\n"
                "För varje claim-ID du behåller måste själva svaret uttryckligen säga hela "
                "den konkreta informationen i claimen, inklusive aktörer, objekt, "
                "förbehåll, negationer och tidsangivelser.\n"
                "Om en claim är relevant och socialt naturlig att säga, ändra svaret så "
                "att hela claimens innehåll sägs.\n"
                "Om en claim inte är relevant eller skulle göra svaret onaturligt, ta "
                "bort claim-ID:t istället.\n"
                "Lägg inte till fakta som inte finns i de listade claimsen eller originalsvaret."
            )
            user_text = (
                f"DETEKTIVENS FRÅGA:\n{question or '(start på samtal)'}\n\n"
                f"NUVARANDE SVAR:\n{response_text}\n\n"
                f"CLAIMS SOM JUST NU MARKERAS SOM ANVÄNDA:\n{claims_text}\n\n"
                "Returnera reparerad JSON nu."
            )

        return llm_chat(
            messages=[
                {"role": "system", "content": instruction},
                {"role": "user", "content": user_text},
            ],
            model=model,
            temperature=0,
            max_tokens=512,
        )

    def ask_npc(
        self,
        npc_id,
        question,
        model=None,
        conversation_id=None,
        player_id=None,
        repair_claim_usage=True,
    ):
        from llms.chat import chat as llm_chat
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
        player_profile = None
        if effective_player_id:
            player_profile = self.player_repo.get_profile_by_id(effective_player_id)
        resolved_temperature = self._resolve_player_temperature(player_profile)
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
                    temperature=resolved_temperature,
                    response_blocked=True,
                ),
            )
            return {
                "npc_id": npc_id,
                "npc_name": (npc_profile or {}).get("name") or "",
                "conversation_id": resolved_conversation_id,
                "response": refusal_message,
                "temperature": resolved_temperature,
                "used_claims": [],
                "important_claim_ids": [],
                "messages": [],
                "flat_prompt": "",
                "chain_metadata": [],
            }

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
        raw_response_text = llm_chat(
            messages=prompt_result.messages,
            model=resolved_model,
            temperature=resolved_temperature,
        )
        available_claim_ids = {claim_id.upper() for claim_id in pipeline_result.available_claim_ids}
        response_text, used_claims = self._parse_llm_chat_payload(
            raw_response=raw_response_text,
            allowed_ids=available_claim_ids,
        )
        if not response_text:
            repaired_response_text = self._repair_llm_chat_payload(
                raw_response=raw_response_text,
                model=resolved_model,
                locale=locale,
            )
            response_text, used_claims = self._parse_llm_chat_payload(
                raw_response=repaired_response_text,
                allowed_ids=available_claim_ids,
            )
        if repair_claim_usage and response_text and used_claims:
            original_response_text = response_text
            original_used_claims = list(used_claims)
            repaired_claim_usage_text = self._repair_claim_usage_payload(
                question=normalized_question,
                response_text=response_text,
                used_claims=used_claims,
                claim_content_by_id=self._build_claim_content_lookup(chain_metadata),
                model=resolved_model,
                locale=locale,
            )
            if repaired_claim_usage_text:
                repaired_response_text, repaired_used_claims = self._parse_llm_chat_payload(
                    raw_response=repaired_claim_usage_text,
                    allowed_ids=available_claim_ids,
                )
                if repaired_response_text:
                    response_changed = repaired_response_text != original_response_text
                    claims_changed = repaired_used_claims != original_used_claims
                    if response_changed or claims_changed:
                        print("[claim_usage_repair] changed response", file=sys.stderr)
                        print(f"from: {original_response_text}", file=sys.stderr)
                        print(f"to: {repaired_response_text}", file=sys.stderr)
                        original_claims_text = ", ".join(original_used_claims) or "(none)"
                        repaired_claims_text = ", ".join(repaired_used_claims) or "(none)"
                        print(f"used_claim_ids from: {original_claims_text}", file=sys.stderr)
                        print(f"used_claim_ids to: {repaired_claims_text}", file=sys.stderr)
                    response_text = repaired_response_text
                    used_claims = repaired_used_claims
        llm_end = perf_counter()
        llm_latency_ms = self._duration_ms(llm_start, llm_end)
        if not response_text:
            response_text = self._fallback_response_text(
                locale=locale,
                is_start_dialog=not normalized_question,
            )
        total_latency_ms = self._duration_ms(total_start, perf_counter())
        important_claim_ids = self._filter_important_claim_ids(
            used_claims,
            list((getattr(pipeline_result.exchange_trace, "selected_important_claim_ids", None) or [])),
        )

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
                temperature=resolved_temperature,
                response_blocked=False,
            ),
        )

        return {
            "npc_id": npc_id,
            "npc_name": localized_npc_name,
            "conversation_id": resolved_conversation_id,
            "response": response_text,
            "temperature": resolved_temperature,
            "used_claims": used_claims,
            "important_claim_ids": important_claim_ids,
            "messages": prompt_result.messages,
            "flat_prompt": prompt_result.flat_prompt,
            "chain_metadata": chain_metadata,
            "selector_debug": pipeline_result.selector_debug,
        }
