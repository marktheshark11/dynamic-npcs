import argparse
import os
import sys

if __name__ == "__main__" and __package__ is None:
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, _root)
    __package__ = "rag"

from dotenv import load_dotenv
from langchain_community.embeddings import OllamaEmbeddings
from neo4j import GraphDatabase
from chat_service import ChatService
from npc_service import NPCService
# from . import ChatService, NPCService


def _build_parser():
    parser = argparse.ArgumentParser(description="Run NPC RAG + prompt + Groq chat flow")
    parser.add_argument("--list-npcs", action="store_true", help="List all NPCs and exit")
    parser.add_argument("--npc-id", help="NPC id to use")
    parser.add_argument("--question", help="Question to ask the NPC")
    parser.add_argument("--model", default="llama-3.3-70b-versatile", help="Groq model name")
    parser.add_argument("--top-k", type=int, default=3, help="Top semantic claims to retrieve")
    parser.add_argument("--min-refs", type=int, default=2, help="Min refs for relation claims")
    parser.add_argument(
        "--prompt-only",
        action="store_true",
        help="Build and print prompt/messages only, do not call Groq",
    )
    return parser


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
    parser = _build_parser()
    args = parser.parse_args()

    load_dotenv()
    db_uri = os.getenv("NEO4J_URI")
    db_user = os.getenv("NEO4J_USER")
    db_password = os.getenv("NEO4J_PASSWORD")

    if not db_uri:
        raise SystemExit("Missing NEO4J_URI in environment")

    driver = GraphDatabase.driver(db_uri, auth=(db_user, db_password))
    embed_model = OllamaEmbeddings(model="mxbai-embed-large")

    try:
        npc_service = NPCService(driver)
        chat_service = ChatService(driver, embed_model, default_model=args.model)

        npcs = npc_service.list_npcs()
        if args.list_npcs:
            if not npcs:
                print("No NPCs found.")
                return
            for npc in npcs:
                print(f"{npc['id']}: {npc['name']}")
            return

        if not npcs:
            print("No NPCs found.")
            return

        npc_id = args.npc_id or _select_npc_interactive(npcs)
        question = args.question or input("Question: ").strip()

        if args.prompt_only:
            prompt_result, chain_metadata = chat_service.build_prompt(
                npc_id=npc_id,
                question=question,
                top_k=args.top_k,
                min_refs=args.min_refs,
            )
            if not prompt_result:
                print("No prompt could be built (NPC not found or no claims).")
                return

            print("\n=== Flat Prompt ===")
            print(prompt_result.flat_prompt)
            print("\n=== Chat Messages ===")
            for msg in prompt_result.messages:
                print(f"[{msg['role']}]\n{msg['content']}\n")
            print(f"Chains: {len(chain_metadata)}")
            return

        result = chat_service.ask_npc(
            npc_id=npc_id,
            question=question,
            model=args.model,
            top_k=args.top_k,
            min_refs=args.min_refs,
        )
        if not result:
            print("No response (NPC not found or no claims).")
            return

        print("\n=== NPC Response ===")
        print(result["response"])
    finally:
        driver.close()


if __name__ == "__main__":
    main()
