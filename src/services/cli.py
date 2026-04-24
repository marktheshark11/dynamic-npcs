import os
import re
import sys

if __name__ == "__main__" and __package__ is None:
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, _root)
    __package__ = "rag"

from db.config import Config
from db.repositories import ConversationRepo, NPCRepo, PlayerRepo
from llms.prompt_guard import PromptGuardValidationError, validate_safe_player_profile
from pipelines import get_pipeline
from services.chat_service import ChatService
from services.scripted_npc_service import ScriptedNpcService


SCRIPTED_NPC_IDS = {"npc_police_officer"}


def _print_prompt_debug(result: dict) -> None:
    flat_prompt = result.get("flat_prompt") or "(ingen prompt tillganglig)"

    print("\n" + "=" * 24 + " PROMPT " + "=" * 24)
    print(flat_prompt)
    print("=" * 57)


def _print_selector_debug(result: dict) -> None:
    selector_debug = result.get("selector_debug") or {}
    if not selector_debug:
        return

    selected_claim_ids = selector_debug.get("selected_claim_ids") or []
    selection_notes = selector_debug.get("selection_notes") or []
    selected_claims = selector_debug.get("selected_claims") or []
    candidate_claims = selector_debug.get("candidate_claims") or []

    print("\n" + "=" * 20 + " SELECTOR " + "=" * 20)
    print(
        f"[Kandidater: {', '.join(claim.get('claim_id') for claim in candidate_claims if claim.get('claim_id')) or '(inga)'}]"
    )
    if candidate_claims:
        print("[Kandidatdetaljer:]")
        for claim in candidate_claims:
            source_marker = " [UNLOCKED]" if claim.get("retrieval_source") == "unlocked" else ""
            important_marker = " [VIKTIG]" if claim.get("important") else ""
            print(f"  - {claim.get('claim_id')}{source_marker}{important_marker}: {claim.get('content', '')}")
    debug_keys = [
        "top_claim_ids",
        "remembered_claim_ids",
        "expanded_claim_ids",
        "extra_claim_ids",
        "unlocked_claim_ids",
        "available_claim_ids_before_cap",
        "available_claim_ids_after_cap",
        "available_claim_ids_after_unlocked",
        "initial_gated_claim_ids",
        "expanded_gated_claim_ids",
    ]
    for key in debug_keys:
        values = selector_debug.get(key) or []
        print(f"[{key}: {', '.join(values) if values else '(inga)'}]")
    print(f"[Valda till prompt: {', '.join(selected_claim_ids) if selected_claim_ids else '(inga)'}]")
    if selected_claims:
        print("[Valda claims:]")
        for claim in selected_claims:
            important_marker = " [VIKTIG]" if claim.get("important") else ""
            print(f"  - {claim.get('claim_id')}{important_marker}: {claim.get('content', '')}")
    if selection_notes:
        print("[Selector-noteringar:]")
        for note in selection_notes:
            print(f"  - {note}")
    if selector_debug.get("raw_response"):
        print(f"[selector_raw_response: {selector_debug.get('raw_response')}]")
    print("=" * 57)


def _extract_claim_ids_from_chains(chain_metadata: list[dict]) -> list[str]:
    """Extraherar alla claim-IDs ur chain_metadata content."""
    ids: list[str] = []
    seen: set[str] = set()
    for chain in chain_metadata or []:
        for m in re.findall(r"<(C\d+)>", chain.get("content", "")):
            if m not in seen:
                seen.add(m)
                ids.append(m)
    return ids


def _select_npc_interactive(npcs):
    print("\nAvailable NPCs:")
    for idx, npc in enumerate(npcs, 1):
        print(f"  {idx}. {npc['name']} ({npc['id']})")

    while True:
        value = input(f"Select NPC (1-{len(npcs)}): ").strip()
        if value.isdigit() and 1 <= int(value) <= len(npcs):
            return npcs[int(value) - 1]["id"]
        print("Invalid selection, try again.")


