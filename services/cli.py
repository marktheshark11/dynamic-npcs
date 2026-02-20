import os
import sys

if __name__ == "__main__" and __package__ is None:
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, _root)
    __package__ = "rag"

from db.config import Config
from chat_service import ChatService
from npc_service import NPCService


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


def main():
    config = Config.from_env()
    driver = config.driver
    embed_model = config.embed_model

    try:
        npc_service = NPCService(driver)
        chat_service = ChatService(driver, embed_model)

        npcs = npc_service.list_npcs()

        if not npcs:
            print("No NPCs found.")
            return

        npc_id = _select_npc_interactive(npcs)
        mode = _select_conversation_mode()
        conversation_id = None
        next_turn_new_conversation = mode == "new"

        if mode == "continue":
            value = input("Conversation ID (leave empty to start new): ").strip()
            if value:
                conversation_id = value
            else:
                next_turn_new_conversation = True

        while True:
            question = input("Question (new/exit): ").strip()

            if not question:
                continue

            lowered = question.lower()
            if lowered == "exit":
                _summarize_and_print(chat_service, conversation_id)
                break
            if lowered == "new":
                _summarize_and_print(chat_service, conversation_id)
                conversation_id = None
                next_turn_new_conversation = True
                print("Starting a new conversation on your next question.")
                continue

            result = chat_service.ask_npc(
                npc_id=npc_id,
                question=question,
                conversation_id=conversation_id,
                new_conversation=next_turn_new_conversation,
            )
            next_turn_new_conversation = False

            if not result:
                print("No response.")
                continue

            previous_conversation_id = conversation_id
            conversation_id = result.get("conversation_id")

            print("\n=== NPC Response ===")
            for messages in result['messages']:
                print(messages['role'])
                print(messages['content'])
            print(result["response"])

            if conversation_id:
                if previous_conversation_id and previous_conversation_id != conversation_id:
                    print(f"Conversation switched to: {conversation_id}")
                else:
                    print(f"Conversation ID: {conversation_id}")
    finally:
        config.close()


if __name__ == "__main__":
    main()
