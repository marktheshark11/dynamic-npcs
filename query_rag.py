from llms.groq import chat
from db_neo4j import ex_query
import json


DATABASE_SCHEMA = """
Neo4j Database Schema:

NODES:
- NPC {name: string, age: int, role: string}
- Memory {memory_id: string, memory: string}
- Event {event_id: string, location: string, start_time: string, stop_time: string, summary: string}
- Personality {personality_id: string, summary: string, lie_style: string, conflict_style: string, stress_response: string}
- Trait {trait: string}

RELATIONSHIPS:
- (NPC)-[:HAS_MEMORY]->(Memory)
- (Memory)-[:MEMORY_OF]->(Event)
- (NPC)-[:HAS_PERSONALITY]->(Personality)
- (Personality)-[:HAS_TRAIT]->(Trait)
- (NPC)-[:UNCLE_OF|NIECE_OF|BROTHER_OF|SISTER_OF]->(NPC)  [family relationships]

IMPORTANT:
- Use full names: "Elin von Dahlen", "Alrik von Dahlen", "Magnus Kreutz", "Sister Helena"
- For relationships between NPCs, use: MATCH (a:NPC)-[r]-(b:NPC)

QUERY EXAMPLES:

1. Find all NPCs:
   MATCH (n:NPC) RETURN n.name, n.age, n.role

2. Find relationship between two NPCs:
   MATCH (a:NPC {name: "Elin von Dahlen"})-[r]-(b:NPC {name: "Alrik von Dahlen"})
   RETURN type(r) as relationship, a.name, b.name

3. Find all relationships for an NPC:
   MATCH (n:NPC {name: "Elin von Dahlen"})-[r]-(other:NPC)
   RETURN type(r) as relationship, other.name as related_person

4. Find who was at an event:
   MATCH (e:Event {location: "Great hall"})<-[:MEMORY_OF]-()<-[:HAS_MEMORY]-(n:NPC)
   RETURN DISTINCT n.name
"""


def generate_cypher_query(user_question: str) -> str:
    """LLM genererar Cypher query"""
    prompt = f"""{DATABASE_SCHEMA}

User question: "{user_question}"

If asked something about a Person, check who the person is from the NPC list and use that name

Generate a Cypher query to answer this question.
Return ONLY the Cypher query, no explanations.

Query:"""
    
    query = chat(prompt).strip()
    
    # Ta bort markdown om den finns
    if query.startswith("```"):
        query = "\n".join(query.split("\n")[1:-1])
    
    return query.strip()


def query_rag(user_question: str) -> str:
    """Query-based RAG pipeline"""
    
    # 1. Generera query
    print(f"\n📝 Generating query for: {user_question}")
    cypher = generate_cypher_query(user_question)
    print(f"Query: {cypher}")
    
    # 2. Kör query
    try:
        records, _, _ = ex_query(cypher)
        results = [dict(r) for r in records]
        print(f"✅ Found {len(results)} results")
    except Exception as e:
        return f"Query failed: {e}"
    
    # 3. Formulera svar
    answer_prompt = f"""
Question: "{user_question}"

Data from database:
{json.dumps(results, indent=2)}

Answer the question naturally based on this data.
"""
    
    return chat(answer_prompt)


# Test
if __name__ == "__main__":

    while True:
      question = input('Ask something (exit to cancel): ')
      if question == 'exit':
          break
      print(query_rag(question))
        
    # questions = [
    #     "Who are all the NPCs?",
    #     "What is Elin von Dahlen's age?",
    #     "Show me events in the Great hall"
    # ]
    
    # for q in questions:
    #     answer = query_rag(q)
    #     print(f"\n💡 {answer}\n{'='*60}\n")