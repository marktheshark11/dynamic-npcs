class ScriptedNpcService:
    def __init__(self):
        self._menu_text = (
            "1. Få ledtråd\n"
            "2. Jag vet vem mördaren är\n"
            "3. Avsluta"
        )

    def ask_npc(self, npc_id: str, question: str | None = None, player_id: str | None = None) -> dict:
        normalized_question = (question or "").strip()

        if not normalized_question:
            response_text = self._menu_text
        else:
            response_text = self._handle_choice(self._parse_choice(normalized_question))

        return {
            "npc_id": npc_id,
            "player_id": player_id,
            "response": response_text,
        }

    @staticmethod
    def _parse_choice(raw_choice: str) -> int:
        try:
            return int(raw_choice)
        except ValueError as exc:
            raise ValueError("Ogiltigt val. Skicka ett heltal, till exempel 1, 2 eller 3.") from exc

    def _handle_choice(self, choice: int) -> str:
        if choice == 1:
            return "Placeholder: val 1 valt. Här kan du senare ge en ledtråd."
        if choice == 2:
            return "Placeholder: val 2 valt. Här kan du senare hantera anklagelsen."
        if choice == 3:
            return "Placeholder: val 3 valt. Här kan du senare avsluta dialogen."
        return "Ogiltigt val. Skicka tomt för att se menyn eller skriv 1, 2 eller 3."