def _select_conversation_mode() -> str:
    print("\nConversation mode:")
    print("  1. Start new conversation")
    print("  2. Continue existing conversation")

    while True:
        value = input("Choose mode (1-2): ").strip()
        if value == "1":
            return "new"
        if value == "2":
            return "continue"
        print("Invalid selection, try again.")


def _select_player_mode() -> str:
    print("\nPlayer mode:")
    print("  1. Create new player")
    print("  2. Use existing player")

    while True:
        value = input("Choose player mode (1-2): ").strip()
        if value == "1":
            return "new"
        if value == "2":
            return "existing"
        print("Invalid selection, try again.")


def _select_existing_player(player_repo: PlayerRepo):
    players = player_repo.list_all()
    if not players:
        print("No players found. Create a new player instead.")
        return None

    print("\nAvailable Players:")
    for idx, player in enumerate(players, 1):
        print(f"  {idx}. {player.display_str()}")

    while True:
        value = input(f"Select player (1-{len(players)}): ").strip()
        if value.isdigit() and 1 <= int(value) <= len(players):
            return players[int(value) - 1]
        print("Invalid selection, try again.")


def _create_new_player(player_repo: PlayerRepo):
    while True:
        while True:
            name = input("Player name: ").strip()
            if name:
                break
            print("Name cannot be empty.")

        while True:
            appearance = input("Player appearance: ").strip()
            if appearance:
                break
            print("Appearance cannot be empty.")

        try:
            validate_safe_player_profile(name=name, appearance=appearance)
        except PromptGuardValidationError as exc:
            print(str(exc))
            continue

        player = player_repo.create(name=name, appearance=appearance)
        print(f"Created player: {player.display_str()}")
        return player


def _select_existing_conversation(
    conversation_repo: ConversationRepo,
    npc_id: str,
    player_id: str,
):
    conversations = conversation_repo.list_for_npc_and_player(
        npc_id=npc_id,
        player_id=player_id,
    )
    if not conversations:
        print("No existing conversations for this player and NPC. A new one will be created.")
        return None

    print("\nExisting conversations for selected player + NPC:")
    for idx, conversation in enumerate(conversations, 1):
        print(
            f"  {idx}. {conversation['conv_id']} | created: {conversation.get('created_at')} "
            f"| exchanges: {conversation.get('exchange_count', 0)}"
        )

    while True:
        value = input(f"Select conversation (1-{len(conversations)}): ").strip()
        if value.isdigit() and 1 <= int(value) <= len(conversations):
            return conversations[int(value) - 1]["conv_id"]
        print("Invalid selection, try again.")


def _summarize_and_print(chat_service: ChatService, conversation_id: str | None) -> None:
    if not conversation_id:
        return

    result = chat_service.summarize_conversation(conversation_id)
    if not result:
        print(f"Could not summarize conversation: {conversation_id}")
        return

    print("\n=== Conversation Summary ===")
    print(f"Conversation ID: {result['conversation_id']}")
    print(result["summary"])


def _start_dynamic_conversation(
    chat_service: ChatService,
    npc_id: str,
    player_id: str | None,
) -> str | None:
    result = chat_service.ask_npc(
        npc_id=npc_id,
        question="",
        player_id=player_id,
        conversation_id=None,
    )
    if not result:
        print("No response.")
        return None

    conversation_id = result.get("conversation_id")
    chain_metadata = result.get("chain_metadata", [])
    used_claims = result.get("used_claims") or []
    _print_prompt_debug(result)
    _print_selector_debug(result)
    print("\n" + "=" * 22 + " RESULTAT " + "=" * 21)
    print("\n[Hittade claims:]")
    if chain_metadata:
        for chain in chain_metadata:
            print(f"  {chain['content']}")
    else:
        print("  (inga)")
    print(f"[Använda: {', '.join(used_claims) if used_claims else '(inga)'}]")
    if conversation_id:
        print(f"[Konversation: {conversation_id}]")
    print(f"\nNPC: {result['response']}")
    print("=" * 57)
    return conversation_id


