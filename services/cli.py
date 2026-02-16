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
        question = input("Question: ").strip()

        result = chat_service.ask_npc(
            npc_id=npc_id,
            question=question,
        )
        if not result:
            print("No response.")
            return

        print("\n=== NPC Response ===")
        for messages in result['messages']:
            print(messages['role'])
            print(messages['content'])
        # print(result['messages'])
        print(result["response"])
    finally:
        config.close()


if __name__ == "__main__":
    main()
