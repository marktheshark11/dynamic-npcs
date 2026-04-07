from dataclasses import dataclass

from db.repositories import NPCRepo, PlayerRepo
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

    def __init__(self, driver):
        self.hint_service = HintService(driver)
        self.npc_repo = NPCRepo(driver)
        self.player_repo = PlayerRepo(driver)
        self._session_states: dict[tuple[str, str], ScriptedNpcSessionState] = {}
        self._menu_text = (
            "1. Om spelet\n"
            "2. Få ledtråd\n"
            "3. Jag vet vem mördaren är, jag vill anklaga den och sedan avsluta spelet"
        )

    def ask_npc(self, npc_id: str, question: str | None = None, player_id: str | None = None) -> dict:
        normalized_question = (question or "").strip()
        session_key = self._session_key(npc_id=npc_id, player_id=player_id)
        session_state = self._session_states.get(session_key, ScriptedNpcSessionState())

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
            )
        elif not normalized_question:
            reply = ScriptedNpcReply(response=self._menu_text)
        else:
            reply = self._handle_choice(
                npc_id=npc_id,
                player_id=player_id,
                choice=self._parse_choice(normalized_question),
            )

        return {
            "npc_id": npc_id,
            "player_id": player_id,
            "response": reply.response,
            "game_completed": reply.game_completed,
            "accused_correct_npc": reply.accused_correct_npc,
            "accused_npc_id": reply.accused_npc_id,
            "completed_at": reply.completed_at,
        }

    @staticmethod
    def _session_key(npc_id: str, player_id: str | None) -> tuple[str, str]:
        return npc_id, player_id or "__anonymous__"

    @staticmethod
    def _parse_choice(raw_choice: str) -> int:
        try:
            return int(raw_choice)
        except ValueError as exc:
            raise ValueError("Ogiltigt val. Skicka ett heltal, till exempel 1, 2 eller 3.") from exc

    def _handle_choice(self, npc_id: str, player_id: str | None, choice: int) -> ScriptedNpcReply:
        if choice == 1:
            return ScriptedNpcReply(response=self._ABOUT_GAME_TEXT)
        if choice == 2:
            if not player_id:
                raise ValueError("player_id krävs för att hämta hintar.")
            return ScriptedNpcReply(response=self.hint_service.get_hint_text(player_id=player_id))
        if choice == 3:
            return self._begin_accusation_flow(npc_id=npc_id, player_id=player_id)
        return ScriptedNpcReply(response="Ogiltigt val. Skicka tomt för att se menyn eller skriv 1, 2 eller 3.")

    def _begin_accusation_flow(self, npc_id: str, player_id: str | None) -> ScriptedNpcReply:
        candidate_lines: list[str] = []
        candidate_ids: list[str] = []

        for npc_candidate_id in self._ACCUSATION_CANDIDATE_IDS:
            npc = self.npc_repo.get_by_id(npc_candidate_id)
            if not npc:
                continue
            candidate_ids.append(npc.id)
            candidate_lines.append(f"{len(candidate_ids)}. {npc.name}")

        if not candidate_ids:
            raise ValueError("Kunde inte hämta kandidater för anklagelsen.")

        self._session_states[self._session_key(npc_id=npc_id, player_id=player_id)] = ScriptedNpcSessionState(
            mode=self._ACCUSE_MODE,
            accusation_candidate_ids=candidate_ids,
        )

        return ScriptedNpcReply(
            response=(
                "Vem anklagar du?\n"
                + "\n".join(candidate_lines)
                + "\nSvara med siffran för den person du vill anklaga."
            )
        )

    def _handle_accusation_follow_up(
        self,
        npc_id: str,
        player_id: str | None,
        choice_text: str,
        session_key: tuple[str, str],
        session_state: ScriptedNpcSessionState,
    ) -> ScriptedNpcReply:
        candidate_ids = session_state.accusation_candidate_ids or []
        if not candidate_ids:
            self._session_states.pop(session_key, None)
            raise ValueError("Anklagelsen kunde inte fortsätta. Försök igen från menyn.")

        if not choice_text:
            return self._repeat_accusation_candidates(candidate_ids)

        try:
            choice = int(choice_text)
        except ValueError as exc:
            raise ValueError(
                f"Ogiltigt val. Välj en kandidat genom att skicka en siffra mellan 1 och {len(candidate_ids)}."
            ) from exc

        if choice < 1 or choice > len(candidate_ids):
            raise ValueError(
                f"Ogiltigt val. Välj en kandidat genom att skicka en siffra mellan 1 och {len(candidate_ids)}."
            )

        accused_npc_id = candidate_ids[choice - 1]
        self._session_states.pop(session_key, None)
        return self._resolve_accusation(npc_id=npc_id, player_id=player_id, accused_npc_id=accused_npc_id)

    def _repeat_accusation_candidates(self, candidate_ids: list[str]) -> ScriptedNpcReply:
        lines: list[str] = []
        for index, npc_candidate_id in enumerate(candidate_ids, start=1):
            npc = self.npc_repo.get_by_id(npc_candidate_id)
            if not npc:
                continue
            lines.append(f"{index}. {npc.name}")

        if not lines:
            raise ValueError("Kunde inte visa kandidatlistan igen. Börja om från menyn.")

        return ScriptedNpcReply(response="Välj en kandidat:\n" + "\n".join(lines))

    def _resolve_accusation(self, npc_id: str, player_id: str | None, accused_npc_id: str) -> ScriptedNpcReply:
        accused_npc = self.npc_repo.get_by_id(accused_npc_id)
        if not accused_npc:
            raise ValueError("Kunde inte hämta den anklagade personen.")

        result = self._finalize_game(player_id=player_id, npc_id=npc_id, accused_npc_id=accused_npc_id)
        is_correct = bool(result["accused_correct_npc"])

        if is_correct:
            return ScriptedNpcReply(
                response="Ja. Det stämmer med det du har lagt fram.'",
                game_completed=True,
                accused_correct_npc=True,
                accused_npc_id=accused_npc_id,
                completed_at=result.get("completed_at"),
            )

        return ScriptedNpcReply(
            response="Tyvärr, du har fel.",
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
