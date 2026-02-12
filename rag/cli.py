import os
import sys

if __name__ == "__main__" and __package__ is None:
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, _root)
    __package__ = "rag"

from dotenv import load_dotenv
from neo4j import GraphDatabase
from langchain_community.embeddings import OllamaEmbeddings

from .pipeline import RAGPipeline

def select_from_menu(prompt, options):
    print(f"\n{prompt}")
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")
    while True:
        choice = input(f"Ange nummer (1-{len(options)}): ")
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1]
        print("Ogiltigt val, försök igen.")

def get_all_npcs(driver):
    with driver.session() as session:
        result = session.run("MATCH (n:NPC) RETURN n.name AS name ORDER BY n.name")
        return [record["name"] for record in result]

def main():
    load_dotenv()
    db_user = os.getenv("NEO4J_USER")
    db_password = os.getenv("NEO4J_PASSWORD")
    db_uri = os.getenv('NEO4J_URI')
    if not db_uri:
        print("NEO4J_URI saknas!")
        return
    driver = GraphDatabase.driver(db_uri, auth=(db_user, db_password))
    embed_model = OllamaEmbeddings(model="mxbai-embed-large")
    pipeline = RAGPipeline(driver, embed_model)
    print("=" * 50)
    print("         HITTA INFO")
    print("=" * 50)
    npcs = get_all_npcs(driver)
    if not npcs:
        print("\n⚠ Inga NPCs hittades")
        return
    npc_name = select_from_menu("Välj karaktär:", npcs)
    question = input("\nSkriv din fråga: ")
    print("\n" + "-" * 50)
    prompt, chain_metadata = pipeline.run(npc_name, question)
    if not prompt:
        print("⚠ Inga claims hittades")
        return
    print("\n" + "=" * 50)
    print("GENERERAD PROMPT:")
    print("=" * 50)
    print(prompt)
    driver.close()

if __name__ == "__main__":
    main()