def main():
    config = Config.from_env()
    driver = config.driver
    embed_model = config.embed_model

    try:
        npc_repo = NPCRepo(driver)
        player_repo = PlayerRepo(driver)
        conversation_repo = ConversationRepo(driver)
        pipeline = get_pipeline(
            pipeline_id=config.pipeline_id,
            driver=driver,
            embed_model=embed_model,
        )
        chat_service = ChatService(
            driver,
            embed_model,
            pipeline=pipeline,
        )
        scripted_npc_service = ScriptedNpcService(driver)

        npcs = npc_repo.list_for_selection()

        if not npcs:
            print("No NPCs found.")
            return

        npc_id = _select_npc_interactive(npcs)
        is_scripted_npc = npc_id in SCRIPTED_NPC_IDS
        player_mode = _select_player_mode()
        if player_mode == "new":
            selected_player = _create_new_player(player_repo)
        else:
            selected_player = _select_existing_player(player_repo)
            if not selected_player:
                selected_player = _create_new_player(player_repo)

        player_id = selected_player.player_id

        conversation_id = None

        if not is_scripted_npc:
            mode = _select_conversation_mode()
            if mode == "continue":
                conversation_id = _select_existing_conversation(
                    conversation_repo=conversation_repo,
                    npc_id=npc_id,
                    player_id=player_id,
                )
            else:
                conversation_id = _start_dynamic_conversation(
                    chat_service=chat_service,
                    npc_id=npc_id,
                    player_id=player_id,
                )
        else:
            print(
                "\nKommissarien använder scriptad terminal-chat. "
                "Skicka tomt för att visa menyn. Om du väljer 3 får du sedan en kandidatlista "
                "och svarar med siffran för den person du vill anklaga. Välj 4 för att se ditt player_id."
            )

        while True:
            question = input("Question (new/exit): ")

            if not is_scripted_npc:
                question = question.strip()
                if not question:
                    continue

            lowered = question.strip().lower()
            if lowered == "exit":
                if not is_scripted_npc:
                    _summarize_and_print(chat_service, conversation_id)
                break
            if lowered == "new":
                if not is_scripted_npc:
                    _summarize_and_print(chat_service, conversation_id)
                    conversation_id = _start_dynamic_conversation(
                        chat_service=chat_service,
                        npc_id=npc_id,
                        player_id=player_id,
                    )
                    continue

            if is_scripted_npc:
                try:
                    result = scripted_npc_service.ask_npc(
                        npc_id=npc_id,
                        question=question,
                        player_id=player_id,
                        conversation_id=conversation_id,
                    )
                except ValueError as exc:
                    print(f"Error: {exc}")
                    continue
            else:
                result = chat_service.ask_npc(
                    npc_id=npc_id,
                    question=question,
                    player_id=player_id,
                    conversation_id=conversation_id,
                )

            if not result:
                print("No response.")
                continue

            previous_conversation_id = conversation_id

            conversation_id = result.get("conversation_id")

            if not is_scripted_npc:

                chain_metadata = result.get("chain_metadata", [])
                used_claims = result.get("used_claims") or []
                _print_prompt_debug(result)
                _print_selector_debug(result)
                print("\n" + "=" * 22 + " RESULTAT " + "=" * 21)
                print("\n[Hittade claims:]")
                if chain_metadata:
                    for chain in chain_metadata:
                        print(f"  {chain['content']}")
                else:
                    print("  (inga)")
                print(f"[Använda: {', '.join(used_claims) if used_claims else '(inga)'}]")

                if conversation_id:
                    if previous_conversation_id and previous_conversation_id != conversation_id:
                        print(f"[Ny konversation: {conversation_id}]")
                    else:
                        print(f"[Konversation: {conversation_id}]")

            print(f"\nNPC: {result['response']}")
            if not is_scripted_npc:
                print("=" * 57)
    finally:
        config.close()


if __name__ == "__main__":
    main()
