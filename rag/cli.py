import os
import sys

if __name__ == "__main__" and __package__ is None:
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, _root)
    __package__ = "rag"

from db.config import Config

from .pipeline import RAGPipeline
from services.npc_service import NPCService

def select_from_menu(prompt, options):
    print(f"\n{prompt}")
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")
    while True:
        choice = input(f"Ange nummer (1-{len(options)}): ")
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return int(choice) - 1
        print("Ogiltigt val, försök igen.")

def main():
    config = Config.from_env()
    driver = config.driver
    embed_model = config.embed_model
    pipeline = RAGPipeline(driver, embed_model)
    npc_service = NPCService(driver)
    print("=" * 50)
    print("         HITTA INFO")
    print("=" * 50)
    npcs = npc_service.list_npcs()
    if not npcs:
        print("\n⚠ Inga NPCs hittades")
        return

    options = [f"{npc['name']} ({npc['id']})" for npc in npcs]
    selected_index = select_from_menu("Välj karaktär:", options)
    npc_id = npcs[selected_index]["id"]
    question = input("\nSkriv din fråga: ")
    print("\n" + "-" * 50)
    prompt_result, chain_metadata = pipeline.run(npc_id, question)
    if not prompt_result:
        print("⚠ Inga claims hittades")
        return
    print("\n" + "=" * 50)
    print("GENERERAD PROMPT:")
    print("=" * 50)
    print(prompt_result.flat_prompt)

    print("\n" + "=" * 50)
    print("CHAT MESSAGES:")
    print("=" * 50)
    for message in prompt_result.messages:
        print(f"[{message['role']}]\n{message['content']}\n")
    config.close()

if __name__ == "__main__":
    main()
