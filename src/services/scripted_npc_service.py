from dataclasses import dataclass

from db.repositories import ConversationRepo, NPCRepo, PlayerRepo, UserRepo
from services.hint_service import HintService


@dataclass
class ScriptedNpcSessionState:
    mode: str = "idle"
    accusation_candidate_ids: list[str] | None = None


@dataclass
class ScriptedNpcReply:
    response: str
    game_completed: bool = False
    accused_correct_npc: bool | None = None
    accused_npc_id: str | None = None
    completed_at: str | None = None


class ScriptedNpcService:
    _ACCUSE_MODE = "awaiting_accusation_choice"
    _ACCUSATION_CANDIDATE_IDS = [
        "npc_beatrice",
        "npc_wilhelm",
        "npc_pamela",
        "npc_bergstrom",
        "npc_mariana",
    ]
    _CORRECT_MURDERER_ID = "npc_beatrice"
    _ABOUT_GAME_TEXT ="Det här är ett mordmysteriumspel där du är detektiven som ska lösa mordet. Behöver du hjälp? Gå in på Clues eller fråga mig om ledtrådar. Lycka till.d "
    _ABOUT_GAME_TEXT_EN = "This is a murder mystery game where you are the detective solving the murder. Need help? Go to Clues or ask me for hints. Good luck."

    def __init__(self, driver):
        self.conversation_repo = ConversationRepo(driver)
        self.hint_service = HintService(driver)
        self.npc_repo = NPCRepo(driver)
        self.player_repo = PlayerRepo(driver)
        self.user_repo = UserRepo(driver)
        self._session_states: dict[tuple[str, str, str], ScriptedNpcSessionState] = {}
        self._menu_text = (
            "1. Om spelet\n"
            "2. Få ledtråd\n"
            "3. Jag vet vem mördaren är, jag vill anklaga den och sedan avsluta spelet"
        )
        self._menu_text_en = (
            "1. About the game\n"
            "2. Get a hint\n"
            "3. I know who the murderer is, I want to accuse them and then end the game"
        )

    @staticmethod
    def _is_english(locale: str | None) -> bool:
        return (locale or "sv").strip().lower() == "en"

    def _resolve_locale(self, player_id: str | None) -> str:
        if not player_id:
            return "sv"
        return self.user_repo.get_locale_by_player_id(player_id)

    def ask_npc(
        self,
        npc_id: str,
        question: str | None = None,
        player_id: str | None = None,
        conversation_id: str | None = None,
    ) -> dict:
        resolved_conversation_id = self._resolve_conversation_id(
            npc_id=npc_id,
            player_id=player_id,
            conversation_id=conversation_id,
        )
        if not resolved_conversation_id:
            raise ValueError("Kunde inte skapa konversation för scripted NPC.")

        normalized_question = (question or "").strip()
        session_key = self._session_key(
            npc_id=npc_id,
            player_id=player_id,
            conversation_id=resolved_conversation_id,
        )
        session_state = self._session_states.get(session_key, ScriptedNpcSessionState())
        locale = self._resolve_locale(player_id)

        if player_id:
            player_profile = self.player_repo.get_profile_by_id(player_id)
            if not player_profile:
                raise ValueError("Kunde inte hitta spelaren.")
            if player_profile.get("has_completed_game"):
                raise ValueError("Spelet är redan avslutat för den här spelaren. Skapa en ny spelare för att fortsätta.")

        if session_state.mode == self._ACCUSE_MODE:
            reply = self._handle_accusation_follow_up(
                npc_id=npc_id,
                player_id=player_id,
                choice_text=normalized_question,
                session_key=session_key,
                session_state=session_state,
                locale=locale,
            )
        elif not normalized_question:
            reply = ScriptedNpcReply(response=self._menu_text_en if self._is_english(locale) else self._menu_text)
        else:
            reply = self._handle_choice(
                npc_id=npc_id,
                player_id=player_id,
                choice=self._parse_choice(normalized_question),
                conversation_id=resolved_conversation_id,
                locale=locale,
            )

        self.conversation_repo.append_exchange(
            conversation_id=resolved_conversation_id,
            player_text=normalized_question,
            npc_text=reply.response,
        )

        return {
            "npc_id": npc_id,
            "player_id": player_id,
            "conversation_id": resolved_conversation_id,
            "response": reply.response,
            "game_completed": reply.game_completed,
            "accused_correct_npc": reply.accused_correct_npc,
            "accused_npc_id": reply.accused_npc_id,
            "completed_at": reply.completed_at,
        }

    def _resolve_conversation_id(
        self,
        npc_id: str,
        player_id: str | None,
        conversation_id: str | None,
    ) -> str | None:
        if conversation_id:
            existing = self.conversation_repo.get_conversation(conversation_id)
            if existing and existing.get("npc_id") == npc_id:
                existing_player_id = existing.get("player_id")
                if player_id and existing_player_id and existing_player_id != player_id:
                    return self.conversation_repo.create_conversation(npc_id, player_id=player_id)
                if player_id and not existing_player_id:
                    self.conversation_repo.link_player(conversation_id, player_id)
                return conversation_id

        return self.conversation_repo.create_conversation(npc_id, player_id=player_id)

    @staticmethod
    def _session_key(
        npc_id: str,
        player_id: str | None,
        conversation_id: str,
    ) -> tuple[str, str, str]:
        return npc_id, player_id or "__anonymous__", conversation_id

    @staticmethod
    def _parse_choice(raw_choice: str) -> int:
        try:
            return int(raw_choice)
        except ValueError as exc:
            raise ValueError("Ogiltigt val. Skicka ett heltal, till exempel 1, 2 eller 3.") from exc

    def _handle_choice(
        self,
        npc_id: str,
        player_id: str | None,
        choice: int,
        conversation_id: str,
        locale: str,
    ) -> ScriptedNpcReply:
        is_english = self._is_english(locale)
        if choice == 1:
            return ScriptedNpcReply(response=self._ABOUT_GAME_TEXT_EN if is_english else self._ABOUT_GAME_TEXT)
        if choice == 2:
            if not player_id:
                raise ValueError("player_id is required to fetch hints." if is_english else "player_id krävs för att hämta hintar.")
            return ScriptedNpcReply(response=self.hint_service.get_hint_text(player_id=player_id))
        if choice == 3:
            return self._begin_accusation_flow(
                npc_id=npc_id,
                player_id=player_id,
                conversation_id=conversation_id,
                locale=locale,
            )
        return ScriptedNpcReply(response="Invalid choice. Send an empty message to see the menu or type 1, 2 or 3." if is_english else "Ogiltigt val. Skicka tomt för att se menyn eller skriv 1, 2 eller 3.")

    def _begin_accusation_flow(
        self,
        npc_id: str,
        player_id: str | None,
        conversation_id: str,
        locale: str,
    ) -> ScriptedNpcReply:
        is_english = self._is_english(locale)
        candidate_lines: list[str] = []
        candidate_ids: list[str] = []

        for npc_candidate_id in self._ACCUSATION_CANDIDATE_IDS:
            npc = self.npc_repo.get_by_id(npc_candidate_id)
            if not npc:
                continue
            candidate_ids.append(npc.id)
            candidate_lines.append(f"{len(candidate_ids)}. {npc.name}")

        if not candidate_ids:
            raise ValueError("Could not load accusation candidates." if is_english else "Kunde inte hämta kandidater för anklagelsen.")

        self._session_states[self._session_key(
            npc_id=npc_id,
            player_id=player_id,
            conversation_id=conversation_id,
        )] = ScriptedNpcSessionState(
            mode=self._ACCUSE_MODE,
            accusation_candidate_ids=candidate_ids,
        )

        return ScriptedNpcReply(
            response=(
                ("Who do you accuse?\n" if is_english else "Vem anklagar du?\n")
                + "\n".join(candidate_lines)
                + ("\nReply with the number of the person you want to accuse." if is_english else "\nSvara med siffran för den person du vill anklaga.")
            )
        )

    def _handle_accusation_follow_up(
        self,
        npc_id: str,
        player_id: str | None,
        choice_text: str,
        session_key: tuple[str, str, str],
        session_state: ScriptedNpcSessionState,
        locale: str,
    ) -> ScriptedNpcReply:
        is_english = self._is_english(locale)
        candidate_ids = session_state.accusation_candidate_ids or []
        if not candidate_ids:
            self._session_states.pop(session_key, None)
            raise ValueError("The accusation could not continue. Try again from the menu." if is_english else "Anklagelsen kunde inte fortsätta. Försök igen från menyn.")

        if not choice_text:
            return self._repeat_accusation_candidates(candidate_ids, locale)

        try:
            choice = int(choice_text)
        except ValueError as exc:
            raise ValueError(
                f"Invalid choice. Select a candidate by sending a number between 1 and {len(candidate_ids)}." if is_english else f"Ogiltigt val. Välj en kandidat genom att skicka en siffra mellan 1 och {len(candidate_ids)}."
            ) from exc

        if choice < 1 or choice > len(candidate_ids):
            raise ValueError(
                f"Invalid choice. Select a candidate by sending a number between 1 and {len(candidate_ids)}." if is_english else f"Ogiltigt val. Välj en kandidat genom att skicka en siffra mellan 1 och {len(candidate_ids)}."
            )

        accused_npc_id = candidate_ids[choice - 1]
        self._session_states.pop(session_key, None)
        return self._resolve_accusation(npc_id=npc_id, player_id=player_id, accused_npc_id=accused_npc_id, locale=locale)

    def _repeat_accusation_candidates(self, candidate_ids: list[str], locale: str) -> ScriptedNpcReply:
        is_english = self._is_english(locale)
        lines: list[str] = []
        for index, npc_candidate_id in enumerate(candidate_ids, start=1):
            npc = self.npc_repo.get_by_id(npc_candidate_id)
            if not npc:
                continue
            lines.append(f"{index}. {npc.name}")

        if not lines:
            raise ValueError("Could not show the candidate list again. Start over from the menu." if is_english else "Kunde inte visa kandidatlistan igen. Börja om från menyn.")

        return ScriptedNpcReply(response=("Choose a candidate:\n" if is_english else "Välj en kandidat:\n") + "\n".join(lines))

    def _resolve_accusation(self, npc_id: str, player_id: str | None, accused_npc_id: str, locale: str) -> ScriptedNpcReply:
        is_english = self._is_english(locale)
        accused_npc = self.npc_repo.get_by_id(accused_npc_id)
        if not accused_npc:
            raise ValueError("Could not load the accused person." if is_english else "Kunde inte hämta den anklagade personen.")

        result = self._finalize_game(player_id=player_id, npc_id=npc_id, accused_npc_id=accused_npc_id)
        is_correct = bool(result["accused_correct_npc"])

        if is_correct:
            return ScriptedNpcReply(
                response="Yes. That matches what you have presented." if is_english else "Ja. Det stämmer med det du har lagt fram.'",
                game_completed=True,
                accused_correct_npc=True,
                accused_npc_id=accused_npc_id,
                completed_at=result.get("completed_at"),
            )

        return ScriptedNpcReply(
            response="Unfortunately, you are wrong." if is_english else "Tyvärr, du har fel.",
            game_completed=True,
            accused_correct_npc=False,
            accused_npc_id=accused_npc_id,
            completed_at=result.get("completed_at"),
        )

    def _finalize_game(
        self,
        player_id: str | None,
        npc_id: str,
        accused_npc_id: str,
    ) -> dict:
        del npc_id

        if not player_id:
            raise ValueError("player_id krävs för att avsluta spelet.")

        result = self.player_repo.complete_game(
            player_id=player_id,
            accused_npc_id=accused_npc_id,
            correct_npc_id=self._CORRECT_MURDERER_ID,
        )
        if not result:
            raise ValueError("Spelet är redan avslutat för den här spelaren. Skapa en ny spelare för att fortsätta.")
        return result
